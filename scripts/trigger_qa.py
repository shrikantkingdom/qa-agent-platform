#!/usr/bin/env python3
"""
scripts/trigger_qa.py
─────────────────────
Called by the GitHub Actions workflow (Step 5) to:
  1. POST /api/v1/run-qa  with structured parameters
  2. Poll for completion (or wait for synchronous response)
  3. Write a qa_summary_<jira_id>.json side-car file consumed by render_summary.py
  4. Optionally call /api/v1/jira/{id}/upload-report and /api/v1/github/create-pr

Can also be run locally:
  python scripts/trigger_qa.py --jira-id CRFLT-123 --team-id statements
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_bool(value: str) -> bool:
    return str(value).lower() in ("true", "1", "yes")


def _post(api_base: str, path: str, payload: dict, *, fatal: bool = True) -> dict:
    """POST to the API.  If fatal=False, returns {} on error instead of exiting."""
    url = f"{api_base.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"[trigger_qa] HTTP {exc.code} from {url}:\n{body}", file=sys.stderr)
        if fatal:
            sys.exit(1)
        return {}
    except urllib.error.URLError as exc:
        print(f"[trigger_qa] Cannot reach {url}: {exc.reason}", file=sys.stderr)
        if fatal:
            sys.exit(1)
        return {}


def _get(api_base: str, path: str) -> dict:
    url = f"{api_base.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"[trigger_qa] GET {url} failed: {exc}", file=sys.stderr)
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Trigger QA Workflow via REST API")
    ap.add_argument("--jira-id",       required=True)
    ap.add_argument("--team-id",       required=True)
    ap.add_argument("--triggered-by",  default="github-actions")
    ap.add_argument("--quality",       default="true")
    ap.add_argument("--alignment",     default="true")
    ap.add_argument("--test-cases",    default="true")
    ap.add_argument("--bdd",           default="true")
    ap.add_argument("--step-defs",     default="true")
    ap.add_argument("--step-style",    default="pytest_bdd")
    ap.add_argument("--upload-jira",   default="false")
    ap.add_argument("--create-pr",     default="false")
    ap.add_argument("--custom-prompt", default="")
    ap.add_argument("--api-base",      default="http://localhost:8000/api/v1")
    ap.add_argument("--output-dir",    default="outputs")
    args = ap.parse_args()

    print(f"[trigger_qa] Jira: {args.jira_id}  Team: {args.team_id}  Triggered-by: {args.triggered_by}")

    # ── Build workflow payload ──────────────────────────────────────────────
    payload = {
        "jira_id": args.jira_id,
        "team_id": args.team_id,
        "triggered_by": args.triggered_by,
        "steps": {
            "ticket_quality":    _parse_bool(args.quality),
            "code_alignment":    _parse_bool(args.alignment),
            "test_cases":        _parse_bool(args.test_cases),
            "bdd_scenarios":     _parse_bool(args.bdd),
            "step_definitions":  _parse_bool(args.step_defs),
            "step_def_style":    args.step_style,
        },
        "custom_prompt": args.custom_prompt or None,
    }

    # ── POST to run-qa ──────────────────────────────────────────────────────
    print("[trigger_qa] Calling POST /run-qa ...")
    result = _post(args.api_base, "/run-qa", payload)

    # ── Extract nested result fields ────────────────────────────────────────
    # QAResponse shape: {success, message, run_id, data: QAWorkflowResult}
    # QAWorkflowResult: {validation: {grade, quality_score, issues, summary}, ...}
    run_id     = result.get("run_id", "unknown")
    qa_data    = result.get("data") or {}
    validation = qa_data.get("validation") or {}
    alignment  = qa_data.get("alignment") or {}
    grade      = validation.get("grade", "N/A")
    overall    = validation.get("quality_score", 0)

    outputs = {
        "report":          qa_data.get("report_path"),
        "testcases_csv":   qa_data.get("testcases_csv_path"),
        "testcases_json":  qa_data.get("testcases_json_path"),
        "bdd_feature":     qa_data.get("bdd_feature_path"),
    }

    print(f"[trigger_qa] Run ID  : {run_id}")
    print(f"[trigger_qa] Grade   : {grade}")
    print(f"[trigger_qa] Score   : {overall}")

    issues = validation.get("issues", [])
    print(f"[trigger_qa] Issues  : {len(issues)}")
    for iss in issues[:5]:
        severity = iss.get("severity", "")
        msg      = iss.get("message",  iss.get("description", ""))
        print(f"            • [{severity}] {msg}")
    if len(issues) > 5:
        print(f"            … and {len(issues) - 5} more (see artefacts)")

    # ── Save summary side-car ───────────────────────────────────────────────
    summary_path = Path(f"qa_summary_{args.jira_id.replace('/', '_')}.json")
    scores = {}
    if validation:
        scores["ticket_quality"] = overall
    if alignment:
        scores["code_alignment"] = alignment.get("score", 0)

    summary = {
        "run_id":        run_id,
        "jira_id":       args.jira_id,
        "team_id":       args.team_id,
        "triggered_by":  args.triggered_by,
        "grade":         grade,
        "overall_score": overall,
        "scores":        scores,
        "issues_count":  len(issues),
        "outputs":       outputs,
    }
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"[trigger_qa] Summary saved → {summary_path}")

    # ── Optional: upload report to Jira ────────────────────────────────────
    if _parse_bool(args.upload_jira):
        print("[trigger_qa] Uploading report to Jira ticket ...")
        # Build a JiraUploadRequest-compatible payload from run results
        issue_msgs = [i.get("message", str(i)) for i in issues]
        report_fname = Path(outputs["report"]).name if outputs.get("report") else None
        upload_payload = {
            "jira_id":        args.jira_id,
            "edited_summary": validation.get("summary", "QA analysis completed via GitHub Actions."),
            "edited_issues":  issue_msgs,
            "quality_score":  overall,
            "grade":          grade if grade != "N/A" else "C",
            "attach_report":  bool(report_fname),
            "report_filename": report_fname,
        }
        up_result = _post(args.api_base, "/upload-to-jira", upload_payload, fatal=False)
        if up_result:
            print(f"[trigger_qa] Jira upload: {up_result.get('status', 'ok')}")
        else:
            print("[trigger_qa] WARNING: Jira upload failed (non-fatal, continuing)")

    # ── Optional: create PR ─────────────────────────────────────────────────
    if _parse_bool(args.create_pr):
        print("[trigger_qa] Creating automation PR ...")
        pr_result = _post(args.api_base, "/github/create-pr",
                          {"run_id": run_id, "jira_id": args.jira_id}, fatal=False)
        pr_url = pr_result.get("pr_url", "") if pr_result else ""
        if pr_url:
            print(f"[trigger_qa] PR created: {pr_url}")
        else:
            print("[trigger_qa] WARNING: PR creation failed or returned no URL (non-fatal)")

    # ── Exit code: non-zero if grade is F ─────────────────────────────────
    if str(grade).upper() == "F":
        print("[trigger_qa] Grade F — marking workflow as FAILED", file=sys.stderr)
        sys.exit(2)

    print("[trigger_qa] Done.")


if __name__ == "__main__":
    main()
