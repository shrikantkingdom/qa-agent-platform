# 08 — Troubleshooting

Common errors and how to fix them.

---

## Server & Startup

### "Connection refused" on port 8000

```bash
lsof -i :8000                     # check what's using the port
kill -9 <PID>                      # free it
uvicorn app.main:app --reload      # restart
```

### "ModuleNotFoundError: No module named 'app'"

You're running from the wrong directory. Make sure you're in `qa-agent-platform/`:

```bash
cd /path/to/qa-agent-platform
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Python version errors

```bash
python3 --version    # needs 3.11+
```

If lower, install via pyenv:
```bash
brew install pyenv
pyenv install 3.11.9
pyenv local 3.11.9
```

---

## AI Provider Issues

### "Authentication failed" on LLM calls

- Check `OPENAI_API_KEY` in `.env` — no extra spaces or quotes
- GitHub PATs expire — regenerate if needed
- OpenAI requires a payment method on file

### "JSON parsing failed"

Rare edge case where the LLM returns markdown fences instead of raw JSON. The platform handles this automatically with fence stripping. If it persists:

```dotenv
LLM_TEMPERATURE=0.0    # add to .env
```

### Out-of-quota (OpenAI)

Switch to a free provider:
```dotenv
LLM_PROVIDER=github     # free with any GitHub account
# or
LLM_PROVIDER=groq       # free tier: 14,400 tokens/min
# or
LLM_PROVIDER=gemini     # free tier: 15 req/min, 1M tokens/day
```

### Slow responses

| Provider | Typical latency |
|----------|----------------|
| Groq | 3–8 seconds |
| GitHub Models | 20–40 seconds |
| OpenAI | 20–40 seconds |
| Ollama (M2/M3) | 15–60 seconds |

---

## Jira Issues

### "Jira ticket not found" (404)

- Check `JIRA_PROJECT_KEY` matches the prefix (e.g. `CRFLT` for `CRFLT-1`)
- Check `JIRA_BASE_URL` ends with `/` — e.g. `https://your-org.atlassian.net/`
- Verify your API token is valid:

```bash
curl -u your@email.com:YOUR_API_TOKEN \
  "https://your-org.atlassian.net/rest/api/3/issue/CRFLT-1"
```

### Webhook returns 403

**Cause:** `localhost:8000` is not reachable from Atlassian Cloud.

**Fix:** Use ngrok for local development:
```bash
brew install ngrok
ngrok http 8000
# Use the https://xxxx.ngrok-free.app URL in the Jira Automation rule
```

### Webhook returns 401

**Cause:** `X-Webhook-Secret` header doesn't match `JIRA_WEBHOOK_SECRET` in `.env`.

**Fix:** Ensure the Jira Automation rule sends the exact same secret value in the custom header.

### Webhook returns 422

**Cause:** Invalid JSON payload.

**Common mistake:**
```json
{"components": "CR-statements"}     ← wrong (string)
{"components": ["CR-statements"]}   ← correct (array)
```

---

## GitHub Issues

### "GitHub repo not found" (404)

- Check `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` — just the name, not the full URL
- Ensure your PAT has `repo` scope (for private repos)

### Push tests fails

- Check `GITHUB_AUTOMATION_REPO` is set to the test automation repo name
- Ensure PAT has `contents: write` and `pull_requests: write` permissions

---

## Docker Issues

### Container can't read `.env`

The `docker-compose.yml` mounts `.env` via `env_file`. Ensure the file exists in the project root:

```bash
cp .env.example .env
docker compose up --build
```

### Outputs disappear after restart

Outputs are mounted as a volume. Check `docker-compose.yml` has:
```yaml
volumes:
  - ./outputs:/app/outputs
```

---

## General

### Mock mode vs Live mode

| Setting | Mock (demo) | Live (real) |
|---------|------------|------------|
| `USE_MOCK_JIRA` | `true` | `false` |
| `USE_MOCK_GITHUB` | `true` | `false` |
| AI provider | Any (including no key) | Requires valid key |

Mock mode returns built-in demo data — useful for testing the platform without credentials.

### Where are my outputs?

```
outputs/
├── reports/       # HTML reports
├── testcases/     # CSV + JSON
└── bdd/           # .feature + _steps.py
```

Clean them with: `make clean`
