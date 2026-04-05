# Innovation Document — QA Agent Platform
## Client Reporting / Wealth Management — Quality Automation Initiative

---

## 1. The Problem: Manual QA at Scale

### 1.1 What the Process Looked Like Before

The QA workflow for the three Wealth Management delivery teams (Statements, Confirms, Letters) was
entirely manual. A typical sprint cycle played out like this:

**Ticket intake (Day 1–2)**
A QA engineer receives a Jira ticket with a summary, an informal description, and — if the team
diligently wrote them — a few bullet-point acceptance criteria. There is no structural quality check.
Vague tickets progress to sprint without challenge because the QA engineer lacks a fast, structured
way to raise quality issues early.

**Test design (Day 3–5)**
The QA engineer reads the ticket, mentally maps out scenarios, and writes test cases in Jira or a
spreadsheet from scratch. For a moderately complex financial document ticket (e.g., a new statement
type with three delivery channels and edge cases around GDPR suppression and archival retention),
this takes **3–5 hours per ticket**. Across three teams, a two-week sprint typically contained
15–25 tickets requiring meaningful test design — consuming **45–125 hours** of QA time per sprint
on test case writing alone.

**BDD scenario authoring (Day 4–6)**
Where BDD was practised, a separate session was needed to convert test cases into Gherkin. This was
often deferred under sprint pressure. Feature files drifted from the actual implementation. The
automation repo frequently contained outdated `.feature` files that no longer reflected real product
behaviour.

**Code-requirement alignment (throughout sprint)**
There was no structured way to check whether developer commits addressed the acceptance criteria. QA
engineers relied on informal communication, manual PR reading, and late-sprint exploratory testing.
Alignment issues (missed requirements, scope creep, over-engineering) were found in UAT rather than
during the sprint.

**Report generation (End of sprint)**
Sprint-end QA reports were assembled manually from Jira queries, test run exports, and notes —
taking **2–4 hours per report** per team. For three teams, this was **6–12 hours per sprint** of low-
value assembly work.

### 1.2 Quantified Manual Effort Baseline

| Activity | Hours per Ticket | Tickets per Sprint | Hours per Sprint |
|----------|-----------------|-------------------|-----------------|
| Test case design | 3–5 hr | 15–25 | 45–125 hr |
| BDD scenario authoring | 1–2 hr | 8–12 | 8–24 hr |
| Alignment check (manual) | 0.5–1 hr | 15–25 | 7–25 hr |
| Ticket quality review | 0.5 hr | 15–25 | 7–12 hr |
| Sprint report assembly | — | — | 6–12 hr per 3 teams |
| **Total per sprint (3 teams)** | | | **~73–198 hours** |

At a conservative UK contractor rate of £400/day for a senior QA engineer, the manual burden equates
to **£9,000–£24,750 per sprint** in fully-loaded QA labour — for activities that are largely
repeatable and pattern-driven.

### 1.3 Root Causes

1. **No ticket quality gate** — tickets are not structurally assessed before sprint commitment
2. **Test design is blank-page work** — QA engineers draft from memory and past experience, producing inconsistent output
3. **No automated alignment verification** — code changes are not traced back to acceptance criteria
4. **BDD is aspirational, not operational** — tooling friction means Gherkin authoring is deferred
5. **Report generation is manual assembly** — no system aggregates and formats QA results automatically
6. **No team-aware context** — generic QA guidance ignores domain rules (GDPR suppression, T+1 SLA, batch idempotency, etc.)

---

## 2. The Strategy: AI-Augmented, Human-Governed QA

### 2.1 Design Principles

The platform was designed around three principles:

**1. Augment, don't replace.**
QA engineers retain full editorial control. The AI generates a draft; the engineer reviews, edits,
and approves before anything is committed to Jira or pushed to the automation repo. This preserves
accountability and correctness while eliminating blank-page friction.

**2. Domain-aware, not generic.**
Generic AI advice ("add error handling", "test edge cases") is not actionable for a regulated
financial document platform. The system is loaded with team-specific context — Jira project keys,
business rules, automation conventions, compliance requirements — so generated outputs reference
real fixtures, real paths, and real regulatory constraints.

**3. Upstream-shifted quality.**
The most expensive rework happens when quality issues are found in UAT or production. The platform
deliberately targets the earliest possible intervention: ticket quality is scored at intake, code
alignment is checked during the sprint, and test coverage gaps are surfaced before sprint end.

### 2.2 Strategy Phases

**Phase 1 — Prove the loop (core workflow)**
Build a single trigger (`POST /run-qa`) that takes a Jira ticket ID and returns: a quality score,
alignment analysis, test cases, BDD scenarios, and pytest-bdd step definitions. The output is a
structured report the QA engineer reviews before any action is taken. Prove value on one team first.

**Phase 2 — Operationalise the review (UI layer)**
Build a React-based review interface so QA engineers can edit, approve, and upload directly — no
API knowledge required. Add release-level batch processing and GitHub push functionality.

**Phase 3 — Team segregation and context depth**
Extend from a single generic config to per-team context files — each embedding team-specific Jira
fields, business rules, automation paths, and compliance constraints. This transitions the platform
from a generic QA tool to a wealth-management-domain-aware assistant.

**Phase 4 — Shift-left automation (roadmap)**
Integrate with GitHub Actions so that opening a PR triggers the QA workflow automatically. The AI
report is posted as a PR comment before code review begins, shifting QA involvement to the moment
code hits version control.

---

## 3. Implementation: How It Was Built

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  QA Agent Platform — Runtime Architecture                                   │
│                                                                             │
│  ┌──────────┐    REST     ┌────────────────────────────────────────────┐   │
│  │  React   │◄──────────►│  FastAPI (app.py)                           │   │
│  │  UI      │            │  ├── /run-qa                (workflow)      │   │
│  └──────────┘            │  ├── /upload-to-jira        (Jira write)    │   │
│                          │  ├── /push-tests            (GitHub write)  │   │
│                          │  ├── /release-qa            (batch)         │   │
│                          │  └── /team-config           (team ctx)      │   │
│                          └──────────────┬─────────────────────────────┘   │
│                                         │                                   │
│                          ┌──────────────▼─────────────────────────────┐   │
│                          │  workflow_service.py (orchestrator)         │   │
│                          │  1. jira_service     → fetch ticket         │   │
│                          │  2. github_service   → fetch commits        │   │
│                          │  3. ai_service       → all LLM calls        │   │
│                          │  4. bdd_service      → file generation      │   │
│                          │  5. report_service   → HTML report          │   │
│                          └──────────────┬─────────────────────────────┘   │
│                                         │                                   │
│           ┌─────────────────────────────▼─────────────────────────────┐   │
│           │  External Integrations                                      │   │
│           │  ├── Jira Cloud REST API  (read + write)                    │   │
│           │  ├── GitHub REST API      (commits + push + PR)             │   │
│           │  └── LLM Provider Layer  (9 providers, runtime-switchable)  │   │
│           │      GitHub Models gpt-4o  ←  active provider              │   │
│           └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 The 9-Step Workflow

Each `POST /run-qa` request runs 9 sequential steps:

| Step | Operation | Output |
|------|-----------|--------|
| 1 | Fetch Jira ticket (title, description, acceptance criteria, labels, custom fields) | `ticket_dict` |
| 2 | Fetch recent GitHub commits (last 20 commits, diff summaries) | `commits_dict` |
| 3 | AI validates ticket quality → JSON score + issues + strengths | `quality_score`, `issues` |
| 4 | AI checks requirement–code alignment → coverage gaps, over-implementation | `alignment_result` |
| 5 | AI generates 8–15 test cases → categorised (smoke, regression, edge case, negative) | `test_cases[]` |
| 6 | Save test cases to CSV | `csv_path` |
| 7 | AI generates BDD scenarios → Gherkin feature_name + scenarios[] | `bdd_scenarios[]` |
| 8 | AI generates pytest-bdd step definitions → complete step def files | `step_definitions[]` |
| 9 | Report service renders HTML report | `report_path` |

### 3.3 Provider-Agnostic LLM Layer

**Why it matters:** GitHub Models API (free, gpt-4o) is used in development. Enterprise deployments
require Azure OpenAI. Different latency/cost profiles justify Anthropic Claude for complex reasoning
tasks, Groq for high-speed generation, and Ollama for air-gapped environments.

**Implementation:** `providers.py` maps a provider name to `{base_url, api_key, model, timeout}`.
`AsyncOpenAI(base_url=..., api_key=...)` is constructed per call. Switching provider requires one
environment variable change: `LLM_PROVIDER=azure`.

```python
# One env var switches everything:
LLM_PROVIDER=github   → GitHub Models API / gpt-4o  (current)
LLM_PROVIDER=azure    → Azure OpenAI
LLM_PROVIDER=anthropic → Claude 3.5 Sonnet
LLM_PROVIDER=ollama   → local Ollama server
```

### 3.4 Team-Scoped Context Injection

Each LLM prompt is prefixed with a team-specific context block loaded from
`config/teams/<team>.md`. This transforms generic AI output into domain-specific output:

**Without team context:**
> "Test that the form validates required fields and handles edge cases."

**With Statements team context:**
> "Test PDF date range inclusivity (off-by-one is historically recurring). Test zero-transaction
> period generates 'no activity' statement, not error. Test batch idempotency — re-run must not
> produce duplicate records. Verify 7-year soft-delete retention (hard delete is compliance
> violation)."

### 3.5 Staged Review Architecture

The platform enforces a deliberate human gate:
- `POST /run-qa` → generates report, saves locally, returns to UI
- User reviews, edits summary, removes false positives from issues list
- `POST /upload-to-jira` → separate explicit action; user-approved content only
- `POST /push-tests` → separate explicit action; pushes step defs to automation repo branch

This is intentional. Auto-posting AI-generated content to the authoritative project record was
rejected as a design choice. QA engineer judgment remains required for every commit to Jira.

### 3.6 pytest-bdd Integration

The automation repo (`playwright_project`) uses `pytest-bdd 7.x` with `playwright.sync_api` and
a Page Object Model. Generated step definitions follow the exact conventions in the repo:

```python
# Generated output matches the repo's existing pattern:
from pathlib import Path
from pytest_bdd import given, when, then, parsers, scenarios
from pages.statements_page import StatementsPage

FEATURES_DIR = Path(__file__).parent.parent.parent.parent / "features"
scenarios(str(FEATURES_DIR / "statements" / "statement_generation.feature"))

@given("a statement run is triggered for account {account_id}", target_fixture="stmt_page")
def given_statement_run(page, config, account_id):
    sp = StatementsPage(page)
    sp.open(config.ui_base_url)
    sp.trigger_statement_run(account_id)
    return sp

@then("a PDF statement should be generated")
def then_pdf_generated(stmt_page):
    assert stmt_page.is_pdf_available()
```

The `target_fixture` pattern means `@given` steps return Page Object instances as pytest
fixtures — exactly how the existing `test_login_steps.py` is structured in the repo.

---

## 4. How Manual Effort Was Reduced

| Activity | Before | After | Saving |
|----------|--------|-------|--------|
| Test case design | 3–5 hr/ticket | 15 min review & edit | ~85% |
| BDD authoring | 1–2 hr/ticket | 10 min review | ~87% |
| Alignment check | 0.5–1 hr/ticket | Automatic, always-on | ~100% |
| Ticket quality review | 0.5 hr/ticket | Instant, scored | ~90% |
| Sprint report generation | 6–12 hr per sprint | Automatic per ticket | ~95% |
| Step definition scaffolding | 2–4 hr/ticket | Generated, push-to-branch | ~90% |

**Projected saving:** 60–80 hours per sprint across three teams, representing £7,500–£10,000 in
fully-loaded QA labour per sprint at current team rates.

**Qualitative improvements:**
- Ticket quality issues are raised at intake, not at UAT
- BDD feature files stay in sync with implementation (generated from the same acceptance criteria)
- Coverage gaps are flagged during the sprint, not discovered after release
- QA engineers spend time on judgment, edge case exploration, and domain reasoning — not assembly

---

## 5. Scalability Design

### 5.1 New Team Onboarding
Adding a fourth team requires: create `config/teams/<team>.md` with project key, Jira custom fields,
automation paths, business rules, and test environment URLs. No code changes. The team context file
is loaded dynamically at request time. Estimated onboarding time: **30–60 minutes** for a new team
context file.

### 5.2 New LLM Provider
Adding a new LLM provider requires: add one entry to `providers.py` (6 lines of code) and set the
environment variable. All 9 workflow steps automatically use the new provider.

### 5.3 New Workflow Step
Each step in `workflow_service.py` is independently ordered and structured. Adding a step (e.g.,
security test case generation, accessibility coverage check) requires adding one prompt builder in
`ai_service.py` and one call in the workflow pipeline. No architectural changes needed.

### 5.4 Multi-Instance Deployment
The current architecture uses local `outputs/` for artefact storage. For horizontal scaling:
- Replace `outputs/` with an S3 bucket (URL-addressable, shared across instances)
- Use PostgreSQL to store QA results and report metadata
- API contract is unchanged — only the storage backend changes

### 5.5 Release-Level Batch Processing
`POST /release-qa` accepts a Jira fixVersion and processes all tickets in that release in parallel
(bounded by a configurable concurrency limit to avoid LLM rate limiting). Large releases (50+
tickets) run in under 10 minutes on GitHub Models API rate limits.

---


> **Q&A sections** (Problem, Design, Scalability, Execution Models) have been consolidated into
> [10-interview-qa.md](10-interview-qa.md).
> **Execution Models** (all 8 trigger modes with comparison table) have been moved to
> [06-deployment.md](06-deployment.md).

---
## 6. End-to-End Flow (Detailed)

```
QA Engineer enters Jira ticket ID in the UI
        │
        ▼
POST /run-qa  →  workflow_service.run_full_workflow()
        │
        ├─ [1/9] jira_service.get_ticket()
        │         → title, description, AC, labels, custom fields, fix version
        │
        ├─ [2/9] github_service.get_recent_commits()
        │         → last 20 commits from configured repo, diff summaries
        │
        ├─ [3/9] ai_service.validate_ticket()
        │         → quality_score (0–100), grade (A–F), issues[], strengths[]
        │
        ├─ [4/9] ai_service.check_alignment()
        │         → coverage_gaps[], over_implementation[], alignment_score
        │
        ├─ [5/9] ai_service.generate_test_cases()
        │         → 8–15 test cases: id, scenario, steps, expected_result, tags
        │
        ├─ [6/9] bdd_service.save_test_cases_csv()
        │         → outputs/bdd/{jira_id}_test_cases.csv
        │
        ├─ [7/9] ai_service.generate_bdd_scenarios()
        │         → feature_name, scenarios[]: given/when/then/tags
        │
        ├─ [8/9] ai_service.generate_step_definitions()
        │         → pytest-bdd step def files (given/when/then decorated functions)
        │         → saved to outputs/bdd/{jira_id}_steps.py
        │
        └─ [9/9] report_service.generate_html_report()
                  → outputs/reports/{jira_id}_report.html
        │
QAResponse → rendered in UI (quality score, issues, test cases, BDD, step defs)
        │
QA engineer reviews: edits summary, removes false positives, adjusts test cases
        │
        ├─ "Upload to Jira" → POST /upload-to-jira
        │   → Creates Jira comment with formatted report + attaches HTML
        │
        └─ "Push Tests" → POST /push-tests
            → Pushes _steps.py to automation repo branch
            → Opens PR against playwright_project/main
```

---

## 7. Future Roadmap

| Phase | Feature | Estimated Value |
|-------|---------|----------------|
| 1 *(delivered)* | Core QA workflow, review UI, Jira upload, pytest-bdd push | Foundation — 70% effort reduction |
| 2 | GitHub Actions integration — trigger on PR open, post report as PR comment | Shift-left to code review |
| 3 | MCP tool server — expose steps as composable AI agent tools | Agent-native integration |
| 4 | Live test execution — run pushed tests, pull results, close the loop | Full feedback cycle |
| 5 | Quality trend dashboards — score trend, coverage%, regression rate per team | Sprint-level insight |
| 6 | Multi-repo mapping — one Jira project → multiple GitHub repos (service + UI + automation) | Enterprise scale |
| 7 | Accessibility coverage generation — WCAG 2.1 test case generation from UI tickets | Proactive a11y compliance |

│  QA Agent Platform — Runtime Architecture                                   │
│                                                                             │
│  ┌──────────┐    REST     ┌────────────────────────────────────────────┐   │
│  │  React   │◄──────────►│  FastAPI (app.py)                           │   │
