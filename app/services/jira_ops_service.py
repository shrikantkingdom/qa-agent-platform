"""
jira_ops_service.py — Extended Jira operations beyond the basic ticket fetch.

Covers:
  - Smart ticket queries (by status, assignee, sprint, component, label)
  - Bulk status transitions
  - Bulk comments / field updates
  - Ticket creation (Epic, Story, Bug, Sub-task, Test, Test Set, Test Plan, Test Execution)
  - Test execution lifecycle (mark pass/fail, comment, close)
  - Test Plan / Test Set / Test Execution management (Xray-compatible structure)
  - Sprint and release metrics
"""
import re
import uuid
from datetime import datetime
from typing import Optional

import httpx

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Mock Jira dataset (CRFLT project) ─────────────────────────────────────────
# Loaded when use_mock_jira=True. Mirrors a realistic CRFLT project state.

_MOCK_TICKETS: list[dict] = [
    # ── Statements ──
    {
        "id": "CRFLT-101", "type": "Story", "summary": "Generate monthly PDF statement for taxable accounts",
        "status": "In Progress", "priority": "High", "assignee": "dev.smith@wealth.com",
        "reporter": "qa.jones@wealth.com", "component": "Statements", "sprint": "CRFLT Sprint 14",
        "story_points": 8, "labels": ["statements", "pdf", "batch"],
        "description": "As a client, I want to receive a monthly PDF statement for my taxable accounts.",
        "acceptance_criteria": "1. PDF generated for all taxable accounts by 3rd business day.\n2. Zero-transaction accounts show 'no activity' page.\n3. All monetary values rounded to 2dp.\n4. Statement date range is inclusive of start and end dates.",
        "fix_version": "2026-Q2",
    },
    {
        "id": "CRFLT-102", "type": "Bug", "summary": "PDF statement missing page break on multi-page accounts",
        "status": "Open", "priority": "Medium", "assignee": "dev.smith@wealth.com",
        "reporter": "qa.jones@wealth.com", "component": "Statements", "sprint": "CRFLT Sprint 14",
        "story_points": 3, "labels": ["statements", "pdf", "regression"],
        "description": "Multi-holding accounts rendering incorrectly — last page cut off.",
        "acceptance_criteria": "All statements render correctly regardless of holding count.",
        "fix_version": "2026-Q2",
    },
    {
        "id": "CRFLT-103", "type": "Story", "summary": "Batch statement archival to S3 with 7-year retention",
        "status": "Done", "priority": "High", "assignee": "dev.patel@wealth.com",
        "reporter": "pm.chen@wealth.com", "component": "Statements", "sprint": "CRFLT Sprint 13",
        "story_points": 5, "labels": ["statements", "archival", "compliance"],
        "description": "All PDF statements must be archived to S3 with 7-year soft-delete retention.",
        "acceptance_criteria": "1. Statement uploaded to S3 within 30min of generation.\n2. Soft-delete only — hard delete blocked at application level.\n3. Retention metadata tag set on every S3 object.",
        "fix_version": "2026-Q1",
    },
    {
        "id": "CRFLT-104", "type": "Epic", "summary": "Statement 2026 Refresh Programme",
        "status": "In Progress", "priority": "High", "assignee": "pm.chen@wealth.com",
        "reporter": "po.williams@wealth.com", "component": "Statements", "sprint": None,
        "story_points": None, "labels": ["statements", "epic"],
        "description": "Multi-quarter initiative to redesign statement generation and delivery pipeline.",
        "acceptance_criteria": None, "fix_version": "2026-Q2",
    },
    # ── Confirms ──
    {
        "id": "CRFLT-201", "type": "Story", "summary": "Generate T+1 SWIFT MT515 trade confirmation",
        "status": "In Review", "priority": "Critical", "assignee": "dev.Kumar@wealth.com",
        "reporter": "qa.roberts@wealth.com", "component": "Confirms", "sprint": "CRFLT Sprint 14",
        "story_points": 13, "labels": ["confirms", "swift", "regulatory"],
        "description": "Trade confirmations must be generated and dispatched within T+1 business day as per FINRA Rule 10b-10.",
        "acceptance_criteria": "1. MT515 message generated for all equity trades within T+1.\n2. Price tolerance within ±0.0001 of trade price.\n3. BIC validation on all counterparty identifiers.\n4. Duplicate prevention — reprocessed trades do not generate second confirm.",
        "fix_version": "2026-Q2",
    },
    {
        "id": "CRFLT-202", "type": "Bug", "summary": "SWIFT MT518 confirmation missing FX conversion rate",
        "status": "Open", "priority": "High", "assignee": "dev.Kumar@wealth.com",
        "reporter": "qa.roberts@wealth.com", "component": "Confirms", "sprint": "CRFLT Sprint 14",
        "story_points": 5, "labels": ["confirms", "swift", "fx"],
        "description": "FX trade confirmations not including the applied conversion rate in MT518 tag 36.",
        "acceptance_criteria": "MT518 tag 36 must include FX rate applied at time of trade execution.",
        "fix_version": "2026-Q2",
    },
    {
        "id": "CRFLT-203", "type": "Story", "summary": "Exception management dashboard for unmatched confirms",
        "status": "Open", "priority": "Medium", "assignee": "dev.lee@wealth.com",
        "reporter": "pm.chen@wealth.com", "component": "Confirms", "sprint": "CRFLT Sprint 15",
        "story_points": 8, "labels": ["confirms", "exceptions", "dashboard"],
        "description": "Operations team needs a UI to view and manage unmatched trade confirmations.",
        "acceptance_criteria": "1. Dashboard shows all unmatched confirms older than 4 hours.\n2. Operations can manually match or escalate.\n3. SLA timer visible per item.",
        "fix_version": "2026-Q3",
    },
    # ── Letters / Client Correspondence ──
    {
        "id": "CRFLT-301", "type": "Story", "summary": "GDPR suppression enforcement before letter dispatch",
        "status": "In Progress", "priority": "Critical", "assignee": "dev.anderson@wealth.com",
        "reporter": "compliance@wealth.com", "component": "Letters", "sprint": "CRFLT Sprint 14",
        "story_points": 8, "labels": ["correspondence", "gdpr", "suppression", "compliance"],
        "description": "Before any letter is dispatched, the system must check the GDPR suppression list. Suppressed clients must not receive any marketing or regulatory non-essential communications.",
        "acceptance_criteria": "1. GDPR suppression check is performed before every dispatch — no exceptions.\n2. Suppressed client → letter is not dispatched and incident is logged.\n3. Opt-out confirmation letters are always dispatched regardless of suppression status.\n4. Suppression list is refreshed from source of truth every 15 minutes.",
        "fix_version": "2026-Q2",
    },
    {
        "id": "CRFLT-302", "type": "Story", "summary": "Template versioning — lock template on dispatch time",
        "status": "Done", "priority": "High", "assignee": "dev.anderson@wealth.com",
        "reporter": "qa.jones@wealth.com", "component": "Letters", "sprint": "CRFLT Sprint 13",
        "story_points": 5, "labels": ["correspondence", "template", "versioning"],
        "description": "Letter templates must be locked to the version active at time of dispatch. Template updates must not retroactively alter dispatched letters.",
        "acceptance_criteria": "1. Each dispatch job records template_id + version_hash.\n2. Template changes create a new version — existing jobs use locked version.\n3. Audit log shows template version used per dispatch.",
        "fix_version": "2026-Q1",
    },
    {
        "id": "CRFLT-303", "type": "Story", "summary": "Bulk letter dispatch with 1000/min throttle",
        "status": "Open", "priority": "Medium", "assignee": "dev.taylor@wealth.com",
        "reporter": "pm.chen@wealth.com", "component": "Letters", "sprint": "CRFLT Sprint 15",
        "story_points": 13, "labels": ["correspondence", "bulk", "throttling"],
        "description": "Bulk dispatch campaigns must not exceed 1000 letters/minute to protect downstream email and postal gateways.",
        "acceptance_criteria": "1. Dispatch rate is enforced at 1000/min globally, not per sender.\n2. Rate limit breach → batch paused and ops alerted, not silently dropped.\n3. Re-queue mechanism for paused batches.",
        "fix_version": "2026-Q2",
    },
    # ── Cross-team ──
    {
        "id": "CRFLT-401", "type": "Epic", "summary": "Client Reporting 2026-Q2 Release",
        "status": "In Progress", "priority": "High", "assignee": "pm.chen@wealth.com",
        "reporter": "po.williams@wealth.com", "component": None, "sprint": None,
        "story_points": None, "labels": ["release", "q2-2026"],
        "description": "Q2 2026 release for all Client Reporting streams — Statements, Confirms, Letters.",
        "acceptance_criteria": None, "fix_version": "2026-Q2",
    },
    # ── UI & API samples ──
    {
        "id": "CRFLT-501", "type": "Story", "summary": "[UI] Client portal: statement download button on holdings page",
        "status": "Open", "priority": "Medium", "assignee": "dev.ui@wealth.com",
        "reporter": "ux@wealth.com", "component": "Statements", "sprint": "CRFLT Sprint 15",
        "story_points": 5, "labels": ["statements", "ui", "portal"],
        "description": "Add a 'Download Statement' button on the client portal holdings page. Button should only appear when a statement is available for the selected period.",
        "acceptance_criteria": "1. Button visible only when statement available.\n2. Click → PDF downloads (Content-Type: application/pdf).\n3. Statement dated correctly in filename: YYYYMM-account_id.pdf.\n4. Button disabled and tooltip shown when no statement available.",
        "fix_version": "2026-Q2",
    },
    {
        "id": "CRFLT-502", "type": "Story", "summary": "[API] Statement generation REST endpoint v2 with async polling",
        "status": "In Progress", "priority": "High", "assignee": "dev.patel@wealth.com",
        "reporter": "qa.jones@wealth.com", "component": "Statements", "sprint": "CRFLT Sprint 14",
        "story_points": 8, "labels": ["statements", "api", "async"],
        "description": "New v2 API for statement generation. POST /statements/generate returns a job_id immediately; client polls GET /statements/jobs/{job_id} for status. Replaces synchronous v1 endpoint.",
        "acceptance_criteria": "1. POST /v2/statements/generate returns 202 Accepted with job_id.\n2. GET /v2/statements/jobs/{job_id} returns status: queued|processing|completed|failed.\n3. Completed job includes download_url valid for 24 hours.\n4. Failed job includes error_code and human-readable message.\n5. v1 endpoint remains functional until 2026-Q3 deprecation.",
        "fix_version": "2026-Q2",
    },
]

# ── Jira transition map ────────────────────────────────────────────────────────
_TRANSITIONS = {
    "Open":        ["In Progress", "Won't Fix"],
    "In Progress": ["In Review", "Open", "Done"],
    "In Review":   ["Done", "In Progress"],
    "Done":        ["Open"],
    "Won't Fix":   ["Open"],
}

# ── Test artefact stores (in-memory, reset on restart) ────────────────────────
_TEST_PLANS: dict[str, dict] = {}
_TEST_SETS:  dict[str, dict] = {}
_TEST_EXECUTIONS: dict[str, dict] = {}


class JiraOpsService:
    """Extended Jira operations — create, query, bulk update, test lifecycle."""

    # ── Ticket Queries ─────────────────────────────────────────────────────────

    def query_tickets(
        self,
        component: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        sprint: Optional[str] = None,
        fix_version: Optional[str] = None,
        label: Optional[str] = None,
        ticket_type: Optional[str] = None,
        text_search: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        results = list(_MOCK_TICKETS)
        if component:
            results = [t for t in results if t.get("component") == component]
        if status:
            results = [t for t in results if t.get("status", "").lower() == status.lower()]
        if assignee:
            results = [t for t in results if assignee.lower() in (t.get("assignee") or "").lower()]
        if sprint:
            results = [t for t in results if sprint.lower() in (t.get("sprint") or "").lower()]
        if fix_version:
            results = [t for t in results if t.get("fix_version") == fix_version]
        if label:
            results = [t for t in results if label in t.get("labels", [])]
        if ticket_type:
            results = [t for t in results if t.get("type", "").lower() == ticket_type.lower()]
        if text_search:
            q = text_search.lower()
            results = [
                t for t in results
                if q in t.get("summary", "").lower() or q in (t.get("description") or "").lower()
            ]
        return results[:limit]

    # ── Ticket Creation ────────────────────────────────────────────────────────

    def create_ticket(self, ticket_data: dict) -> dict:
        import random as _r
        new_id = f"CRFLT-{_r.randint(600, 999)}"
        ticket = {
            "id": new_id,
            "created": True,
            "created_at": datetime.utcnow().isoformat(),
            **ticket_data,
        }
        _MOCK_TICKETS.append(ticket)
        logger.info(f"Created ticket {new_id}: {ticket_data.get('summary', '')[:60]}")
        return {"id": new_id, "url": f"https://shrikantpatil.atlassian.net/browse/{new_id}", "ticket": ticket}

    # ── Status Transitions ─────────────────────────────────────────────────────

    def transition_ticket(self, ticket_id: str, new_status: str, comment: Optional[str] = None) -> dict:
        ticket = self._find(ticket_id)
        if not ticket:
            return {"success": False, "error": f"{ticket_id} not found"}

        current = ticket.get("status", "Open")
        allowed = _TRANSITIONS.get(current, [])
        if new_status not in allowed:
            return {
                "success": False,
                "error": f"Cannot transition from '{current}' to '{new_status}'. Allowed: {allowed}",
            }

        ticket["status"] = new_status
        ticket["last_transitioned"] = datetime.utcnow().isoformat()
        if comment:
            ticket.setdefault("comments", []).append({
                "author": "qa-agent@system",
                "body": comment,
                "created_at": datetime.utcnow().isoformat(),
            })
        return {"success": True, "ticket_id": ticket_id, "new_status": new_status}

    def bulk_transition(self, ticket_ids: list[str], new_status: str, comment: Optional[str] = None) -> list[dict]:
        return [self.transition_ticket(tid, new_status, comment) for tid in ticket_ids]

    # ── Comments ───────────────────────────────────────────────────────────────

    def add_comment(self, ticket_id: str, comment: str, author: str = "qa-agent") -> dict:
        ticket = self._find(ticket_id)
        if not ticket:
            return {"success": False, "error": f"{ticket_id} not found"}
        ticket.setdefault("comments", []).append({
            "id": str(uuid.uuid4())[:8],
            "author": author,
            "body": comment,
            "created_at": datetime.utcnow().isoformat(),
        })
        return {"success": True, "ticket_id": ticket_id}

    def bulk_comment(self, ticket_ids: list[str], comment: str, author: str = "qa-agent") -> list[dict]:
        return [self.add_comment(tid, comment, author) for tid in ticket_ids]

    # ── Field Updates ──────────────────────────────────────────────────────────

    def update_ticket(self, ticket_id: str, fields: dict) -> dict:
        ticket = self._find(ticket_id)
        if not ticket:
            return {"success": False, "error": f"{ticket_id} not found"}
        allowed_fields = {"assignee", "priority", "story_points", "fix_version", "sprint", "labels"}
        updated = {}
        for k, v in fields.items():
            if k in allowed_fields:
                ticket[k] = v
                updated[k] = v
        return {"success": True, "ticket_id": ticket_id, "updated_fields": updated}

    def bulk_update(self, ticket_ids: list[str], fields: dict) -> list[dict]:
        return [self.update_ticket(tid, fields) for tid in ticket_ids]

    # ── Test Plan Management ────────────────────────────────────────────────────

    def create_test_plan(self, name: str, fix_version: str, ticket_ids: list[str], team_id: str) -> dict:
        plan_id = f"TP-{str(uuid.uuid4())[:8].upper()}"
        plan = {
            "id": plan_id,
            "name": name,
            "fix_version": fix_version,
            "team_id": team_id,
            "ticket_ids": ticket_ids,
            "status": "Draft",
            "created_at": datetime.utcnow().isoformat(),
            "test_sets": [],
        }
        _TEST_PLANS[plan_id] = plan
        return plan

    def create_test_set(self, plan_id: str, name: str, ticket_ids: list[str]) -> dict:
        if plan_id not in _TEST_PLANS:
            return {"error": f"Test plan {plan_id} not found"}
        set_id = f"TS-{str(uuid.uuid4())[:8].upper()}"
        ts = {
            "id": set_id,
            "plan_id": plan_id,
            "name": name,
            "ticket_ids": ticket_ids,
            "status": "Draft",
            "created_at": datetime.utcnow().isoformat(),
        }
        _TEST_SETS[set_id] = ts
        _TEST_PLANS[plan_id]["test_sets"].append(set_id)
        return ts

    def create_test_execution(self, plan_id: str, set_id: Optional[str], ticket_ids: list[str]) -> dict:
        exec_id = f"TEX-{str(uuid.uuid4())[:8].upper()}"
        executions = {
            tid: {"status": "Not Run", "result": None, "comment": None, "executed_at": None}
            for tid in ticket_ids
        }
        tex = {
            "id": exec_id,
            "plan_id": plan_id,
            "set_id": set_id,
            "ticket_ids": ticket_ids,
            "executions": executions,
            "status": "Not Started",
            "created_at": datetime.utcnow().isoformat(),
        }
        _TEST_EXECUTIONS[exec_id] = tex
        return tex

    def mark_test_result(
        self, exec_id: str, ticket_id: str, result: str, comment: Optional[str] = None
    ) -> dict:
        tex = _TEST_EXECUTIONS.get(exec_id)
        if not tex:
            return {"error": f"Execution {exec_id} not found"}
        if ticket_id not in tex["executions"]:
            return {"error": f"Ticket {ticket_id} not in execution {exec_id}"}
        if result not in ("Pass", "Fail", "Blocked", "Not Run"):
            return {"error": "result must be Pass | Fail | Blocked | Not Run"}
        tex["executions"][ticket_id] = {
            "status": "Executed",
            "result": result,
            "comment": comment,
            "executed_at": datetime.utcnow().isoformat(),
        }
        # Update overall status
        results = [e["result"] for e in tex["executions"].values() if e["result"]]
        if all(r == "Pass" for r in results):
            tex["status"] = "Passed"
        elif any(r == "Fail" for r in results):
            tex["status"] = "Failed"
        else:
            tex["status"] = "In Progress"

        return {"success": True, "exec_id": exec_id, "ticket_id": ticket_id, "result": result}

    def get_test_plan(self, plan_id: str) -> Optional[dict]:
        return _TEST_PLANS.get(plan_id)

    def get_test_execution(self, exec_id: str) -> Optional[dict]:
        return _TEST_EXECUTIONS.get(exec_id)

    def list_test_plans(self) -> list[dict]:
        return list(_TEST_PLANS.values())

    # ── Sprint Metrics ──────────────────────────────────────────────────────────

    def sprint_metrics(self, sprint: str) -> dict:
        tickets = self.query_tickets(sprint=sprint)
        return {
            "sprint": sprint,
            "total": len(tickets),
            "by_status": _count_by(tickets, "status"),
            "by_component": _count_by(tickets, "component"),
            "by_type": _count_by(tickets, "type"),
            "total_points": sum(t.get("story_points") or 0 for t in tickets),
            "completed_points": sum(
                (t.get("story_points") or 0) for t in tickets if t.get("status") == "Done"
            ),
        }

    def release_metrics(self, fix_version: str) -> dict:
        tickets = self.query_tickets(fix_version=fix_version)
        return {
            "fix_version": fix_version,
            "total": len(tickets),
            "by_status": _count_by(tickets, "status"),
            "by_component": _count_by(tickets, "component"),
            "bugs": len([t for t in tickets if t.get("type") == "Bug"]),
            "stories": len([t for t in tickets if t.get("type") == "Story"]),
            "done_pct": round(
                100 * len([t for t in tickets if t.get("status") == "Done"]) / max(len(tickets), 1), 1
            ),
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _find(self, ticket_id: str) -> Optional[dict]:
        for t in _MOCK_TICKETS:
            if t["id"] == ticket_id:
                return t
        return None

    def get_ticket(self, ticket_id: str) -> Optional[dict]:
        return self._find(ticket_id)

    def get_all_tickets(self) -> list[dict]:
        return list(_MOCK_TICKETS)


def _count_by(tickets: list[dict], field: str) -> dict:
    counts: dict = {}
    for t in tickets:
        v = t.get(field) or "Unknown"
        counts[v] = counts.get(v, 0) + 1
    return counts


jira_ops_service = JiraOpsService()
