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

## 6. Questions & Answers

### About the Problem

**Q: Why not just use Jira plugins or existing test management tools like Zephyr or Xray?**
A: Jira plugins manage test execution but do not generate test cases, validate ticket quality, or
check requirement-code alignment. They require a QA engineer to author everything manually and
then enter it into the tool. The platform automates the authoring step — the most time-consuming
part — and integrates with existing Jira workflows, not against them.

**Q: How do you know the AI-generated test cases are correct?**
A: They are not assertions of correctness — they are a structured first draft. The QA engineer
reviews every generated test case before it is uploaded to Jira. The platform's value is in
reducing blank-page authoring time by 85%, not in removing the engineer's judgment. Incorrect
suggestions are edited or deleted in the review UI.

**Q: Couldn't a junior QA write faster test cases once experienced?**
A: Experienced QAs write faster test cases, yes. But they still start from scratch on every ticket,
which is cognitively expensive and inconsistent across engineers. The platform produces a
consistent structure (test ID, scenario, steps, expected result, tags, priority) that a junior and
a senior both review and improve. Consistency at scale is the larger benefit.

**Q: What is the ROI case?**
A: At 60–80 hours saved per sprint across three teams, and 26 sprints per year (2-week sprints):
- Hours saved annually: 1,560–2,080 hr
- At £400/day (8hr day): £78,000–£104,000/year in engineering time
- Platform build + maintenance estimated at £30,000 annually
- **Net annual saving: ~£48,000–£74,000** — not counting the compounding value of earlier defect
  detection.

---

### About the Design

**Q: Why FastAPI rather than a Python CLI tool?**
A: The platform needs to serve a React UI, expose endpoints to GitHub Actions webhooks, and
potentially serve multiple concurrent users. A REST API supports all of these use cases. A CLI
tool would require reimplementing the HTTP server layer later.

**Q: Why not use LangChain or a full agent framework?**
A: The workflow is deterministic: 9 steps, always in the same order, with the same inputs and
expected JSON outputs. LangChain adds abstraction and dependency surface area without benefit for
a sequential, structured-output pipeline. Direct `AsyncOpenAI` calls with structured JSON prompts
are simpler, more debuggable, and faster.

**Q: Why is the human review step mandatory and not optional?**
A: Because auto-posting AI content to Jira corrupts the authoritative project record. Sprint
velocity is measured from Jira. QA coverage decisions are made from Jira. If the AI posts
hallucinated test cases, teams make planning decisions based on false data. The staged review is a
correctness gate, not a friction point.

**Q: Why are team context files plain Markdown rather than a database or structured config?**
A: Markdown files are editable by non-engineers (QA leads, business analysts) without a UI.
They are version-controlled in Git alongside the application, so context changes are auditable.
Structured database records would require a migration every time a business rule changes.

**Q: How does the platform handle a Jira ticket with no acceptance criteria?**
A: The quality validator scores it low (typically 30–50/100) and generates a specific issue:
`{"field": "acceptance_criteria", "severity": "critical", "message": "No acceptance criteria
defined..."}`. The QA engineer is prompted to request clarification before proceeding. The
workflow can still generate test cases using the description alone, but the quality gate is explicit.

---

### About Scalability and Risk

**Q: What happens if the LLM generates a hallucinated business rule?**
A: Two defences. First, the team context file provides explicit business rules that ground the LLM
output. Second, the QA engineer reviews all generated content before upload. A hallucinated rule
("statements are retained for 5 years") would be caught by a QA engineer who knows the retention
policy is 7 years. The platform does not auto-publish.

**Q: What if the LLM provider goes down?**
A: The platform falls back to mock responses when `call_structured()` raises an exception, and
`LLM_PROVIDER` can be switched to any of 9 supported providers in seconds by changing one
environment variable. Outage impact is the current provider; the workflow is provider-agnostic.

**Q: How does this scale to a team with 100 tickets per sprint?**
A: The `POST /release-qa` endpoint processes a full release in parallel. 100 tickets at the
current GitHub Models API rate limit (60 RPM for gpt-4o) takes approximately 10–15 minutes for
full analysis. The bottleneck is LLM throughput, not the platform. An Azure OpenAI deployment
with higher rate limits would process the same batch in under 4 minutes.

**Q: What is the privacy and data security posture?**
A: Credentials are stored in environment variables, never in application code or API responses.
Jira and GitHub tokens are never logged or serialised. The LLM provider receives ticket text and
commit summaries — no PII (customer names, account numbers, transaction data) should exist in
Jira tickets; if it does, that is a pre-existing data hygiene issue, not introduced by this
platform. Outputs are stored locally in `outputs/` with no external exposure.

**Q: Can this be used across other business units, not just Wealth Management?**
A: Yes. New teams are onboarded by creating a single Markdown context file with no code changes.
The workflow, UI, and LLM prompts are generic by design; team context files provide the domain
specificity. An Investment Banking or Retail Banking team could be onboarded in under an hour.

---

## 7. End-to-End Flow (Detailed)

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

## 8. Future Roadmap

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

## 6. Questions & Answers

### About the Problem

**Q: Why not just use Jira plugins or existing test management tools like Zephyr or Xray?**
A: Jira plugins manage test execution but do not generate test cases, validate ticket quality, or
check requirement-code alignment. They require a QA engineer to author everything manually and
then enter it into the tool. The platform automates the authoring step — the most time-consuming
part — and integrates with existing Jira workflows, not against them.

**Q: How do you know the AI-generated test cases are correct?**
A: They are not assertions of correctness — they are a structured first draft. The QA engineer
reviews every generated test case before it is uploaded to Jira. The platform's value is in
reducing blank-page authoring time by 85%, not in removing the engineer's judgment. Incorrect
suggestions are edited or deleted in the review UI.

**Q: Couldn't a junior QA write faster test cases once experienced?**
A: Experienced QAs write faster test cases, yes. But they still start from scratch on every ticket,
which is cognitively expensive and inconsistent across engineers. The platform produces a
consistent structure (test ID, scenario, steps, expected result, tags, priority) that a junior and
a senior both review and improve. Consistency at scale is the larger benefit.

**Q: What is the ROI case?**
A: At 60–80 hours saved per sprint across three teams, and 26 sprints per year (2-week sprints):
- Hours saved annually: 1,560–2,080 hr
- At £400/day (8hr day): £78,000–£104,000/year in engineering time
- Platform build + maintenance estimated at £30,000 annually
- **Net annual saving: ~£48,000–£74,000** — not counting the compounding value of earlier defect
  detection.

---

### About the Design

**Q: Why FastAPI rather than a Python CLI tool?**
A: The platform needs to serve a React UI, expose endpoints to GitHub Actions webhooks, and
potentially serve multiple concurrent users. A REST API supports all of these use cases. A CLI
tool would require reimplementing the HTTP server layer later.

**Q: Why not use LangChain or a full agent framework?**
A: The workflow is deterministic: 9 steps, always in the same order, with the same inputs and
expected JSON outputs. LangChain adds abstraction and dependency surface area without benefit for
a sequential, structured-output pipeline. Direct `AsyncOpenAI` calls with structured JSON prompts
are simpler, more debuggable, and faster.

**Q: Why is the human review step mandatory and not optional?**
A: Because auto-posting AI content to Jira corrupts the authoritative project record. Sprint
velocity is measured from Jira. QA coverage decisions are made from Jira. If the AI posts
hallucinated test cases, teams make planning decisions based on false data. The staged review is a
correctness gate, not a friction point.

**Q: Why are team context files plain Markdown rather than a database or structured config?**
A: Markdown files are editable by non-engineers (QA leads, business analysts) without a UI.
They are version-controlled in Git alongside the application, so context changes are auditable.
Structured database records would require a migration every time a business rule changes.

**Q: How does the platform handle a Jira ticket with no acceptance criteria?**
A: The quality validator scores it low (typically 30–50/100) and generates a specific issue:
`{"field": "acceptance_criteria", "severity": "critical", "message": "No acceptance criteria
defined..."}`. The QA engineer is prompted to request clarification before proceeding. The
workflow can still generate test cases using the description alone, but the quality gate is explicit.

---

### About Scalability and Risk

**Q: What happens if the LLM generates a hallucinated business rule?**
A: Two defences. First, the team context file provides explicit business rules that ground the LLM
output. Second, the QA engineer reviews all generated content before upload. A hallucinated rule
("statements are retained for 5 years") would be caught by a QA engineer who knows the retention
policy is 7 years. The platform does not auto-publish.

**Q: What if the LLM provider goes down?**
A: The platform falls back to mock responses when `call_structured()` raises an exception, and
`LLM_PROVIDER` can be switched to any of 9 supported providers in seconds by changing one
environment variable. Outage impact is the current provider; the workflow is provider-agnostic.

**Q: How does this scale to a team with 100 tickets per sprint?**
A: The `POST /release-qa` endpoint processes a full release in parallel. 100 tickets at the
current GitHub Models API rate limit (60 RPM for gpt-4o) takes approximately 10–15 minutes for
full analysis. The bottleneck is LLM throughput, not the platform. An Azure OpenAI deployment
with higher rate limits would process the same batch in under 4 minutes.

**Q: What is the privacy and data security posture?**
A: Credentials are stored in environment variables, never in application code or API responses.
Jira and GitHub tokens are never logged or serialised. The LLM provider receives ticket text and
commit summaries — no PII (customer names, account numbers, transaction data) should exist in
Jira tickets; if it does, that is a pre-existing data hygiene issue, not introduced by this
platform. Outputs are stored locally in `outputs/` with no external exposure.

**Q: Can this be used across other business units, not just Wealth Management?**
A: Yes. New teams are onboarded by creating a single Markdown context file with no code changes.
The workflow, UI, and LLM prompts are generic by design; team context files provide the domain
specificity. An Investment Banking or Retail Banking team could be onboarded in under an hour.

---

## 7. End-to-End Flow (Detailed)

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

## 8. Future Roadmap

| Phase | Feature | Estimated Value |
|-------|---------|----------------|
| 1 *(delivered)* | Core QA workflow, review UI, Jira upload, pytest-bdd push | Foundation — 70% effort reduction |
| 2 | GitHub Actions integration — trigger on PR open, post report as PR comment | Shift-left to code review |
| 3 | MCP tool server — expose steps as composable AI agent tools | Agent-native integration |
| 4 | Live test execution — run pushed tests, pull results, close the loop | Full feedback cycle |
| 5 | Quality trend dashboards — score trend, coverage%, regression rate per team | Sprint-level insight |
| 6 | Multi-repo mapping — one Jira project → multiple GitHub repos (service + UI + automation) | Enterprise scale |
| 7 | Accessibility coverage generation — WCAG 2.1 test case generation from UI tickets | Proactive a11y compliance |

- GitHub PAT scoped to minimum required permissions (contents: write, pull_requests: write)

---

## 9. Execution Models — How the Workflow Can Be Triggered

The platform was designed around a single principle: **the orchestration brain is always the
backend API; the trigger mechanism is interchangeable**. This section documents all supported and
planned execution modes, the intentional choices made, and the trade-off reasoning.

---

### 9.1 Core Problem Being Solved

> "How do we execute an AI-driven QA workflow (Jira → Code → Tests → Report) in a way that
> is easy, scalable, and reliable for QA teams?"

The answer is not a single interface. Different teams operate differently. Enterprise QA teams live
in Jira; engineering teams prefer CLI or GitHub Actions; managers want dashboards. The API-first
architecture supports all of them without duplicating the orchestration logic.

---

### 9.2 All Execution Models

#### Model 1 — VS Code / Copilot Agent (IDE-Driven)

**How it works:** A developer opens the repo in VS Code, enables a Copilot Agent prompt, and the
agent calls the platform's MCP tools or API endpoints inline.

**Steps:**
1. Open repo in VS Code
2. Enable Copilot Agent mode
3. Run structured prompt (e.g. "Run QA for CRFLT-42")
4. Agent calls Jira MCP → GitHub MCP → generates outputs

| | |
|---|---|
| **Pros** | Zero infra setup; easiest to prototype; full flexibility; great for debugging |
| **Cons** | Not scalable; requires technical users; no standardisation across team |
| **Best for** | POC / initial build phase |

---

#### Model 2 — CLI Tool

**How it works:** A shell command wraps the API call.

```bash
python scripts/trigger_qa.py --jira-id CRFLT-123 --team-id statements
```

**Steps:**
1. Install dependencies and configure `.env`
2. Run command with ticket ID and team flag
3. Outputs written to `outputs/` locally

| | |
|---|---|
| **Pros** | Faster than IDE; scriptable; easy to automate via cron or CI |
| **Cons** | Technical users only; no visual feedback; limited adoption for QA analysts |
| **Best for** | Internal engineering teams; automation pipelines |

---

#### Model 3 — Backend API (FastAPI) — Chosen Foundation

**How it works:** Any system or user calls `POST /api/v1/run-qa` with a JSON payload. The backend
orchestrates the entire workflow internally.

**Steps:**
1. Caller sends `{"jira_id": "CRFLT-123", "team_id": "statements", ...}`
2. Backend fetches ticket from Jira REST API
3. Backend fetches recent commits from GitHub REST API
4. AI pipeline runs all 9 workflow steps
5. Outputs written to `outputs/`; response returned; Jira comment posted if `post_to_jira=true`

| | |
|---|---|
| **Pros** | Scalable; reusable; centralised logic; plugs into any trigger (UI, Jira, Slack, GitHub) |
| **Cons** | Requires hosting; needs API design discipline |
| **Best for** | **Foundation layer** — all other models are thin wrappers over this |

> This is the intentional choice. All other execution models reduce to "call the API with the right parameters". The workflow logic lives in exactly one place.

---

#### Model 4 — Web UI Dashboard — Primary User-Facing Mode

**How it works:** QA engineer opens the browser dashboard, enters a Jira ticket ID, clicks
"Run QA Analysis". The UI calls the backend API and renders results live.

**Steps:**
1. Open `http://localhost:8000` (or deployed URL)
2. Enter Jira ID, select team
3. Click "Run QA Analysis"
4. UI streams progress log
5. Review generated content in the tabbed editor (test cases, BDD, report)
6. Click "Upload to Jira" to post the reviewed output

| | |
|---|---|
| **Pros** | Very user-friendly; high adoption by QA analysts; visual progress bar; centralized usage |
| **Cons** | Requires frontend; slightly more infra; not suitable for batch runs |
| **Best for** | **Primary mode** — QA-heavy teams, non-technical users |

---

#### Model 5 — GitHub Actions (CI/CD Triggered)

**How it works:** The `qa-workflow.yml` workflow runs on `workflow_dispatch`. Can be extended to
trigger on PR open, label assignment, or push to a release branch.

**Steps:**
1. Workflow dispatched (manually or via API trigger) with `jira_id` and `team_id`
2. Workflow starts the FastAPI server on the runner
3. `scripts/trigger_qa.py` calls the API with all step flags
4. Artefacts (HTML report, test cases, BDD files) uploaded as GitHub Actions artefacts
5. QA comment posted to Jira ticket via `post_to_jira=true`

```yaml
# Trigger via REST
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/shrikantkingdom/qa-agent-platform/actions/workflows/256210169/dispatches \
  -d '{"ref": "main", "inputs": {"jira_id": "CRFLT-1", "team_id": "statements", "upload_to_jira": "true"}}'
```

| | |
|---|---|
| **Pros** | No separate hosting; artefacts versioned with runs; audit trail per commit/ticket |
| **Cons** | Cold-start latency (server boot); runner cost per run; not interactive |
| **Best for** | Automated regression on PR open; release-gate QA; CI/CD pipelines |

---

#### Model 6 — Jira-Native Execution (Automation Rules)

**How it works:** A Jira Automation rule fires a webhook to the platform API when a trigger
condition is met (button click, status transition, issue creation).

**Steps (Option A — Jira Automation webhook):**
1. Create a Jira Automation rule: trigger = "Transition to In Progress" or custom button
2. Action = "Send web request" to `POST https://<platform>/api/v1/run-qa`
3. Payload includes `{{issue.key}}` and team mapping
4. Platform posts result as a comment back to the same ticket

**Steps (Option B — Jira Connect App):**
1. Build a Jira Forge or Connect app with a panel button
2. Button calls the platform API; result rendered inside Jira issue panel

| | |
|---|---|
| **Pros** | Zero context switching; fits existing QA workflow; high adoption; enterprise-friendly |
| **Cons** | Jira Automation requires Admin access; Forge app requires development |
| **Best for** | **Mature enterprise teams** — QA analysts who never leave Jira |

---

#### Model 7 — ChatOps (Slack / Teams Bot)

**How it works:** QA engineer or developer sends a slash command in a team channel.

```
/qa-run CRFLT-123
```

Bot calls the platform API and replies with score, grade, and report link in the thread.

| | |
|---|---|
| **Pros** | Extremely low friction; no UI needed; fast adoption; visible to whole team in channel |
| **Cons** | Limited result visualisation; harder for detailed review; requires bot infrastructure |
| **Best for** | Quick access layer; notifying team of QA score without context-switching |

---

#### Model 8 — Fully Automated (Scheduled / Event-Driven)

**How it works:** Cron job or event bus triggers batch QA across all tickets in a sprint or
release automatically — no human input required.

**Steps:**
1. Trigger event: nightly cron / PR merge webhook / release creation in Jira
2. Backend calls `POST /release-qa` with `fixVersion`
3. All tickets in the release processed in parallel
4. Reports posted to each Jira ticket; summary dashboard updated
5. Alerts fired for tickets scoring below threshold

| | |
|---|---|
| **Pros** | Zero manual effort; continuous QA validation; sprint-level trend data |
| **Cons** | Less per-ticket control; needs strong monitoring to avoid alert noise |
| **Best for** | Large-scale systems; continuous QA governance; sprint health monitoring |

---

### 9.3 Execution Model Comparison

| Model | Ease of Use | Scalability | QA Friendly | Best Use Case |
|-------|------------|-------------|-------------|---------------|
| VS Code / Copilot Agent | Low | Low | ❌ | POC / debugging |
| CLI (`trigger_qa.py`) | Medium | Medium | ❌ | Engineering / CI scripting |
| Backend API direct | Medium | High | ⚠️ | Core orchestration layer |
| Web UI Dashboard | High | High | ✅ | Primary — QA analyst daily use |
| GitHub Actions | Medium | High | ⚠️ | CI/CD gate; automated trigger |
| Jira Automation | Very High | High | ✅ | Enterprise — no context switching |
| Slack / Teams Bot | High | Medium | ✅ | Quick access; team visibility |
| Scheduled / Event-Driven | Very High | Very High | ✅ | Continuous QA; release governance |

---

### 9.4 Architecture Decision: Why API-First

The key design principle is: **separate the execution layer from the orchestration logic**.

```
┌─────────────────────────────────────────────────┐
│            Trigger Layer (interchangeable)       │
│  Web UI │ GitHub Actions │ Jira │ Slack │ Cron  │
└─────────────────────┬───────────────────────────┘
                      │ POST /api/v1/run-qa
                      ▼
┌─────────────────────────────────────────────────┐
│         Orchestration Layer (single source)      │
│  FastAPI backend → workflow_service → ai_service │
│  Jira REST API + GitHub REST API integration     │
└─────────────────────────────────────────────────┘
```

Benefits:
- **Extensible**: add a new trigger (e.g. Slack bot) without touching the workflow logic
- **Maintainable**: one place to fix bugs, update prompts, change output format
- **Enterprise-ready**: audit log, RBAC, rate limiting all applied once at the API layer

---

## 10. Interview Questions & Answers — Execution Model Depth

---

### Design Decisions

**Q: Why did you build a REST API rather than a standalone CLI tool?**

A: Three reasons. First, the platform needs to serve both a browser UI and automated systems
(GitHub Actions, Jira webhooks) simultaneously — a CLI can only serve one caller at a time.
Second, REST makes the workflow reachable from any language or platform without installing
Python dependencies. Third, the API enables concurrency: multiple tickets can be processed in
parallel by separate callers, which a blocking CLI loop cannot do.

---

**Q: Why did you choose Web UI as the primary mode rather than Jira-native or Slack?**

A: The Web UI was the right choice for the initial rollout for three reasons:
1. **Review gate**: QA engineers need to read and edit generated content before it posts to Jira.
A Jira Automation webhook auto-posts without review — that risks polluting the authoritative
project record with hallucinated test cases.
2. **Adoption curve**: QA teams unfamiliar with AI tools are more comfortable with a familiar
browser form than a Jira sidebar plugin they've never seen.
3. **Iteration speed**: Changing the UI (adding a tab, adjusting the review panel) is faster than
releasing a Jira Forge app update.
Jira-native and Slack modes are roadmap items — they make sense once the team trusts the quality
of the output and wants to reduce the review step friction.

---

**Q: What would it take to add a Slack bot trigger in the current architecture?**

A: Around 40–60 lines of code. The Slack bolt app would receive a slash command, extract the
`jira_id` from the message text, call `POST /api/v1/run-qa` via `httpx`, and post the
`grade + score + report_url` back to the channel thread. The entire QA workflow logic is
unchanged — only the trigger and response-formatting code is new.

---

**Q: How do you prevent the automated triggered runs (GitHub Actions, scheduled) from spamming Jira tickets with duplicate comments?**

A: Two mechanisms. First, `post_to_jira` defaults to `false` on the API — callers must explicitly
opt in. Second, the platform's run history in SQLite tracks `run_id` per `jira_id`; a
deduplication check before posting can prevent double-commenting if the same ticket is
triggered twice in a short window. For the GitHub Actions mode, the workflow input
`upload_to_jira` is the explicit gate — set `false` for dry-run checks.

---

**Q: How would you handle Jira Automation webhook authentication if the platform were deployed externally?**

A: The platform would expose a dedicated webhook endpoint (e.g. `POST /webhooks/jira`) protected
by a shared secret header (`X-Webhook-Secret`). Jira Automation sends the secret as a custom
header in the "Send web request" action. The endpoint validates the secret via
`hmac.compare_digest` before processing the payload. This prevents unauthenticated callers from
triggering expensive LLM workflows.

---

**Q: In the GitHub Actions model, the FastAPI server starts cold on every run. How do you mitigate startup latency?**

A: Three mitigations currently in place:
1. The workflow polls the `/health` endpoint in a loop (1-second interval, 30-second timeout)
before calling the API — so the first call is never made before the server is ready.
2. Python dependencies are cached via `actions/setup-python` with `cache: pip` — reducing cold
dependency install from ~40s to ~5s.
3. For latency-sensitive use cases, the platform can be deployed as a persistent service (e.g.
on a small ECS task or Railway instance) and the GitHub Actions workflow points to the
external URL instead of starting a local server — removing the cold-start entirely.

---

**Q: How would you route a Jira Automation webhook to the correct team's workflow (statements vs confirms vs letters)?**

A: The webhook payload includes the Jira issue fields. The platform maps the `components` field
on the ticket (e.g. `CR-statements`) to the `team_id` parameter. This mapping lives in
`workflow_service._load_team_context()`. A Jira Automation rule can also pass the component
as a custom header or body field — the routing logic is centralised in the API, not split
across Jira rules.

---

### Scaling and Risk

**Q: If the platform serves 10 teams, 50 tickets per sprint each — 500 tickets — how does the architecture hold?**

A: The API is stateless and async. Each `/run-qa` call is a coroutine; FastAPI can handle
concurrent requests naturally. The bottleneck is LLM rate limits, not the application server.
Horizontal scaling path:
- Deploy 2–3 API instances behind a load balancer (no shared state beyond the SQLite DB, which
can be replaced with PostgreSQL)
- Shard LLM calls across Azure OpenAI deployments in different regions (each has its own TPM limit)
- Use `POST /release-qa` with the concurrency limiter rather than 500 individual calls

---

**Q: What is your monitoring strategy for production automated runs?**

A: Three layers:
1. **Structured logging** — every workflow run logs `run_id`, `jira_id`, `team_id`, `grade`,
`duration_seconds`, and `error` to stdout in JSON format, readable by any APM.
2. **Run history API** — `GET /history` exposes recent runs with status; a simple Grafana
datasource or Jira dashboard widget can surface failure rate.
3. **Grade-F exit code** — the `trigger_qa.py` script exits with code `2` on a Grade F result,
causing the GitHub Actions job to fail and alerting the team via the standard Actions
notification channel.

---

### One-Line Summary for Interviews

> "We built an API-first agentic QA platform using FastAPI and direct LLM integration, exposed
> it via a review-first Web UI for daily QA use, and wired it to GitHub Actions for CI/CD
> automation — with the architecture designed so that Jira webhooks, Slack bots, and scheduled
> runs can be added as thin trigger layers without changing any workflow logic."
