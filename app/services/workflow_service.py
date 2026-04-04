import time
from typing import Optional

from app.models.schemas import (
    AlignmentResult,
    QARequest,
    QAWorkflowResult,
    ValidationIssue,
    ValidationResult,
)
from app.services.ai_service import ai_service
from app.services.bdd_service import bdd_service
from app.services.github_service import github_service
from app.services.jira_service import jira_service
from app.services.report_service import report_service
from app.services.test_generation_service import test_generation_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowService:
    async def run_full_workflow(self, request: QARequest) -> QAWorkflowResult:
        start = time.monotonic()
        result = QAWorkflowResult(jira_id=request.jira_id, release=request.release)
        extra = request.custom_prompt or ""
        team_ctx = await self._load_team_context(request.team_id)
        additional_context = "\n".join(filter(None, [team_ctx, extra]))

        logger.info(f"=== QA Workflow START: {request.jira_id} ===")

        try:
            # -------------------------------------------------------------- #
            # Step 1 — Fetch Jira ticket                                       #
            # -------------------------------------------------------------- #
            logger.info("[1/9] Fetching Jira ticket…")
            ticket = await jira_service.get_ticket(request.jira_id)
            if not ticket:
                raise ValueError(f"Jira ticket not found: {request.jira_id}")
            result.ticket = ticket
            ticket_dict = ticket.model_dump()

            # -------------------------------------------------------------- #
            # Step 2 — Validate ticket quality                                 #
            # -------------------------------------------------------------- #
            logger.info("[2/9] Validating ticket quality…")
            sys_p, usr_p = ai_service.build_validation_prompt(ticket_dict, additional_context)
            val_raw = await ai_service.call_structured(sys_p, usr_p)
            result.validation = ValidationResult(
                quality_score=val_raw.get("quality_score", 50),
                grade=val_raw.get("grade", "C"),
                issues=[
                    ValidationIssue(**i) for i in val_raw.get("issues", [])
                ],
                strengths=val_raw.get("strengths", []),
                summary=val_raw.get("summary", ""),
            )

            # -------------------------------------------------------------- #
            # Step 3 — Fetch GitHub commits                                    #
            # -------------------------------------------------------------- #
            logger.info("[3/9] Fetching GitHub commits…")
            commits = await github_service.get_commits_from_jira(request.jira_id)
            result.commits = commits
            commits_dict = [c.model_dump() for c in commits]

            # -------------------------------------------------------------- #
            # Step 4 — Code vs Jira alignment check                           #
            # -------------------------------------------------------------- #
            logger.info("[4/9] Code-requirement alignment check…")
            sys_p, usr_p = ai_service.build_alignment_prompt(ticket_dict, commits_dict, additional_context)
            align_raw = await ai_service.call_structured(sys_p, usr_p)
            result.alignment = AlignmentResult(
                score=align_raw.get("score", 50),
                aligned=align_raw.get("aligned", False),
                coverage_gaps=align_raw.get("coverage_gaps", []),
                over_implementation=align_raw.get("over_implementation", []),
                summary=align_raw.get("summary", ""),
            )
            alignment_dict = result.alignment.model_dump()

            # -------------------------------------------------------------- #
            # Step 5 — Generate test cases                                     #
            # -------------------------------------------------------------- #
            logger.info("[5/9] Generating test cases…")
            sys_p, usr_p = ai_service.build_test_generation_prompt(
                ticket_dict, alignment_dict, additional_context
            )
            tc_raw = await ai_service.call_structured(sys_p, usr_p)
            result.test_cases = test_generation_service.parse_test_cases(tc_raw)
            tc_dict = [tc.model_dump() for tc in result.test_cases]

            # -------------------------------------------------------------- #
            # Step 6 — Export test case artefacts                             #
            # -------------------------------------------------------------- #
            logger.info("[6/9] Exporting test case artefacts…")
            result.testcases_csv_path = test_generation_service.export_as_csv(
                result.test_cases, request.jira_id
            )
            result.testcases_json_path = test_generation_service.export_as_json(
                result.test_cases, request.jira_id
            )

            # -------------------------------------------------------------- #
            # Step 7 — Generate BDD scenarios                                  #
            # -------------------------------------------------------------- #
            if request.include_bdd:
                logger.info("[7/9] Generating BDD scenarios…")
                sys_p, usr_p = ai_service.build_bdd_prompt(ticket_dict, tc_dict, additional_context)
                bdd_raw = await ai_service.call_structured(sys_p, usr_p)
                feature_name, result.bdd_scenarios = bdd_service.parse_scenarios(bdd_raw)

                # ---------------------------------------------------------- #
                # Step 8 — Generate pytest-bdd step definitions               #
                # ---------------------------------------------------------- #
                logger.info("[8/9] Generating pytest-bdd step definitions…")
                scenarios_dict = [s.model_dump() for s in result.bdd_scenarios]
                sys_p, usr_p = ai_service.build_step_definitions_prompt(
                    scenarios_dict, additional_context
                )
                steps_raw = await ai_service.call_structured(sys_p, usr_p)
                result.step_definitions = bdd_service.parse_step_definitions(steps_raw)

                result.bdd_feature_path = bdd_service.save_feature_file(
                    feature_name, result.bdd_scenarios, request.jira_id
                )
                bdd_service.save_step_definitions(
                    result.step_definitions, request.jira_id
                )
            else:
                logger.info("[7/9] BDD generation skipped (include_bdd=false)")
                logger.info("[8/9] pytest-bdd step definition generation skipped")

            # -------------------------------------------------------------- #
            # Step 9 — Generate HTML report                                    #
            # -------------------------------------------------------------- #
            logger.info("[9/9] Generating HTML report…")
            result.report_path = report_service.generate_html_report(result)

            # -------------------------------------------------------------- #
            # Optional: Post to Jira (auto mode — prefer manual review via UI) #
            # -------------------------------------------------------------- #
            if request.post_to_jira:
                logger.info("Posting QA summary comment to Jira…")
                comment = self._build_jira_comment(result)
                await jira_service.add_comment(request.jira_id, comment)
                if result.report_path:
                    await jira_service.attach_file(request.jira_id, result.report_path)

            result.status = "completed"
            logger.info(f"=== QA Workflow COMPLETE: {request.jira_id} ===")

        except Exception as exc:
            logger.error(
                f"Workflow FAILED for {request.jira_id}: {exc}", exc_info=True
            )
            result.status = "failed"
            result.error = str(exc)

        result.duration_seconds = round(time.monotonic() - start, 2)
        return result

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _load_team_context(team_id: Optional[str]) -> str:
        """Load team-specific instruction markdown as extra context for prompts."""
        if not team_id:
            return ""
        from pathlib import Path
        for candidate in (
            Path("config/teams") / f"{team_id}.md",
            Path("config/teams") / f"{team_id.lower()}.md",
        ):
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        return ""

    def _build_jira_comment(self, result: QAWorkflowResult) -> str:
        score = result.validation.quality_score if result.validation else "N/A"
        grade = result.validation.grade if result.validation else "N/A"
        alignment_score = result.alignment.score if result.alignment else "N/A"
        tc_count = len(result.test_cases)
        bdd_count = len(result.bdd_scenarios)
        issue_count = len(result.validation.issues) if result.validation else 0

        return (
            f"*🤖 QA Agent Analysis — {result.jira_id}*\n\n"
            f"*Quality Score:* {score}/100 (Grade {grade})\n"
            f"*Code Alignment:* {alignment_score}/100\n"
            f"*Issues Found:* {issue_count}\n"
            f"*Test Cases Generated:* {tc_count}\n"
            f"*BDD Scenarios:* {bdd_count}\n"
            f"*Duration:* {result.duration_seconds}s\n\n"
            f"Report is attached.\n\n"
            f"_Generated by QA Agent Platform_"
        )


workflow_service = WorkflowService()
