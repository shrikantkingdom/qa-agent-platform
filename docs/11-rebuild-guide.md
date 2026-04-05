# 11 — Rebuild Guide

Step-by-step reference to rebuild the QA Agent Platform from scratch. Use this if you need to recreate the project, understand the build order, or onboard a new developer.

---

## Build Order

The platform was built in this exact order. Each phase is independently testable.

### Phase 1 — Foundation (FastAPI + Schemas)

1. **Create project structure**
   ```
   qa-agent-platform/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py
   │   ├── api/__init__.py
   │   ├── api/routes.py
   │   ├── models/__init__.py
   │   ├── models/schemas.py
   │   ├── config/__init__.py
   │   ├── config/settings.py
   │   ├── config/providers.py
   │   ├── services/__init__.py
   │   └── utils/logger.py
   ├── requirements.txt
   ├── .env.example
   └── .gitignore
   ```

2. **`requirements.txt`** — core dependencies:
   ```
   fastapi
   uvicorn[standard]
   pydantic-settings
   httpx
   openai
   jinja2
   tenacity
   python-multipart
   aiofiles
   ```

3. **`app/config/settings.py`** — `pydantic.BaseSettings` loading all env vars:
   - LLM: `llm_provider`, `openai_api_key`, `openai_model`, `openai_base_url`
   - Jira: `jira_base_url`, `jira_email`, `jira_api_token`, `jira_project_key`, `use_mock_jira`
   - GitHub: `github_token`, `github_repo_owner`, `github_repo_name`, `use_mock_github`
   - Webhook: `jira_webhook_secret`

4. **`app/config/providers.py`** — provider registry mapping name → `{base_url, api_key, model}` for 9 providers. Key function: `resolve_provider_config(provider_name)`.

5. **`app/models/schemas.py`** — all Pydantic v2 models:
   - `QARequest`, `QAResponse`, `WorkflowSteps`
   - `ValidationResult`, `AlignmentResult`, `TestCase`, `BDDScenario`
   - `JiraUploadRequest`, `PushTestsRequest`, `ReleaseQARequest`
   - `JiraWebhookPayload`

6. **`app/main.py`** — FastAPI app with CORS, lifespan (create output dirs), static mount for UI.

7. **`app/api/routes.py`** — start with `GET /health` and `POST /run-qa` only.

**Test:** `uvicorn app.main:app --reload` → `GET /health` returns 200.

---

### Phase 2 — Services (Core Workflow)

8. **`app/services/jira_service.py`** — `get_ticket(jira_id)` with mock mode. Uses `httpx.AsyncClient` for real Jira REST API calls. Returns `ticket_dict`.

9. **`app/services/github_service.py`** — `get_recent_commits(repo, limit)` with mock mode. Also `push_playwright_test_file()` for the Git Blob API sequence.

10. **`app/services/ai_service.py`** — the LLM brain:
    - `call_structured(system_prompt, user_prompt)` → JSON dict
    - `build_validation_prompt()`, `build_alignment_prompt()`, `build_test_cases_prompt()`, `build_bdd_prompt()`, `build_step_definitions_prompt()`
    - `_mock_response(user_prompt)` for offline dev/testing
    - Multi-tier JSON extraction fallback (direct → markdown strip → regex)

11. **`app/services/bdd_service.py`** — parse BDD scenarios, save `.feature` files, save `_steps.py` files with correct pytest-bdd imports and `target_fixture` pattern.

12. **`app/services/report_service.py`** — Jinja2 template rendering → `outputs/reports/{jira_id}_report.html`.

13. **`app/services/workflow_service.py`** — the 9-step orchestrator:
    ```python
    async def run_full_workflow(self, request: QARequest) -> WorkflowResult:
        # 1. Fetch Jira ticket
        # 2. Fetch GitHub commits
        # 3. Validate ticket quality (LLM)
        # 4. Check requirement-code alignment (LLM)
        # 5. Generate test cases (LLM)
        # 6. Save test cases CSV
        # 7. Generate BDD scenarios (LLM)
        # 8. Generate step definitions (LLM)
        # 9. Render HTML report
    ```
    Each step is guarded: if a step's flag is `false` in `WorkflowSteps`, skip it.

**Test:** `POST /run-qa {"jira_id": "TEST-1"}` with mock mode returns a full `QAResponse`.

---

### Phase 3 — UI + Upload + Push

14. **`ui/index.html`** — single-page React-like UI (vanilla JS, no build step):
    - Form: Jira ID input, team dropdown, checkboxes for steps
    - Progress log (streaming)
    - Results panel: quality score ring, issues table, test cases grid, BDD viewer
    - Buttons: Download Report, Upload to Jira, Push Tests

15. **`templates/report_template.html`** — Jinja2 template with quality ring, stats cards, issues table, test cases grid, BDD code blocks.

16. **Routes:** `POST /upload-to-jira`, `POST /push-playwright-tests`, `GET /testcase-download/...`

**Test:** Open browser, enter a ticket ID, click Run, see results.

---

### Phase 4 — Team Context + Multi-Team

17. **`config/teams/`** — create `global.md`, `statements.md`, `confirms.md`, `letters.md`.

18. **`workflow_service._load_team_context(team_id)`** — loads `config/teams/{team_id}.md` and appends to every prompt's `additional_context`.

19. **Routes:** `GET /teams`, `GET /teams/{id}`, `PUT /teams/{id}` — team config CRUD from the UI.

**Test:** Run same ticket with and without `team_id` — outputs differ (generic vs domain-specific).

---

### Phase 5 — Extended Features

20. **Release batch:** `POST /run-release` — fetches all tickets for a `fixVersion`, runs workflow on each.

21. **History:** `app/services/history_service.py` — SQLite-based run audit log. Routes: `GET /history`, `GET /history/stats`.

22. **Jira operations:** `app/services/jira_ops_service.py` — query, create, transition, bulk update, test plans, sprint metrics.

23. **Upstream stubs:** `app/services/upstream_service.py` — test data discovery and creation.

---

### Phase 6 — Jira Automation Webhook

24. **`POST /webhooks/jira`** route with:
    - `JiraWebhookPayload` schema: `jira_id`, `components[]`, `post_to_jira`, `team_id`, `custom_prompt`
    - HMAC authentication via `X-Webhook-Secret` header
    - Background task execution (returns 202 immediately)
    - Component → team resolution via `_COMPONENT_TEAM_MAP`

25. **Jira Automation Rule:**
    - Trigger: "When issue transitions to In Progress"
    - Action: "Send web request" to `POST https://<platform>/api/v1/webhooks/jira`
    - Headers: `Content-Type: application/json`, `X-Webhook-Secret: <secret>`
    - Payload: `{"jira_id": "{{issue.key}}", "components": ["{{issue.components.name}}"], "post_to_jira": true}`

---

## Key Architecture Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | FastAPI | Async-native, Pydantic integration, auto-docs |
| LLM calls | Direct AsyncOpenAI | No framework overhead for a deterministic pipeline |
| Team context | Markdown files | Editable by non-engineers, Git-trackable, no DB migration |
| Human review | Mandatory gate | Prevents AI hallucinations from corrupting Jira records |
| Mock mode | Built-in | Enables offline dev and fast unit tests |
| Provider layer | 9-provider registry | One env var switches everything |
| Webhook auth | HMAC shared secret | Simple, secure, no OAuth complexity |
| Background tasks | FastAPI BackgroundTasks | Prevents Jira's 30s webhook timeout from killing the workflow |

## Key Code Patterns

### Provider-agnostic LLM call
```python
config = resolve_provider_config(settings.llm_provider)
client = AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])
response = await client.chat.completions.create(
    model=config["model"],
    response_format={"type": "json_object"},
    messages=[...],
    temperature=0.3,
)
```

### Team context injection
```python
additional_context = self._load_team_context(team_id)
if request.custom_prompt:
    additional_context += f"\n\n--- Custom Instructions ---\n{request.custom_prompt}"
# additional_context is passed to every prompt builder
```

### HMAC webhook verification
```python
if settings.jira_webhook_secret:
    if not hmac.compare_digest(header_secret, settings.jira_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
```

### Component → team resolution
```python
_COMPONENT_TEAM_MAP = {"cr-statements": "statements", "cr-confirms": "confirms", "cr-letters": "letters"}
team_id = _COMPONENT_TEAM_MAP.get(component.lower(), settings.default_team)
```

## File Dependency Graph

```
settings.py ← providers.py
     ↑
schemas.py
     ↑
ai_service.py ← jira_service.py, github_service.py
     ↑
workflow_service.py ← bdd_service.py, report_service.py
     ↑
routes.py → main.py
```

Build from bottom to top. Each layer depends only on the layers below it.
