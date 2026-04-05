# QA Agent Platform

AI-powered QA workflow automation for Jira-driven development teams. Enter a Jira ticket ID — get a quality score, test cases, BDD scenarios, pytest-bdd step definitions, and a full HTML report.

**Two trigger modes:**
1. **Web UI** — open `http://localhost:8000`, enter a ticket, click Run
2. **Jira Automation** — webhook fires automatically on status transition, posts results back as a Jira comment

## Quick Start

```bash
git clone https://github.com/shrikantkingdom/qa-agent-platform.git
cd qa-agent-platform
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # configure LLM + Jira + GitHub keys
uvicorn app.main:app --reload
```

Open **http://localhost:8000** — enter `CRFLT-1` and click **Run QA Analysis**.

See [docs/01-quick-start.md](docs/01-quick-start.md) for the full walkthrough.

## How It Works

```
Jira Ticket → 9-step AI pipeline → Quality Score + Test Cases + BDD + HTML Report
```

| Step | What happens |
|------|-------------|
| 1 | Fetch Jira ticket (title, AC, labels, custom fields) |
| 2 | Fetch recent GitHub commits |
| 3 | AI validates ticket quality → score 0–100, grade A–F |
| 4 | AI checks requirement–code alignment → coverage gaps |
| 5 | AI generates 8–15 test cases (happy path, negative, edge case) |
| 6 | Export test cases to CSV |
| 7 | AI generates BDD Gherkin scenarios |
| 8 | AI generates pytest-bdd step definitions |
| 9 | Render HTML report |

## Project Structure

```
qa-agent-platform/
├── app/                  # FastAPI backend (routes, services, models, config)
├── ui/                   # Single-page browser UI (no build step)
├── config/               # Team context files + Jira project config
├── templates/            # Jinja2 HTML report template
├── outputs/              # Generated reports, test cases, BDD files
├── tests/                # pytest test suite
├── scripts/              # CLI trigger script
├── docs/                 # Full documentation (see index below)
├── Dockerfile            # Container build
├── docker-compose.yml    # One-command deployment
├── Makefile              # Dev shortcuts (make run, make test, make dev)
└── requirements.txt
```

## Documentation Index

| Doc | Topic |
|-----|-------|
| [01-quick-start.md](docs/01-quick-start.md) | End-to-end setup and first run |
| [02-architecture.md](docs/02-architecture.md) | System design, 9-step workflow, LLM layer, team context |
| [03-jira-webhook-setup.md](docs/03-jira-webhook-setup.md) | Jira Automation webhook trigger (with CRFLT examples) |
| [04-installation.md](docs/04-installation.md) | Prerequisites, 9 AI providers, Jira/GitHub config |
| [05-team-onboarding.md](docs/05-team-onboarding.md) | Adding a new team in 30 minutes |
| [06-deployment.md](docs/06-deployment.md) | Docker, production, CI/CD, execution models |
| [07-api-reference.md](docs/07-api-reference.md) | All endpoints with request/response examples |
| [08-troubleshooting.md](docs/08-troubleshooting.md) | Common errors and fixes |
| [09-innovation-story.md](docs/09-innovation-story.md) | Problem statement, design decisions, ROI |
| [10-interview-qa.md](docs/10-interview-qa.md) | Deep Q&A for interviews and knowledge transfer |
| [11-rebuild-guide.md](docs/11-rebuild-guide.md) | Step-by-step rebuild reference |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Pydantic v2 |
| LLM | AsyncOpenAI (9 providers: GitHub Models, OpenAI, Anthropic, Azure, Groq, Ollama, etc.) |
| Jira | REST API v3 + Automation webhooks |
| GitHub | REST API (commits, file push, PR creation) |
| UI | Vanilla HTML/JS (single file, no build step) |
| Reports | Jinja2 HTML templates |
| Container | Docker + docker-compose |

## License

MIT
