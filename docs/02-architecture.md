# Technical Architecture — QA Agent Platform
## Client Reporting / Wealth Management — Quality Automation System

---

## 1. System Overview

**QA Agent Platform** is a FastAPI-based REST service that automates the quality assurance workflow
for Wealth Management delivery teams. It accepts a Jira ticket ID and orchestrates a 9-step
pipeline — fetching data from Jira and GitHub, running five parallel-purpose LLM prompts, generating
artefacts (HTML report, CSV, `.feature` file, pytest-bdd step definitions), and returning a
structured quality report for human review before any write-back to Jira or the automation repo.

**Three teams currently served:**
- Statements (`config/teams/statements.md` — CRFLT project)
- Confirms (`config/teams/confirms.md` — CRFLT project)
- Letters / Client Correspondence (`config/teams/letters.md` — CRFLT project)

---

## 2. Repository Structure

```
qa-agent-platform/
│
├── app/
│   ├── api/
│   │   └── routes.py              ← All FastAPI route definitions (13 endpoints)
│   ├── config/
│   │   └── settings.py            ← Pydantic BaseSettings (env-driven config)
│   ├── models/
│   │   └── schemas.py             ← All Pydantic request/response models
│   ├── providers/
│   │   └── providers.py           ← LLM provider registry (9 providers)
│   ├── services/
│   │   ├── ai_service.py          ← All LLM prompt builders + AsyncOpenAI calls
│   │   ├── bdd_service.py         ← Gherkin file writer + pytest-bdd step def writer
│   │   ├── github_service.py      ← GitHub REST API client (read + push + PR)
│   │   ├── jira_service.py        ← Jira REST API client (read + comment + upload)
│   │   ├── report_service.py      ← HTML report generation
│   │   └── workflow_service.py    ← 9-step pipeline orchestrator
│   └── utils/
│       └── logger.py              ← Structured logging setup
│
├── config/
│   └── teams/
│       ├── global.md              ← Default fallback context
│       ├── statements.md          ← Statements team context
│       ├── confirms.md            ← Confirms team context
│       └── letters.md             ← Letters / Client Correspondence context
│
├── docs/                          ← Architecture and innovation documentation
├── outputs/                       ← Generated artefacts (reports, feature files, step defs)
├── ui/
│   └── index.html                 ← Single-page React UI (CDN-loaded, no build step)
│
├── app.py                         ← FastAPI app entry point
├── requirements.txt
└── start.sh                       ← Local one-command startup
```

---

## 3. Technology Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| API Framework | FastAPI 0.111 | Async-first, Pydantic integration, auto OpenAPI docs |
| Async LLM Client | AsyncOpenAI 1.x | Compatible with all OpenAI-API-compatible providers |
| Validation | Pydantic v2 | Runtime type safety, JSON coercion, model serialisation |
| Jira Client | httpx (async) | Native async, used for both Jira and GitHub API calls |
| LLM Providers | 9 providers via providers.py | GitHub Models (default), OpenAI, Azure, Anthropic, Groq, Ollama, etc. |
| UI | React 18 (CDN), Tailwind CSS | No build toolchain; single HTML file served directly |
| Report Generation | Jinja2 + Bootstrap | HTML QA reports with grade rings, issue tables, BDD sections |
| File Storage | Local `outputs/` | Simple; swappable to S3 without API contract changes |
| Config | python-dotenv + Pydantic BaseSettings | 12-factor app pattern; env-driven |
| Logging | Python logging + colorlog | Per-module structured logging |

---

## 4. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/run-qa` | Run full 9-step QA workflow for a single ticket |
| `POST` | `/api/v1/upload-to-jira` | Upload reviewed report as Jira comment + attachment |
| `POST` | `/api/v1/push-tests` | Push pytest-bdd step definitions to automation repo |
| `POST` | `/api/v1/run-release-qa` | Batch QA for all tickets in a fixVersion |
| `GET` | `/api/v1/team-config/{team_id}` | Read a team context file |
| `PUT` | `/api/v1/team-config/{team_id}` | Update a team context file |
| `GET` | `/api/v1/testcase-download/{jira_id}` | Download test cases CSV |
| `GET` | `/api/v1/testcase-download/{jira_id}/steps` | Download pytest-bdd step definitions |
| `GET` | `/api/v1/report/{jira_id}` | Download HTML QA report |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/` | Serve React UI (index.html) |
| `GET` | `/api/v1/providers` | List available LLM providers |
| `POST` | `/api/v1/run-custom-prompt` | Run a custom LLM prompt with team context |

---

## 5. The 9-Step Workflow in Detail

### Step 1 — Jira Ticket Fetch
```python
ticket = await jira_service.get_ticket(jira_id)
```
- HTTP `GET /rest/api/3/issue/{jira_id}` with Basic Auth (email + API token)
- Extracts: `summary`, `description`, `acceptance_criteria` (custom field), `status`, `labels`,
  `assignee`, `reporter`, `fix_version`, plus all team-specific custom fields
- Returns as `ticket_dict` — the base input for all LLM prompts

### Step 2 — GitHub Commit Fetch
```python
commits = await github_service.get_recent_commits(repo, limit=20)
```
- HTTP `GET /repos/{owner}/{repo}/commits` with Bearer token
- Fetches last 20 commits: SHA, message, author, timestamp, and diff stat
- Used to check whether code changes trace back to acceptance criteria

### Step 3 — Ticket Quality Validation
```python
sys_p, usr_p = ai_service.build_validation_prompt(ticket_dict, additional_context)
raw = await ai_service.call_structured(sys_p, usr_p)
result.quality_score = raw["quality_score"]            # int 0–100
result.issues = raw["issues"]                          # list of {field, severity, message, recommendation}
result.strengths = raw["strengths"]                    # list of strings
```
- LLM acts as a QA principal examining the ticket for testability
- Validates: AC completeness, ambiguity, measurability, TDD readiness
- Returns grade A–F with structured issues list

### Step 4 — Requirement–Code Alignment
```python
sys_p, usr_p = ai_service.build_alignment_prompt(ticket_dict, commits_dict, additional_context)
raw = await ai_service.call_structured(sys_p, usr_p)
result.alignment = raw["score"]                        # int 0–100
result.coverage_gaps = raw["coverage_gaps"]            # list of strings
result.over_implementation = raw["over_implementation"]
```
- Cross-references commit messages and diff statistics against acceptance criteria
- Surfaces missing implementations, undocumented scope changes, and over-engineering

### Step 5 — Test Case Generation
```python
sys_p, usr_p = ai_service.build_test_cases_prompt(ticket_dict, validation_raw, additional_context)
raw = await ai_service.call_structured(sys_p, usr_p)
result.test_cases = raw["test_cases"]                  # 8–15 structured test cases
```
- Returns: `test_id`, `scenario`, `steps[]`, `expected_result`, `test_type`, `priority`, `tags[]`
- Categories: Happy Path, Negative, Edge Case, Performance, Security, Accessibility
- Domain-specific rules injected via `additional_context` (e.g., "test GDPR suppression is absolute")

### Step 6 — Test Cases CSV Export
```python
csv_path = bdd_service.save_test_cases_csv(result.test_cases, jira_id)
```
- Writes `outputs/test_cases/{jira_id}.csv`
- Columns: test_id, scenario, steps (pipe-delimited), expected_result, test_type, priority, tags

### Step 7 — BDD Scenario Generation
```python
sys_p, usr_p = ai_service.build_bdd_prompt(ticket_dict, test_cases_raw, additional_context)
raw = await ai_service.call_structured(sys_p, usr_p)
feature_name, result.bdd_scenarios = bdd_service.parse_scenarios(raw)
```
- Returns: `feature_name`, `scenarios[]` with `given[]`, `when[]`, `then[]`, `tags[]`
- Feature file saved: `outputs/bdd/{jira_id}.feature`

### Step 8 — pytest-bdd Step Definitions
```python
sys_p, usr_p = ai_service.build_step_definitions_prompt(scenarios_dict, additional_context)
raw = await ai_service.call_structured(sys_p, usr_p)
result.step_definitions = bdd_service.parse_step_definitions(raw)
bdd_service.save_step_definitions(result.step_definitions, jira_id)
```
- Generates complete `tests/step_defs/<team>/<feature>_steps.py` files
- Follows `playwright_project` conventions exactly:
  - `from pytest_bdd import given, when, then, parsers, scenarios`
  - `FEATURES_DIR` path resolution using `Path(__file__).parent...`
  - `@given(..., target_fixture=...)` for Page Object instantiation
  - `parsers.parse(...)` for parameterised steps
  - Function naming: `given_<verb>`, `when_<verb>`, `then_<verb>`

### Step 9 — HTML Report Generation
```python
result.report_path = report_service.generate_html_report(result)
```
- Jinja2 template rendering: quality ring, stats cards, issues table, test cases grid, BDD viewer
- Saved to `outputs/reports/{jira_id}_report.html`

---

## 6. LLM Provider Architecture

### 6.1 Provider Registry

```python
# providers.py — simplified
PROVIDERS = {
    "github":    {"base_url": "https://models.inference.ai.azure.com", "model": "gpt-4o", ...},
    "openai":    {"base_url": "https://api.openai.com/v1",              "model": "gpt-4o", ...},
    "azure":     {"base_url": "{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT}", "model": os.getenv("AZURE_MODEL"), ...},
    "anthropic": {"base_url": "https://api.anthropic.com/v1",           "model": "claude-3-5-sonnet-latest", ...},
    "groq":      {"base_url": "https://api.groq.com/openai/v1",         "model": "llama3-70b-8192", ...},
    "ollama":    {"base_url": "http://localhost:11434/v1",               "model": "llama3", ...},
    # ... 3 more
}
```

### 6.2 Call Pattern

```python
async def call_structured(self, system: str, user: str) -> dict:
    config = resolve_provider_config(settings.llm_provider)
    client = AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])
    response = await client.chat.completions.create(
        model=config["model"],
        response_format={"type": "json_object"},    # JSON mode
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=4096,
    )
    return json.loads(response.choices[0].message.content)
```

JSON mode (`response_format={"type": "json_object"}`) is used on all prompts to guarantee parseable
output. The `temperature=0.3` setting biases toward deterministic, structured responses rather than
creative variation.

### 6.3 Fallback Mock Mode

When no API key is set (`OPENAI_API_KEY=""` or unset), `call_structured()` routes to
`_mock_response(user_prompt)` which pattern-matches on prompt keywords and returns pre-built
JSON. This supports fully offline development and unit testing without LLM calls.

---

## 7. Team Context Injection Architecture

### 7.1 Context Loading

```python
# workflow_service.py
def _load_team_context(self, team_id: str | None) -> str:
    if not team_id:
        path = Path(settings.teams_path) / "global.md"
    else:
        path = Path(settings.teams_path) / f"{team_id}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
```

### 7.2 Context Threading

The loaded context string is composed with any user-supplied `custom_prompt`:

```python
additional_context = team_context
if request.custom_prompt:
    additional_context += f"\n\n--- Custom Instructions ---\n{request.custom_prompt}"
```

This `additional_context` is passed to every prompt builder. Each builder appends it to the user
section of the prompt if non-empty, ensuring team-specific business rules are visible to the LLM
across all 9 steps.

### 7.3 Team Context File Content Model

Each `config/teams/<team>.md` contains:
- Project key and Jira board URL
- GitHub repo URLs (services, UI, automation)
- Jira custom field names and valid values
- Automation directory structure and naming conventions
- pytest-bdd tags and feature file paths
- Business rules with compliance criticality
- Test environment URLs

---

## 8. GitHub Integration

### 8.1 Read — Commit Fetching

```python
GET /repos/{owner}/{repo}/commits?per_page={limit}
Authorization: Bearer {GITHUB_TOKEN}
```

Returns commit metadata + stats. No local git clone; pure REST.

### 8.2 Write — Test File Push

`github_service.push_playwright_test_file()` performs the GitHub Blob API sequence:

```
1. GET  /repos/{owner}/{repo}/git/refs/heads/main         → current main SHA
2. POST /repos/{owner}/{repo}/git/refs                     → create branch qa-agent/{jira_id}
   (422 already-exists → silently skipped)
3. GET  /repos/{owner}/{repo}/contents/tests/step_defs/{team}/{file}  → existing file SHA (if any)
4. PUT  /repos/{owner}/{repo}/contents/tests/step_defs/{team}/{file}  → create or update
   content: base64(step_def_content)
   message: "feat(qa-agent): add generated step defs for {jira_id}"
5. POST /repos/{owner}/{repo}/pulls                        → open PR (if create_pr=True)
   title: "[QA Agent] Add pytest-bdd step defs for {jira_id}"
   base: "main", head: "qa-agent/{jira_id}"
```

No local git operations. No file system dependencies beyond the `outputs/` content already in memory.

---

## 9. pytest-bdd Integration Architecture

### 9.1 Target Repo Structure

```
playwright_project/
├── features/
│   ├── ui/         ← existing: login.feature, cart.feature, navigation.feature
│   └── api/        ← existing: posts.feature, todos.feature, users.feature
├── tests/
│   └── step_defs/
│       ├── ui/     ← existing: test_login_steps.py, test_cart_steps.py
│       └── api/    ← existing: test_posts_steps.py, test_users_steps.py
├── pages/          ← Page Object classes
├── conftest.py     ← session/function fixtures: page, browser, config, api_client
└── pytest.ini      ← testpaths = tests/step_defs
```

### 9.2 Generation Contract

The AI is instructed to match the exact in-repo pattern via the `repo_context` string in
`ai_service.build_step_definitions_prompt()`:

```python
# Features are linked with explicit FEATURES_DIR path resolution
FEATURES_DIR = Path(__file__).parent.parent.parent.parent / "features"
scenarios(str(FEATURES_DIR / "ui" / "login.feature"))

# @given with target_fixture returns Page Object as named fixture
@given("I am on the login page", target_fixture="login_page")
def given_on_login_page(page, config):
    lp = LoginPage(page)
    lp.open(config.ui_base_url)
    return lp

# parsers.parse() for parameterised steps
@when(parsers.parse('I login with username "{username}" and password "{password}"'))
def when_login(login_page, username, password):
    login_page.login(username, password)
```

### 9.3 File Placement

Generated step definitions:
- Saved locally: `outputs/bdd/{jira_id}_steps.py`
- Pushed to repo: `tests/step_defs/{team}/{feature}_steps.py`
  (team is resolved from the Jira component on the ticket: CR-statements → statements, CR-confirms → confirms, CR-letters → letters — all under CRFLT project)

---

## 10. Challenges Overcome

### 10.1 Framework Mismatch — Generating Wrong Automation Code

**Challenge:** The original implementation generated plain pytest functions with Playwright POM
(no pytest-bdd). When the user updated `playwright_project` to use `pytest-bdd 7.x`, the generated
output was structurally incompatible with the new repo conventions.

**Resolution:** Full audit of the target repo (`conftest.py`, `pytest.ini`, `requirements.txt`,
actual step definition files). Rewrote `build_step_definitions_prompt()` to:
- Use `from pytest_bdd import given, when, then, parsers, scenarios`
- Link feature files via `FEATURES_DIR / ...`
- Apply `target_fixture` on `@given` for POM Page Object injection
- Use `parsers.parse()` for parameterised steps
- Match function naming conventions (`given_`, `when_`, `then_`)

Updated `bdd_service.save_step_definitions()` header imports to match. Updated mock response
in `_mock_response()`. Updated log messages in `workflow_service.py`.

**Lesson:** Always audit the target framework before generating code for it. "pytest + Playwright"
and "pytest-bdd + Playwright" produce structurally different file conventions.

### 10.2 Multi-Team Context Without Code Proliferation

**Challenge:** Three teams with different Jira project keys, custom fields, business rules,
automation paths, and compliance requirements. Hardcoding team-specific logic in Python would
have required code changes for every onboarding.

**Resolution:** Configuration-as-Markdown pattern. Each team gets a `.md` file with all
team-specific context. The orchestrator loads it at runtime and injects it into every prompt.
New team = new file, no code change. File is editable from the UI without redeployment.

**Trade-off:** The LLM must interpret unstructured Markdown rather than structured JSON. This
works because LLMs have strong Markdown comprehension; the alternative (YAML/JSON config) would
require a schema and a form UI, adding significant complexity with marginal accuracy benefit.

### 10.3 JSON Mode Reliability Across Providers

**Challenge:** Not all providers support `response_format={"type": "json_object"}`. Some return
JSON wrapped in markdown code blocks. Some return malformed JSON on complex prompts.

**Resolution:** `call_structured()` has a provider-aware JSON extraction layer:
1. Try direct `json.loads()` on the response
2. If that fails, extract content between ` ```json ` and ` ``` ` markers (markdown code block strip)
3. If that fails, attempt regex extraction of outermost `{...}` block
4. If all fail, fall back to mock response with error logged

**Trade-off accepted:** The fallback is logged and traceable. Network errors cause workflow step
failure, which is surfaced in the `QAResponse.error` field rather than crashing the endpoint.

### 10.4 Jira Custom Fields Are Not Standardised

**Challenge:** Jira custom fields have opaque IDs (`customfield_10028`) that differ across
instances. A field named "Acceptance Criteria" might be `customfield_10014` in one org and
`customfield_10028` in another.

**Resolution:** `jira_service.get_ticket()` reads all custom fields and includes the full
`customFields` dict in the ticket payload sent to the LLM. The system prompt instructs the LLM
to infer acceptance criteria from both the standard `description` field and any custom field
containing "criteria", "AC", or "acceptance" in its name.

**Future fix:** A one-time field discovery call (`GET /rest/api/3/field`) on first startup to
resolve custom field names to IDs, stored in settings.

### 10.5 GitHub API Rate Limits During Batch Runs

**Challenge:** Release QA batch processing calls GitHub commit API once per ticket. A release
with 30 tickets would trigger 30 separate API calls to the same repo within seconds, risking
rate limit responses (HTTP 403).

**Resolution:** `get_recent_commits()` caches the last fetch result (keyed by repo + timestamp
bucket). Within a batch run, all tickets for the same repo share one commit fetch. The cache
TTL is 60 seconds — sufficient for a batch run but not stale for sequential single-ticket runs.

---

## 11. Open Problems

### 11.1 Acceptance Criteria Field Variance
Jira field IDs for "acceptance criteria" vary per instance. Currently handled by LLM inference
from the full custom fields dict, but a formal field mapping configuration would be more reliable.

### 11.2 No Persistent QA History
Every run generates a new HTML report locally. There is no database of historical QA results.
Quality score trends over time, coverage gap patterns across releases, and regression analysis are
not currently possible without manual file inspection.

### 11.3 Step Definition Deduplication
If the same acceptance criteria appears in two tickets in the same release, the generated step
definitions may contain duplicate `@given`/`@when`/`@then` functions. pytest-bdd raises an error
for duplicate step text. Generated files currently need manual deduplication review before push.

### 11.4 No Automated Test Execution Loop
After `push-tests`, the generated step definitions sit on a branch. There is no trigger to run
them and pull back results. The feedback loop is incomplete — QA engineers must manually verify
that generated steps execute cleanly against the target environment.

### 11.5 Context Window Boundary for Large Tickets
Tickets with detailed acceptance criteria (15+ items), large commit diffs, and a long team context
file can approach the effective context window boundary for `max_tokens=4096` responses. Very large
release notes or migration stories may produce truncated step definition output.

---

## 12. Future Enhancements

### 12.1 GitHub Actions Integration (Next Priority)
Add a `.github/workflows/qa-agent.yml` to `playwright_project` that triggers on PR open.
The workflow calls `POST /run-qa` with the Jira ticket ID from the PR title (parsed by convention),
and posts the report as a PR comment using the GitHub Actions bot. This shifts QA analysis to the
moment code enters review — the earliest possible intervention point.

### 12.2 Persistent QA Database
Add SQLite (single-file, zero-ops) or PostgreSQL to store:
- `runs` table: jira_id, team_id, quality_score, alignment_score, run_timestamp
- `issues` table: run_id, field, severity, message
- `test_cases` table: run_id, test_id, scenario, priority, tags

Enables: quality trend charts, sprint retrospective reports, regression detection.

### 12.3 MCP Tool Server
Expose each workflow step as a composable MCP tool. Enables AI coding agents (GitHub Copilot,
Claude Desktop, Cursor) to invoke individual steps — e.g., "validate this ticket" or "generate
step defs for these scenarios" — without running the full 9-step workflow.

### 12.4 Live Test Execution Feedback
After `push-tests` creates the branch, trigger the GitHub Actions test workflow via
`POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches`. Poll for completion.
Fetch the job log. Render pass/fail results on the QA report. This closes the full loop from
ticket quality check to test execution evidence.

### 12.5 Duplicate Step Detection
Before pushing generated step definitions, call the GitHub API to read existing step files in the
target team directory. Extract defined step texts using regex. Compare against generated steps.
Flag duplicates in the UI before push, suggesting which functions to remove or merge.

### 12.6 Multi-Repo Ticket Mapping
All three teams share the CRFLT project and are differentiated by component (CR-statements, CR-confirms, CR-letters).
Each team can span multiple GitHub repos; add a `repo_scope` field to team config files specifying which repos to check for each workflow step.
The alignment checker in Step 4 would then analyse commits across all three repos against the same
acceptance criteria.

---

> **Interview Q&A** covering architecture, design, LLM, security, scalability, and career questions
> has been consolidated into [10-interview-qa.md](10-interview-qa.md).

