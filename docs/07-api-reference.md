# 07 — API Reference

All endpoints are prefixed with `/api/v1`. Interactive docs available at `/docs` (Swagger) and `/redoc` (ReDoc).

---

## Core Workflow

### `POST /run-qa`

Execute the full 9-step QA workflow for a Jira ticket.

**Request:**
```json
{
  "jira_id": "CRFLT-1",
  "team_id": "statements",
  "release": "v2.1.0",
  "post_to_jira": true,
  "custom_prompt": "Focus on GDPR compliance",
  "triggered_by": "web_ui",
  "steps": {
    "ticket_quality": true,
    "code_alignment": true,
    "test_cases": true,
    "bdd_scenarios": true,
    "step_definitions": true
  }
}
```

**Response:** `QAResponse` — quality score, validation issues, test cases, BDD scenarios, alignment results, output file paths, run_id.

### `POST /run-release`

Batch-process all tickets in a Jira release.

**Request:**
```json
{
  "release": "v2.1.0",
  "team_id": "statements",
  "include_bdd": true,
  "custom_prompt": ""
}
```

**Response:** Array of per-ticket results with scores and file paths.

### `POST /quick/regression-tests`

Generate a focused regression test set (skips ticket quality step).

**Request:**
```json
{
  "jira_id": "CRFLT-5",
  "team_id": "confirms",
  "pr_url": "https://github.com/org/repo/pull/42",
  "additional_context": "Focus on SWIFT message validation"
}
```

---

## Jira Integration

### `POST /upload-to-jira`

Post a reviewed QA summary as a Jira comment and optionally attach the HTML report.

**Request:**
```json
{
  "jira_id": "CRFLT-1",
  "quality_score": 78,
  "grade": "B",
  "edited_summary": "Ticket is well-structured with clear AC...",
  "edited_issues": ["Missing edge case for zero-balance", "No accessibility criteria"],
  "attach_report": true,
  "report_filename": "CRFLT-1_report.html"
}
```

### `POST /webhooks/jira`

Receive a trigger from Jira Automation or a Forge app. Returns 202 immediately; workflow runs in background.

**Headers:** `X-Webhook-Secret: <your_secret>`

**Request:**
```json
{
  "jira_id": "CRFLT-1",
  "components": ["CR-statements"],
  "post_to_jira": true
}
```

See [03-jira-webhook-setup.md](03-jira-webhook-setup.md) for full webhook setup.

---

## GitHub Integration

### `POST /push-playwright-tests`

Push generated pytest-bdd step definitions to the automation repo and optionally open a PR.

**Request:**
```json
{
  "jira_id": "CRFLT-1",
  "create_pr": true,
  "branch_prefix": "qa-agent"
}
```

---

## Outputs

### `GET /outputs/{type}/{filename}`

Download a generated artefact. Opens inline for HTML/feature/py files; downloads for CSV/JSON.

| `type` | Example filename |
|--------|-----------------|
| `reports` | `CRFLT-1_report.html` |
| `testcases` | `CRFLT-1_testcases.csv` or `.json` |
| `bdd` | `CRFLT-1.feature` or `CRFLT-1_steps.py` |

### `GET /testcase-download/{jira_id}/{fmt}`

Convenience shortcut. `fmt` = `csv` | `json` | `bdd` | `steps`.

```bash
curl http://localhost:8000/api/v1/testcase-download/CRFLT-1/csv -o testcases.csv
```

---

## Team Configuration

### `GET /teams`

List all available team context files.

### `GET /teams/{team_id}`

Return the Markdown content of a team's context file.

### `PUT /teams/{team_id}`

Create or update a team context file from the UI.

**Request:**
```json
{
  "content": "# Statements Team\n\n## Business Rules\n..."
}
```

---

## Jira Operations

### `POST /jira-ops/query`

Query tickets with filters (component, status, assignee, sprint, label, text search).

### `POST /jira-ops/create-ticket`

Create a new Jira ticket.

### `POST /jira-ops/transition`

Transition one or more tickets to a new status.

### `POST /jira-ops/bulk-update`

Bulk-update fields on multiple tickets.

### `POST /jira-ops/comment`

Add a comment to a ticket.

### `POST /jira-ops/test-plan`

Create a test plan grouping tickets for a release.

### `GET /jira-ops/test-plans`

List all test plans.

### `POST /jira-ops/test-set`

Create a test set within a plan.

### `POST /jira-ops/test-execution`

Create a test execution for a set.

### `POST /jira-ops/mark-result`

Mark a test execution result (pass/fail/blocked).

### `GET /jira-ops/sprint-metrics/{sprint_name}`

Sprint-level metrics (ticket counts, scores, coverage).

### `GET /jira-ops/release-metrics/{fix_version}`

Release-level metrics.

---

## CRFLT Project

### `GET /crflt/boards`

Returns project info and board list for the CRFLT project.

### `GET /crflt/tickets`

Query CRFLT tickets. Optional filters: `component`, `status`, `limit`.

### `GET /crflt/sample-tickets`

Return all sample tickets in the system.

---

## System

### `GET /health`

Liveness probe. Returns provider, model, Jira/GitHub connection status.

```json
{
  "status": "healthy",
  "service": "QA Agent Platform",
  "llm_provider": "github",
  "llm_model": "gpt-4o",
  "jira": "live",
  "github": "live"
}
```

### `GET /providers`

List all supported LLM providers and their models.

### `GET /config`

Non-sensitive active configuration (for UI status bar).

---

## History

### `GET /history`

List recent workflow runs. Filters: `team_id`, `jira_id`, `task_type`, `limit`, `offset`.

### `GET /history/stats`

Aggregate statistics across all runs.

### `GET /history/{run_id}`

Details for a specific run.

### `DELETE /history/{run_id}`

Delete a run record.

---

## Upstream & Test Data

### `GET /upstream/systems`

List available upstream system stubs.

### `POST /upstream/{system_id}`

Call an upstream system stub.

### `POST /test-data`

Discover or create test data. `action` = `discover` | `create`.
