from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from typing import Optional

from app.config.providers import list_providers, get_provider
from app.config.settings import settings
from app.models.schemas import (
    AddCommentRequest,
    BulkFieldUpdateRequest,
    BulkTransitionRequest,
    JiraCreateRequest,
    JiraUploadRequest,
    JiraQueryRequest,
    MarkTestResultRequest,
    PushTestsRequest,
    QARequest,
    QAResponse,
    QuickRegressionRequest,
    ReleaseQARequest,
    TeamConfigUpdate,
    TestDataRequest,
    TestExecutionRequest,
    TestPlanRequest,
    TestSetRequest,
    UpstreamCallRequest,
)
from app.services.github_service import github_service
from app.services.history_service import history_service
from app.services.jira_ops_service import jira_ops_service
from app.services.jira_service import jira_service
from app.services.upstream_service import upstream_service
from app.services.workflow_service import workflow_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ── existing endpoints ─────────────────────────────────────────────────────────


@router.post("/run-qa", response_model=QAResponse)
async def run_qa(request: QARequest):
    """Execute the full QA workflow for a Jira ticket."""
    logger.info(f"POST /run-qa  jira_id={request.jira_id}")

    run_id = str(uuid.uuid4())
    steps_dict = request.steps.model_dump()

    history_service.create_run(
        run_id=run_id,
        task_type="qa_analysis",
        jira_id=request.jira_id,
        release=request.release,
        team_id=request.team_id,
        team_name=request.team_id,
        triggered_by=request.triggered_by,
        steps_selected=steps_dict,
    )

    import time
    t0 = time.time()
    result = await workflow_service.run_full_workflow(request)
    elapsed = round(time.time() - t0, 2)

    quality_score = result.validation.quality_score if result.validation else None
    alignment_score = result.alignment.score if result.alignment else None
    history_service.complete_run(
        run_id=run_id,
        duration_secs=elapsed,
        quality_score=quality_score,
        alignment_score=alignment_score,
        test_case_count=len(result.test_cases),
        bdd_count=len(result.bdd_scenarios),
        outputs={
            "report": result.report_path,
            "testcases_csv": result.testcases_csv_path,
            "testcases_json": result.testcases_json_path,
            "bdd_feature": result.bdd_feature_path,
        },
        error_message=result.error,
    )

    return QAResponse(
        success=result.status == "completed",
        message=(
            f"QA workflow completed for {result.jira_id}"
            if result.status == "completed"
            else f"QA workflow failed: {result.error}"
        ),
        data=result,
        error=result.error,
        run_id=run_id,
    )


@router.get("/providers")
async def get_providers():
    """List all supported LLM providers and their available models."""
    return {
        "current_provider": settings.llm_provider,
        "current_model": settings.openai_model,
        "providers": list_providers(),
    }


@router.get("/config")
async def get_config():
    """Return non-sensitive active configuration (for the UI status bar)."""
    provider = get_provider(settings.llm_provider)
    return {
        "provider": settings.llm_provider,
        "provider_name": provider["name"],
        "model": settings.openai_model,
        "jira_connected": not settings.use_mock_jira,
        "jira_url": settings.jira_base_url,
        "github_connected": not settings.use_mock_github,
        "jira_project": settings.jira_project_key,
        "mcp_note": (
            "This platform uses Jira and GitHub REST APIs directly. "
            "MCP server integration is planned for a future release."
        ),
    }


@router.get("/outputs/{output_type}/{filename}")
async def download_output(output_type: str, filename: str):
    """Serve a generated output artefact inline (opens in browser tab)."""
    allowed_types = {"reports", "testcases", "bdd"}
    if output_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid output type")

    safe_filename = Path(filename).name
    file_path = Path("outputs") / output_type / safe_filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Inline types open in the browser tab; everything else prompts a download.
    inline_suffixes = {".html", ".feature", ".py"}
    media_types = {
        ".html": "text/html",
        ".csv": "text/csv",
        ".json": "application/json",
        ".feature": "text/plain",
        ".py": "text/plain",
    }
    media_type = media_types.get(file_path.suffix, "application/octet-stream")

    if file_path.suffix in inline_suffixes:
        # Serve inline — browser opens it in a new tab
        content = file_path.read_bytes()
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"inline; filename=\"{safe_filename}\""},
        )

    # CSV / JSON — still download but keep the proper filename
    return FileResponse(str(file_path), media_type=media_type, filename=safe_filename)


@router.get("/health")
async def health_check():
    """Liveness probe."""
    from app.config.providers import get_provider as gp
    p = gp(settings.llm_provider)
    return {
        "status": "healthy",
        "service": "QA Agent Platform",
        "llm_provider": settings.llm_provider,
        "llm_provider_name": p["name"],
        "llm_model": settings.openai_model,
        "jira": "live" if not settings.use_mock_jira else "mock",
        "github": "live" if not settings.use_mock_github else "mock",
    }


# ── Task 1: Manual Jira upload after review ────────────────────────────────────


@router.post("/upload-to-jira")
async def upload_to_jira(request: JiraUploadRequest):
    """Post the reviewed/edited QA summary as a Jira comment and optionally attach the HTML report."""
    logger.info(f"POST /upload-to-jira  jira_id={request.jira_id}")

    issues_text = "\n".join(f"  • {i}" for i in request.edited_issues) if request.edited_issues else "  None found"
    comment = (
        f"*🤖 QA Agent Analysis — {request.jira_id}*\n\n"
        f"*Quality Score:* {request.quality_score}/100 (Grade {request.grade})\n\n"
        f"*Summary:*\n{request.edited_summary}\n\n"
        f"*Issues Identified:*\n{issues_text}\n\n"
        f"_Reviewed and uploaded via QA Agent Platform_"
    )

    comment_ok = await jira_service.add_comment(request.jira_id, comment)
    attach_ok = True

    if request.attach_report and request.report_filename:
        safe_name = Path(request.report_filename).name
        report_path = Path("outputs/reports") / safe_name
        if report_path.exists():
            attach_ok = await jira_service.attach_file(request.jira_id, str(report_path))
        else:
            logger.warning(f"Report file not found: {report_path}")
            attach_ok = False

    if not comment_ok:
        raise HTTPException(status_code=502, detail="Failed to post comment to Jira")

    return {
        "success": True,
        "comment_posted": comment_ok,
        "report_attached": attach_ok,
        "jira_id": request.jira_id,
    }


# ── Task 2: Single-click test case download ─────────────────────────────────────


@router.get("/testcase-download/{jira_id}/{fmt}")
async def download_testcases(jira_id: str, fmt: str):
    """Convenience endpoint: download test cases by jira_id and format (csv | json | bdd | steps)."""
    safe_id = Path(jira_id).name
    mapping = {
        "csv": (Path("outputs/testcases") / f"{safe_id}_testcases.csv", "text/csv"),
        "json": (Path("outputs/testcases") / f"{safe_id}_testcases.json", "application/json"),
        "bdd": (Path("outputs/bdd") / f"{safe_id}.feature", "text/plain"),
        "steps": (Path("outputs/bdd") / f"{safe_id}_steps.py", "text/plain"),
    }
    if fmt not in mapping:
        raise HTTPException(status_code=400, detail="fmt must be csv | json | bdd | steps")
    file_path, media_type = mapping[fmt]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path.name}")
    return FileResponse(str(file_path), media_type=media_type, filename=file_path.name)


# ── Task 3: Push Playwright tests to automation repo ──────────────────────────


@router.post("/push-playwright-tests")
async def push_playwright_tests(request: PushTestsRequest):
    """Read generated Playwright test file for jira_id and push it to the automation repo.

    If create_pr=True (default) a pull request is opened; otherwise the commit lands
    directly on the qa-agent/<jira_id> branch.
    """
    logger.info(f"POST /push-playwright-tests  jira_id={request.jira_id}")
    safe_id = Path(request.jira_id).name
    steps_file = Path("outputs/bdd") / f"{safe_id}_steps.py"
    if not steps_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No generated test file found for {request.jira_id}. Run the QA workflow with include_bdd=true first.",
        )

    file_content = steps_file.read_text(encoding="utf-8")
    branch_prefix = request.branch_prefix or "qa-agent"

    push_result = await github_service.push_playwright_test_file(
        jira_id=request.jira_id,
        file_content=file_content,
        create_pr=request.create_pr,
        branch_prefix=branch_prefix,
    )

    return {
        "success": True,
        "jira_id": request.jira_id,
        **push_result,
    }


# ── Task 4: Release-batch QA ────────────────────────────────────────────────────


@router.post("/run-release")
async def run_qa_release(request: ReleaseQARequest):
    """Fetch all Jira tickets for a release version and run the QA workflow on each."""
    logger.info(f"POST /run-release  release={request.release}")

    tickets = await jira_service.get_release_tickets(request.release)
    if not tickets:
        raise HTTPException(
            status_code=404,
            detail=f"No tickets found for release '{request.release}'",
        )

    results = []
    for ticket in tickets:
        qa_req = QARequest(
            jira_id=ticket.id,
            release=request.release,
            include_bdd=request.include_bdd,
            post_to_jira=False,
            create_pr=False,
            custom_prompt=request.custom_prompt,
            team_id=request.team_id,
        )
        result = await workflow_service.run_full_workflow(qa_req)
        results.append({
            "jira_id": result.jira_id,
            "status": result.status,
            "quality_score": result.validation.quality_score if result.validation else None,
            "grade": result.validation.grade if result.validation else None,
            "test_cases": len(result.test_cases),
            "bdd_scenarios": len(result.bdd_scenarios),
            "report_path": result.report_path,
            "error": result.error,
        })

    return {
        "release": request.release,
        "total_tickets": len(tickets),
        "results": results,
    }


# ── Task 5: Team configuration files ────────────────────────────────────────────

_TEAMS_DIR = Path("config/teams")


@router.get("/teams")
async def list_teams():
    """List all available team configuration files."""
    _TEAMS_DIR.mkdir(parents=True, exist_ok=True)
    teams = []
    for f in sorted(_TEAMS_DIR.glob("*.md")):
        teams.append({"id": f.stem, "name": f.stem.replace("-", " ").title(), "filename": f.name})
    return {"teams": teams}


@router.get("/teams/{team_id}")
async def get_team_config(team_id: str):
    """Return the markdown content of a team configuration file."""
    safe_id = Path(team_id).name  # prevent path traversal
    path = _TEAMS_DIR / f"{safe_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Team config '{safe_id}' not found")
    return {"team_id": safe_id, "content": path.read_text(encoding="utf-8")}


@router.put("/teams/{team_id}")
async def update_team_config(team_id: str, body: TeamConfigUpdate):
    """Save (create or overwrite) a team configuration file."""
    safe_id = Path(team_id).name
    _TEAMS_DIR.mkdir(parents=True, exist_ok=True)
    path = _TEAMS_DIR / f"{safe_id}.md"
    path.write_text(body.content, encoding="utf-8")
    logger.info(f"Team config saved: {path}")
    return {"success": True, "team_id": safe_id, "bytes_written": len(body.content.encode())}


# ════════════════════════════════════════════════════════════════════════════════
# HISTORY — run audit log
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/history")
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    team_id: Optional[str] = Query(None),
    jira_id: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
):
    return history_service.get_history(limit=limit, offset=offset, team_id=team_id, jira_id=jira_id, task_type=task_type)


@router.get("/history/stats")
async def get_history_stats():
    return history_service.get_stats()


@router.get("/history/{run_id}")
async def get_history_run(run_id: str):
    run = history_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.delete("/history/{run_id}")
async def delete_history_run(run_id: str):
    deleted = history_service.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"success": True, "deleted_run_id": run_id}


# ════════════════════════════════════════════════════════════════════════════════
# UPSTREAM SYSTEMS — test data stubs
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/upstream/systems")
async def list_upstream_systems():
    return {"systems": upstream_service.list_systems()}


@router.post("/upstream/{system_id}")
async def call_upstream_system(system_id: str, request: UpstreamCallRequest):
    result = upstream_service.call_upstream(system_id, request.endpoint, request.params)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ════════════════════════════════════════════════════════════════════════════════
# TEST DATA MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/test-data")
async def manage_test_data(request: TestDataRequest):
    if request.action == "discover":
        result = upstream_service.discover_test_data(request.system_id, request.data_type, request.filters)
    elif request.action == "create":
        result = upstream_service.create_test_data(request.system_id, request.spec)
    else:
        raise HTTPException(status_code=400, detail="action must be 'discover' or 'create'")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "system_id": request.system_id, "action": request.action, "data": result}


# ════════════════════════════════════════════════════════════════════════════════
# JIRA OPS — extended ticket operations
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/jira-ops/query")
async def jira_query(request: JiraQueryRequest):
    tickets = jira_ops_service.query_tickets(
        component=request.component,
        status=request.status,
        assignee=request.assignee,
        sprint=request.sprint,
        fix_version=request.fix_version,
        label=request.label,
        ticket_type=request.ticket_type,
        text_search=request.text_search,
        limit=request.limit,
    )
    return {"total": len(tickets), "tickets": tickets}


@router.post("/jira-ops/create-ticket")
async def create_jira_ticket(request: JiraCreateRequest):
    data = request.model_dump()
    result = jira_ops_service.create_ticket(data)
    return result


@router.post("/jira-ops/transition")
async def transition_ticket(request: BulkTransitionRequest):
    if len(request.ticket_ids) == 1:
        return jira_ops_service.transition_ticket(request.ticket_ids[0], request.new_status, request.comment)
    return jira_ops_service.bulk_transition(request.ticket_ids, request.new_status, request.comment)


@router.post("/jira-ops/bulk-update")
async def bulk_update_tickets(request: BulkFieldUpdateRequest):
    results = jira_ops_service.bulk_update(request.ticket_ids, request.fields)
    if request.comment:
        for tid in request.ticket_ids:
            jira_ops_service.add_comment(tid, request.comment)
    return {"results": results}


@router.post("/jira-ops/comment")
async def add_jira_comment(request: AddCommentRequest):
    return jira_ops_service.add_comment(request.ticket_id, request.comment, request.author)


@router.post("/jira-ops/test-plan")
async def create_test_plan(request: TestPlanRequest):
    plan = jira_ops_service.create_test_plan(
        name=request.name,
        fix_version=request.fix_version,
        ticket_ids=request.ticket_ids,
        team_id=request.team_id,
    )
    return plan


@router.get("/jira-ops/test-plans")
async def list_test_plans():
    return {"plans": jira_ops_service.list_test_plans()}


@router.post("/jira-ops/test-set")
async def create_test_set(request: TestSetRequest):
    return jira_ops_service.create_test_set(request.plan_id, request.name, request.ticket_ids)


@router.post("/jira-ops/test-execution")
async def create_test_execution(request: TestExecutionRequest):
    return jira_ops_service.create_test_execution(request.plan_id, request.set_id, request.ticket_ids)


@router.post("/jira-ops/mark-result")
async def mark_test_result(request: MarkTestResultRequest):
    result = jira_ops_service.mark_test_result(
        request.exec_id, request.ticket_id, request.result, request.comment
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/jira-ops/sprint-metrics/{sprint_name}")
async def sprint_metrics(sprint_name: str):
    return jira_ops_service.sprint_metrics(sprint_name)


@router.get("/jira-ops/release-metrics/{fix_version}")
async def release_metrics(fix_version: str):
    return jira_ops_service.release_metrics(fix_version)


# ════════════════════════════════════════════════════════════════════════════════
# CRFLT PROJECT INFO
# ════════════════════════════════════════════════════════════════════════════════

_CRFLT_BOARDS = [
    {"id": 37, "name": "Statements", "team_id": "statements", "team_name": "Statements",
     "component": "CR-statements", "sprint": "CRFLT Sprint 1", "jira_url": "https://shrikantpatil.atlassian.net/jira/software/c/projects/CRFLT/boards/37"},
    {"id": 38, "name": "Confirms", "team_id": "confirms", "team_name": "Confirms",
     "component": "CR-confirms", "sprint": "CRFLT Sprint 1", "jira_url": "https://shrikantpatil.atlassian.net/jira/software/c/projects/CRFLT/boards/38"},
    {"id": 39, "name": "Letters", "team_id": "letters", "team_name": "Client Correspondence",
     "component": "CR-letters", "sprint": "CRFLT Sprint 1", "jira_url": "https://shrikantpatil.atlassian.net/jira/software/c/projects/CRFLT/boards/39"},
]


@router.get("/crflt/boards")
async def get_crflt_boards():
    return {"project": "CRFLT", "project_name": "Client Reporting", "boards": _CRFLT_BOARDS}


@router.get("/crflt/tickets")
async def get_crflt_tickets(
    component: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    tickets = jira_ops_service.query_tickets(component=component, status=status, limit=limit)
    return {"total": len(tickets), "tickets": tickets}


@router.get("/crflt/sample-tickets")
async def get_sample_tickets():
    return {"tickets": jira_ops_service.get_all_tickets()}


# ════════════════════════════════════════════════════════════════════════════════
# QUICK TASKS
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/quick/task-types")
async def list_quick_task_types():
    return {
        "tasks": [
            {"id": "regression_tests", "name": "Regression Test Generator", "description": "Generate regression tests from Jira description + PR commits"},
            {"id": "qa_analysis", "name": "Full QA Analysis", "description": "Story quality, alignment, test cases, BDD, step defs"},
            {"id": "ticket_creation", "name": "Bulk Ticket Creator", "description": "Create multiple Jira tickets from a CSV or description"},
            {"id": "bulk_status_update", "name": "Bulk Status Updater", "description": "Transition multiple tickets in one go"},
            {"id": "test_plan_builder", "name": "Test Plan Builder", "description": "Group tickets into a test plan with sets and executions"},
        ]
    }


@router.post("/quick/regression-tests")
async def quick_regression_tests(request: QuickRegressionRequest):
    """Generate a focused regression test set from a Jira ticket and optional PR."""
    logger.info(f"POST /quick/regression-tests  jira_id={request.jira_id}")
    from app.models.schemas import WorkflowSteps

    qa_req = QARequest(
        jira_id=request.jira_id,
        steps=WorkflowSteps(
            ticket_quality=False,
            code_alignment=bool(request.pr_url),
            test_cases=True,
            bdd_scenarios=True,
            step_definitions=True,
        ),
        custom_prompt=(
            f"REGRESSION FOCUS: Generate test cases covering all previously working functionality. "
            f"Additional context: {request.additional_context or 'none provided'}"
        ),
        team_id=request.team_id,
        triggered_by=request.triggered_by,
    )
    result = await workflow_service.run_full_workflow(qa_req)
    return {
        "jira_id": request.jira_id,
        "status": result.status,
        "test_cases": len(result.test_cases),
        "bdd_scenarios": len(result.bdd_scenarios),
        "testcases_csv": result.testcases_csv_path,
        "bdd_feature": result.bdd_feature_path,
        "error": result.error,
    }
