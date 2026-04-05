# 01 — Quick Start

Get the QA Agent Platform running and analyse your first Jira ticket in under 5 minutes.

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.11+ | `python3 --version` |
| pip | latest | `pip --version` |
| Git | any | `git --version` |

## 1. Clone and Install

```bash
git clone https://github.com/shrikantkingdom/qa-agent-platform.git
cd qa-agent-platform
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — minimum required settings:

```dotenv
# AI Provider (GitHub Models is free)
LLM_PROVIDER=github
OPENAI_API_KEY=ghp_yourGitHubPAThere
OPENAI_MODEL=gpt-4o
```

**Demo mode** (no Jira/GitHub credentials needed):
```dotenv
USE_MOCK_JIRA=true
USE_MOCK_GITHUB=true
```

**Real mode** (connects to your Jira and GitHub):
```dotenv
USE_MOCK_JIRA=false
JIRA_BASE_URL=https://your-org.atlassian.net/
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=ATATTxxx...
JIRA_PROJECT_KEY=CRFLT

USE_MOCK_GITHUB=false
GITHUB_TOKEN=ghp_yourToken
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo
```

## 3. Start the Server

```bash
# Standard
uvicorn app.main:app --reload

# Or use Make
make dev
```

## 4. Run Your First Analysis

### Option A — Web UI

1. Open **http://localhost:8000**
2. Enter a Jira ticket ID (e.g. `CRFLT-1`)
3. Select a team from the dropdown (e.g. `statements`)
4. Click **Run QA Analysis**
5. Review the results: quality score, test cases, BDD scenarios
6. Click **Upload to Jira** to post the reviewed summary as a Jira comment
7. Click **Push Tests** to push generated step definitions to your automation repo

### Option B — curl

```bash
curl -X POST http://localhost:8000/api/v1/run-qa \
  -H "Content-Type: application/json" \
  -d '{"jira_id": "CRFLT-1", "team_id": "statements", "post_to_jira": true}'
```

### Option C — Jira Automation (auto-trigger)

Set up a Jira Automation rule that fires a webhook when a ticket transitions to "In Progress". The platform runs the QA workflow and posts results back as a comment — no manual action required.

See [03-jira-webhook-setup.md](03-jira-webhook-setup.md) for full setup instructions with real CRFLT project examples.

## 5. Generated Outputs

After a successful run, find your artefacts in:

| Output | Location | Format |
|--------|----------|--------|
| HTML Report | `outputs/reports/CRFLT-1_report.html` | Standalone HTML |
| Test Cases | `outputs/testcases/CRFLT-1_testcases.csv` | CSV |
| BDD Feature | `outputs/bdd/CRFLT-1.feature` | Gherkin |
| Step Definitions | `outputs/bdd/CRFLT-1_steps.py` | Python (pytest-bdd) |

## What's Next

| Goal | Doc |
|------|-----|
| Understand the architecture | [02-architecture.md](02-architecture.md) |
| Set up Jira webhook auto-trigger | [03-jira-webhook-setup.md](03-jira-webhook-setup.md) |
| Configure a different AI provider | [04-installation.md](04-installation.md) |
| Add your team's context | [05-team-onboarding.md](05-team-onboarding.md) |
| Deploy to production | [06-deployment.md](06-deployment.md) |
| Full API reference | [07-api-reference.md](07-api-reference.md) |
