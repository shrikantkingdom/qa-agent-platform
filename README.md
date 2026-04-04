# 🤖 QA Agent Platform

> **One-click AI-powered QA workflow automation** — validate Jira tickets, analyse code changes, generate test cases, BDD scenarios, and a full HTML QA report in a single API call.

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Jira Ticket Validation** | Quality score (0–100), grade, issue list, strengths |
| **Code Alignment** | Links GitHub commits to Jira requirements; surfaces gaps |
| **Test Case Generation** | Happy Path, Negative, Edge Case, Regression scenarios |
| **BDD Scenarios** | Gherkin Feature files + pytest-bdd step definitions |
| **HTML QA Report** | Standalone, printable, shareable report |
| **CSV / JSON Export** | Structured test case artefacts for any test management tool |
| **Mock Mode** | Works out-of-the-box without real Jira/GitHub credentials |
| **One-click UI** | Enter a Jira ID → click Run → download everything |

---

## 🏗️ Project Structure

```
qa-agent-platform/
├── app/
│   ├── main.py                   # FastAPI app, CORS, lifespan, static UI mount
│   ├── api/
│   │   └── routes.py             # POST /run-qa, GET /outputs/…, GET /health
│   ├── services/
│   │   ├── workflow_service.py   # ★ Main 9-step orchestrator
│   │   ├── ai_service.py         # LLM prompt builders + OpenAI calls
│   │   ├── jira_service.py       # Jira MCP abstraction (mock + real)
│   │   ├── github_service.py     # GitHub MCP abstraction (mock + real)
│   │   ├── test_generation_service.py   # Parse + export test cases
│   │   ├── bdd_service.py        # Gherkin feature files + step defs
│   │   └── report_service.py     # Jinja2 HTML report renderer
│   ├── models/
│   │   └── schemas.py            # All Pydantic v2 models
│   ├── utils/
│   │   └── logger.py             # Structured stdout logging
│   └── config/
│       └── settings.py           # pydantic-settings env config
│
├── ui/
│   └── index.html                # Single-page UI (no build step)
│
├── templates/
│   └── report_template.html      # Jinja2 HTML report template
│
├── outputs/                      # Auto-created on startup
│   ├── reports/                  # HTML reports
│   ├── testcases/                # CSV + JSON test cases
│   └── bdd/                      # .feature + _steps.py files
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & enter the project

```bash
git clone <repo-url>
cd qa-agent-platform
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY
# Leave USE_MOCK_JIRA=true and USE_MOCK_GITHUB=true for demo mode
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

### 6. Open the UI

```
http://localhost:8000
```

Enter a Jira ID (e.g. `PROJ-123`), click **Run QA Analysis**, and download your artefacts.

---

## 🔌 API Reference

### `POST /api/v1/run-qa`

Execute the full QA workflow.

**Request body:**
```json
{
  "jira_id":     "PROJ-123",
  "release":     "v2.1.0",
  "include_bdd": true,
  "post_to_jira": false
}
```

**Response:** `QAResponse` containing quality score, validation issues, test cases, BDD scenarios, alignment results, and output file paths.

---

### `GET /api/v1/outputs/{type}/{filename}`

Download a generated artefact.

| `type`     | Files                                   |
|------------|-----------------------------------------|
| `reports`  | `{JIRA_ID}_report.html`                 |
| `testcases`| `{JIRA_ID}_testcases.csv / .json`       |
| `bdd`      | `{JIRA_ID}.feature`, `{JIRA_ID}_steps.py` |

---

### `GET /api/v1/health`

Liveness check — returns `{"status": "healthy"}`.

---

### Interactive Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🧠 Workflow Steps

```
POST /run-qa
     │
     ▼
[1] Fetch Jira ticket            (jira_service)
[2] Validate ticket quality      (ai_service → LLM)
[3] Fetch GitHub commits         (github_service)
[4] Code-requirement alignment   (ai_service → LLM)
[5] Generate test cases          (ai_service → LLM)
[6] Export CSV + JSON            (test_generation_service)
[7] Generate BDD Gherkin         (ai_service → LLM)
[8] Generate step definitions    (ai_service → LLM)
[9] Render HTML report           (report_service → Jinja2)
     │
     ▼
  outputs/reports/*.html
  outputs/testcases/*.csv + *.json
  outputs/bdd/*.feature + *_steps.py
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | `""` | OpenAI key. Leave blank for mock responses |
| `OPENAI_MODEL` | `gpt-4o` | Model name |
| `USE_MOCK_JIRA` | `true` | Use built-in demo ticket instead of real Jira |
| `USE_MOCK_GITHUB` | `true` | Use built-in demo commits instead of real GitHub |
| `JIRA_BASE_URL` | — | `https://your-org.atlassian.net/rest/api/3` |
| `JIRA_API_TOKEN` | — | Jira API token |
| `JIRA_EMAIL` | — | Email address associated with the token |
| `GITHUB_TOKEN` | — | GitHub Personal Access Token |
| `GITHUB_REPO_OWNER` | — | GitHub org/user name |
| `GITHUB_REPO_NAME` | — | Repository name |

---

## 🔌 Connecting Real Integrations

### Jira
1. Set `USE_MOCK_JIRA=false` in `.env`
2. Fill in `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
3. Create an API token at: https://id.atlassian.com/manage-profile/security/api-tokens

### GitHub
1. Set `USE_MOCK_GITHUB=false`
2. Fill in `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`
3. Token needs `repo` + `read:org` scopes

---

## 🔮 Extending the Platform

| Enhancement | Where to add |
|---|---|
| Slack notification | `workflow_service.py` after step 9 |
| Jira webhook trigger | New FastAPI route in `routes.py` |
| Playwright test execution | New service, called from `workflow_service.py` |
| React UI | Replace `ui/index.html`, keep API unchanged |
| Custom LLM (Azure OpenAI) | Set `OPENAI_BASE_URL` in `.env` |
| Additional prompt tuning | `ai_service.py` prompt builder methods |

---

## 🛡️ Security Notes

- Never commit `.env` to source control (already in typical `.gitignore`)
- The download endpoint sanitises filenames to prevent path traversal
- LLM outputs are JSON-parsed; raw HTML is never injected unsanitised
- CORS is open (`*`) by default — restrict `allow_origins` for production
