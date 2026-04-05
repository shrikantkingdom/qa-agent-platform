# 04 — Installation & Setup Guide

> **Platform**: macOS / Linux / Windows (WSL recommended)
>
> See [01-quick-start.md](01-quick-start.md) for the 5-minute version.
> See [08-troubleshooting.md](08-troubleshooting.md) for FAQ & common errors.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Configure Your AI Provider](#3-configure-your-ai-provider)
4. [Configure Jira](#4-configure-jira)
5. [Configure GitHub](#5-configure-github)
6. [Start the Platform](#6-start-the-platform)
7. [Use the Platform](#7-use-the-platform)
8. [Multi-Team Setup](#8-multi-team-setup)
9. [Switching Providers On-the-Fly](#9-switching-providers-on-the-fly)

---

## 1. Prerequisites

| Tool | Required | Version | Install |
|------|----------|---------|---------|
| Python | ✅ | 3.11+ | [python.org](https://www.python.org/downloads/) |
| pip | ✅ | bundled | — |
| Git | ✅ | any | `brew install git` / [git-scm.com](https://git-scm.com) |
| Jira Cloud account | ✅ | any | [atlassian.com](https://www.atlassian.com/software/jira) |
| GitHub account | ✅ | any | [github.com](https://github.com) |
| At least 1 AI API key | ✅ | — | See Section 4 |

### Check your Python version
```bash
python3 --version    # must be 3.11 or higher
```

If you have Python 3.9 or 3.10, use `pyenv` to install 3.11:
```bash
brew install pyenv
pyenv install 3.11
pyenv global 3.11
```

---

## 2. Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/qa-agent-platform.git
cd qa-agent-platform

# 2. Create a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate          # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example config and edit it
cp .env.example .env
# Now edit .env with your API keys — see Sections 4, 5, 6

# 5. Create output directories (first time only)
mkdir -p outputs/reports outputs/testcases outputs/bdd

# 6. Start the platform
./start.sh
```

Open your browser at **http://localhost:8000**

---

## 3. Configure Your AI Provider

Open `.env` in any text editor. Find the `LLM Provider` block and change just **3 lines**:

```dotenv
LLM_PROVIDER=<provider>
OPENAI_API_KEY=<your_key>
OPENAI_MODEL=<model_name>
```

The `OPENAI_BASE_URL` is set automatically from `LLM_PROVIDER`. You do **not** need to change it unless you have a custom endpoint.

---

### 3.1 GitHub Models (Free — Recommended)

**Cost**: Free (included with any GitHub account)  
**Models available**: gpt-4o, gpt-4o-mini, gpt-4.1, Llama 3.3, Phi-4, Mistral, and more  
**Limits**: 15 requests/min, 150/day for free accounts; higher with GitHub Copilot Pro

**Get a GitHub Classic PAT:**
1. Go to **github.com** → Settings → Developer settings → Personal access tokens → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name: `qa-platform-models`
4. Expiry: 90 days (or No expiration)
5. Scopes: check **`read:user`** (minimum) — no repo scopes needed for Models API
6. Click **Generate token** and copy it immediately

**`.env` configuration:**
```dotenv
LLM_PROVIDER=github
OPENAI_API_KEY=ghp_yourTokenHere
OPENAI_MODEL=gpt-4o
# OPENAI_BASE_URL is set automatically to https://models.inference.ai.azure.com
```

**Available models to use in `OPENAI_MODEL`:**
- `gpt-4o` — Best all-round (recommended)
- `gpt-4o-mini` — Faster, cheaper
- `gpt-4.1` — Latest GPT (if available on your account)
- `meta-llama-3.3-70b-instruct` — Open-source alternative
- `phi-4` — Microsoft's compact model

---

### 3.2 OpenAI

**Cost**: Pay-per-use (~ $0.002–0.015 per QA run)  
**Get API key:**
1. Go to **platform.openai.com** → Log in
2. Click your profile → **API keys**
3. Click **Create new secret key**
4. Copy it immediately (shown only once)
5. Add billing info at **platform.openai.com/settings/billing**

**`.env` configuration:**
```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-yourKeyHere
OPENAI_MODEL=gpt-4o
# OPENAI_BASE_URL should be left unset (or empty) for default OpenAI endpoint
```

**Models:** `gpt-4o` (best), `gpt-4o-mini` (cheap), `gpt-4.1`, `o3-mini`

---

### 3.3 Anthropic (Claude)

**Cost**: Pay-per-use (~$0.003–0.015 per run)  
**Get API key:**
1. Go to **console.anthropic.com** → Sign up / Log in
2. Click **API Keys** in the left sidebar
3. Click **Create Key**
4. Copy the key (starts with `sk-ant-`)

**`.env` configuration:**
```dotenv
LLM_PROVIDER=anthropic
OPENAI_API_KEY=sk-ant-yourKeyHere
OPENAI_MODEL=claude-3-5-sonnet-20241022
# OPENAI_BASE_URL is set automatically to https://api.anthropic.com/v1
```

**Models:** `claude-3-5-sonnet-20241022` (best), `claude-3-5-haiku-20241022` (fast), `claude-3-opus-20240229` (most powerful)

> **Note:** Claude does not support JSON mode response format. The platform automatically falls back to prompt-based JSON extraction for Claude.

---

### 3.4 DeepSeek

**Cost**: Very cheap (~$0.0003 per run)  
**Get API key:**
1. Go to **platform.deepseek.com** → Sign up
2. Click **API Keys** in the left sidebar
3. Click **Create new API key**
4. Copy the key (starts with `sk-`)

**`.env` configuration:**
```dotenv
LLM_PROVIDER=deepseek
OPENAI_API_KEY=sk-yourKeyHere
OPENAI_MODEL=deepseek-chat
# OPENAI_BASE_URL is set automatically to https://api.deepseek.com
```

**Models:** `deepseek-chat` (V3, recommended), `deepseek-reasoner` (R1, best for complex analysis)

---

### 3.5 Groq

**Cost**: Free generous tier (14,400 tokens/min free)  
**Get API key:**
1. Go to **console.groq.com** → Sign up (GitHub or Google login)
2. Click **API Keys** in the left sidebar
3. Click **Create API Key**
4. Copy the key (starts with `gsk_`)

**`.env` configuration:**
```dotenv
LLM_PROVIDER=groq
OPENAI_API_KEY=gsk_yourKeyHere
OPENAI_MODEL=llama-3.3-70b-versatile
# OPENAI_BASE_URL is set automatically to https://api.groq.com/openai/v1
```

**Models:** `llama-3.3-70b-versatile` (recommended), `llama-3.1-8b-instant` (ultra-fast), `mixtral-8x7b-32768`

---

### 3.6 Mistral

**Cost**: Pay-per-use, competitive pricing  
**Get API key:**
1. Go to **console.mistral.ai** → Sign up
2. Click **API Keys** in the left sidebar
3. Click **Create new key**
4. Copy the key

**`.env` configuration:**
```dotenv
LLM_PROVIDER=mistral
OPENAI_API_KEY=yourKeyHere
OPENAI_MODEL=mistral-large-latest
# OPENAI_BASE_URL is set automatically to https://api.mistral.ai/v1
```

**Models:** `mistral-large-latest` (best), `mistral-small-latest` (cheap), `codestral-latest` (code-focused)

---

### 3.7 Ollama (Local)

**Cost**: Free — runs entirely on your machine  
**Requires**: 8GB+ RAM (16GB+ for best results), optionally an NVIDIA/Apple Silicon GPU

**Install Ollama:**
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

**Pull a model:**
```bash
ollama pull llama3.1          # 4.7 GB — recommended
ollama pull phi4              # 2.5 GB — fast Microsoft model  
ollama pull deepseek-r1:7b    # 4.7 GB — reasoning model
```

**Start Ollama server** (runs in background):
```bash
ollama serve
```

**`.env` configuration** (no API key needed):
```dotenv
LLM_PROVIDER=ollama
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.1
# OPENAI_BASE_URL is set automatically to http://localhost:11434/v1
```

> **Tip:** Ollama does not support JSON mode. The platform handles this automatically.

---

### 3.8 Google Gemini

**Cost**: Very generous free tier (15 req/min, 1M tokens/day free)  
**Get API key:**
1. Go to **aistudio.google.com**
2. Click **Get API Key** in the top-right
3. Click **Create API key in new project** (or select existing)
4. Copy the key (starts with `AIza`)

**`.env` configuration:**
```dotenv
LLM_PROVIDER=gemini
OPENAI_API_KEY=AIzaYourKeyHere
OPENAI_MODEL=gemini-2.0-flash
# OPENAI_BASE_URL is set automatically to https://generativelanguage.googleapis.com/v1beta/openai/
```

**Models:** `gemini-2.0-flash` (fastest/free), `gemini-1.5-pro` (most capable)

---

### 3.9 Azure OpenAI

**Cost**: Pay-per-use (Azure billing)  
**Requires**: Azure subscription + Azure OpenAI resource deployed

**Get credentials:**
1. Go to **portal.azure.com** → Azure OpenAI
2. Create or open an Azure OpenAI resource
3. Go to **Keys and Endpoint** in the resource blade
4. Copy **Key 1** and the **Endpoint URL**

**`.env` configuration:**
```dotenv
LLM_PROVIDER=azure
OPENAI_API_KEY=yourAzureKeyHere
OPENAI_MODEL=gpt-4o         # must match your deployment name
OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/
```

---

## 4. Configure Jira

### Get Your Jira API Token

1. Log in to **id.atlassian.com/manage-profile/security/api-tokens**
2. Click **Create API token**
3. Name it: `qa-platform`
4. Click **Create** and copy the token immediately

### Find Your Jira URL

Your Jira URL is in the format: `https://your-org.atlassian.net/`  
(visible in your browser when on your Jira board)

### `.env` configuration:
```dotenv
USE_MOCK_JIRA=false
JIRA_BASE_URL=https://your-org.atlassian.net/
JIRA_API_TOKEN=ATATTxxx...your_token_here
JIRA_EMAIL=your_email@company.com
JIRA_PROJECT_KEY=PROJ        # The prefix before ticket numbers, e.g. CRFLT, PROJ, DEV
```

### Test the Jira connection:
```bash
source .venv/bin/activate
python -c "
import asyncio
from app.services.jira_service import JiraService
jira = JiraService()
async def test():
    t = await jira.get_ticket('YOUR-PROJECT-1')   # replace with a real ticket key
    print(t)
asyncio.run(test())
"
```

---

## 5. Configure GitHub

### Get a GitHub Personal Access Token

For GitHub **code analysis** (reading commits):
1. Go to **github.com** → Settings → Developer settings → Personal access tokens → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name: `qa-platform`
4. Scopes needed: **`repo`** (private repos) or **`public_repo`** (public only)
5. Click Generate and copy

> **Note:** If using GitHub Models for your AI provider, use the same PAT — one token works for both.

### `.env` configuration:
```dotenv
USE_MOCK_GITHUB=false
GITHUB_TOKEN=ghp_yourTokenHere
GITHUB_REPO_OWNER=your-github-username-or-org
GITHUB_REPO_NAME=your-repo-name          # Just the name, NOT the full URL
GITHUB_AUTOMATION_REPO=your-test-repo    # Optional: for BDD step push-back
```

---

## 6. Start the Platform

```bash
# Standard start
./start.sh

# On a custom port
./start.sh --port 9000

# With hot-reload (development mode)
./start.sh --reload

# Override AI provider without editing .env
./start.sh --provider groq

# Load a team-specific config
./start.sh --team mobile

# Windows (if start.sh doesn't run)
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

---

## 7. Use the Platform

### Web UI

1. Enter a Jira ticket key (e.g. `CRFLT-1`) in the text field
2. Check **Generate BDD scenarios** if you want Gherkin feature files
3. Click **Run QA Analysis**
4. Watch the live progress log
5. When complete:
   - View the quality score and grade in the results panel
   - Click **Download HTML Report** for the full report
   - Click **Test Cases (CSV)** to import into TestRail / Xray / Zephyr
   - Click **BDD Feature File** to copy into your automation project

### REST API (for CI/CD integration)

```bash
# Run QA workflow
curl -X POST http://localhost:8000/api/v1/run-qa \
  -H "Content-Type: application/json" \
  -d '{"jira_id": "CRFLT-1", "include_bdd": true}'

# Health check
curl http://localhost:8000/api/v1/health

# List available AI providers
curl http://localhost:8000/api/v1/providers

# Current configuration
curl http://localhost:8000/api/v1/config
```

---

## 8. Multi-Team Setup

Each team can use a different Jira project, GitHub repo, and AI provider without touching the shared `.env`.

### Create a team profile:
```bash
cp config/teams/example.env config/teams/mobile.env
# Edit config/teams/mobile.env with team-specific settings
```

### Example `config/teams/mobile.env`:
```dotenv
APP_NAME=QA Platform - Mobile Team
JIRA_PROJECT_KEY=MOBILE
GITHUB_REPO_NAME=mobile-app
LLM_PROVIDER=groq
OPENAI_API_KEY=gsk_mobile_team_key
OPENAI_MODEL=llama-3.3-70b-versatile
```

### Start for a specific team:
```bash
./start.sh --team mobile --port 8001
./start.sh --team backend --port 8002
./start.sh --team frontend --port 8003
```

Each team instance is isolated on its own port.

---

## 9. Switching Providers On-the-Fly

Change just 3 lines in `.env`, then restart:

| To switch to | `LLM_PROVIDER` | `OPENAI_API_KEY` starts with | Typical `OPENAI_MODEL` |
|---|---|---|---|
| GitHub Models | `github` | `ghp_` | `gpt-4o` |
| OpenAI | `openai` | `sk-proj-` | `gpt-4o` |
| Claude | `anthropic` | `sk-ant-` | `claude-3-5-sonnet-20241022` |
| DeepSeek | `deepseek` | `sk-` | `deepseek-chat` |
| Groq | `groq` | `gsk_` | `llama-3.3-70b-versatile` |
| Mistral | `mistral` | any | `mistral-large-latest` |
| Ollama | `ollama` | `ollama` | `llama3.1` |
| Gemini | `gemini` | `AIza` | `gemini-2.0-flash` |
| Azure OpenAI | `azure` | any | your deployment name |

You can also override without editing `.env`:
```bash
LLM_PROVIDER=groq OPENAI_API_KEY=gsk_xxx ./start.sh
# or
./start.sh --provider deepseek
```

---

