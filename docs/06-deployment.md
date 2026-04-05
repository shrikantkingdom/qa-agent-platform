# 06 — Deployment

How to run the QA Agent Platform in development, Docker, CI/CD, and production.

---

## Local Development

```bash
make dev                         # uvicorn with --reload
# or
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
# Build and start
make docker-up
# or
docker compose up --build -d

# Stop
make docker-down

# Logs
docker compose logs -f qa-platform
```

The container exposes port 8000. Config and outputs are mounted as volumes so they persist across restarts.

### Environment Variables

Pass via `.env` file (docker-compose reads it automatically) or override individually:

```bash
docker compose run -e LLM_PROVIDER=groq qa-platform
```

## Production Deployment

### Option 1 — Docker on a VM

```bash
ssh your-server
git clone https://github.com/shrikantkingdom/qa-agent-platform.git
cd qa-agent-platform
cp .env.example .env && vim .env    # configure production keys
docker compose up -d
```

### Option 2 — Platform-as-a-Service

Works on Railway, Render, Fly.io, or any platform that supports Docker:

1. Push repo to GitHub
2. Connect the platform to your repo
3. Set environment variables in the platform dashboard
4. Deploy — the `Dockerfile` handles everything

### Option 3 — AWS / Azure

- **ECS/Fargate**: push Docker image to ECR, create task definition, run service
- **Azure Container Apps**: deploy directly from Docker image
- Scale horizontally — the app is stateless (no session state, `outputs/` is local file storage)

### CORS for Production

In `app/main.py`, restrict CORS origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # not "*"
    ...
)
```

## CI/CD — GitHub Actions

The platform includes a GitHub Actions workflow (`.github/workflows/qa-workflow.yml`) that:

1. Checks out code on the runner
2. Installs dependencies (cached via `actions/setup-python`)
3. Starts the FastAPI server
4. Waits for `/health` to return 200
5. Runs `scripts/trigger_qa.py` against a ticket
6. Uploads HTML report + test cases as workflow artefacts
7. Posts QA summary to Jira (if `upload_to_jira=true`)

### Trigger via REST

```bash
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/shrikantkingdom/qa-agent-platform/actions/workflows/qa-workflow.yml/dispatches \
  -d '{"ref": "main", "inputs": {"jira_id": "CRFLT-1", "team_id": "statements", "upload_to_jira": "true"}}'
```

## Execution Models

The platform is API-first — the orchestration logic lives in one place, and the trigger mechanism is interchangeable.

| Model | How | Best For |
|-------|-----|----------|
| **Web UI** | Browser at `localhost:8000` | Daily QA use, non-technical users |
| **Jira Automation** | Webhook on status transition | Enterprise teams who live in Jira |
| **GitHub Actions** | CI/CD workflow dispatch | Automated regression on PR open |
| **CLI** | `python scripts/trigger_qa.py --jira-id CRFLT-1` | Engineering / scripting |
| **curl / API** | `POST /api/v1/run-qa` | Any integration |
| **ChatOps** | Slack `/qa-run CRFLT-1` (roadmap) | Quick access, team visibility |
| **Scheduled** | Cron → `/release-qa` (roadmap) | Continuous QA governance |

### Architecture Decision

```
┌─────────────────────────────────────────────────┐
│            Trigger Layer (interchangeable)       │
│  Web UI │ GitHub Actions │ Jira │ Slack │ Cron  │
└─────────────────────┬───────────────────────────┘
                      │ POST /api/v1/run-qa
                      ▼
┌─────────────────────────────────────────────────┐
│         Orchestration Layer (single source)      │
│  FastAPI → workflow_service → ai_service         │
│  Jira REST API + GitHub REST API integration     │
└─────────────────────────────────────────────────┘
```

Add a new trigger (Slack bot, cron job) without touching the workflow logic.

## Exposing Locally (ngrok)

For Jira Automation webhooks during local development:

```bash
brew install ngrok
ngrok http 8000
```

Use the HTTPS URL from ngrok in the Jira Automation rule. See [03-jira-webhook-setup.md](03-jira-webhook-setup.md) for details.

**In production**, use the real application URL — no ngrok needed.
