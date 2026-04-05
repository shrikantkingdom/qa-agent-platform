# Jira Automation — QA Agent Integration Guide

> This guide explains how to trigger the QA Agent Platform directly from Jira so that a QA
> analysis starts automatically every time a ticket changes state — with no manual steps required.

---

## Overview

```
Jira ticket event (transition / button click)
        │
        ▼
Jira Automation Rule ── HTTP POST ──▶ POST /api/v1/webhooks/jira
                                              │
                                              ▼
                                     FastAPI background task
                                     9-step AI QA workflow
                                              │
                                              ▼
                                  🤖 QA comment posted back to Jira
```

The platform webhook returns **202 Accepted** immediately — the analysis runs in the background
and posts the result as a Jira comment once complete (~60–90 seconds).

---

## Prerequisites

| Item | Details |
|------|---------|
| Platform deployed | The API must be reachable from Jira's servers. For local dev use [ngrok](https://ngrok.com): `ngrok http 8000` |
| Platform URL | Note your deployment URL — e.g. `https://qa-agent.internal.com` or ngrok URL |
| `JIRA_WEBHOOK_SECRET` set | Generate and add to `.env` — see [Step 1](#step-1--generate-and-configure-the-shared-secret) |
| Jira Admin access | Required to create Automation rules |

---

## Step 1 — Generate and Configure the Shared Secret

The shared secret prevents unauthenticated callers from triggering expensive LLM workflows.

```bash
# Generate a strong secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: yXp3mT8k9v2Fq7rN1wZ6cA4jO0bL5eUs
```

Add to your `.env`:
```
JIRA_WEBHOOK_SECRET=yXp3mT8k9v2Fq7rN1wZ6cA4jO0bL5eUs
```

Restart the platform after updating `.env`.

---

## Step 2 — Jira Automation Rule (Trigger on Ticket Transition)

This is the recommended approach for teams. A QA analysis fires automatically whenever a
ticket moves to **"In Progress"** (or any status you choose).

### 2.1 Open Jira Automation

1. Go to your CRFLT project in Jira
2. Click **Project Settings** → **Automation**
3. Click **Create rule**

### 2.2 Configure the Trigger

| Setting | Value |
|---------|-------|
| Trigger | **Issue transitioned** |
| From status | *(any)* |
| To status | **In Progress** *(or "In QA" / "In Review")* |

> **Tip:** To restrict to Stories only, add a **Condition** step:
> `Issue type = Story`

### 2.3 Add the "Send web request" Action

1. Click **+ New action** → **Send web request**
2. Fill in the fields:

| Field | Value |
|-------|-------|
| **URL** | `https://<your-platform-url>/api/v1/webhooks/jira` |
| **HTTP method** | `POST` |
| **Headers** | `Content-Type: application/json` |
| | `X-Webhook-Secret: <your JIRA_WEBHOOK_SECRET value>` |
| **Body (custom data)** | See below |

**Request body:**
```json
{
  "issue_key": "{{issue.key}}",
  "components": ["{{#issue.components}}{{name}}{{^last}},{{/last}}{{/issue.components}}"],
  "triggered_by": "{{rule.name}}",
  "post_to_jira": true
}
```

> **Note on the components field:** Jira Automation smart values do not produce a JSON array
> natively. If the smart value syntax above does not work in your Jira version, hardcode the
> component name as a fallback:
> ```json
> {
>   "issue_key": "{{issue.key}}",
>   "components": ["CR-statements"],
>   "triggered_by": "jira-automation",
>   "post_to_jira": true
> }
> ```
> Or use the `team_id` field to bypass component resolution entirely:
> ```json
> {
>   "issue_key": "{{issue.key}}",
>   "team_id": "statements",
>   "triggered_by": "jira-automation",
>   "post_to_jira": true
> }
> ```

### 2.4 Save and Enable

1. Give the rule a name: **"Run QA AI Analysis on In Progress"**
2. Click **Save**
3. Toggle the rule to **Enabled**

### 2.5 Test the Rule

1. Open any CRFLT ticket (e.g. CRFLT-1)
2. Click `...` → **Automation** → find your rule → **Run rule**
3. Watch the Jira ticket — a comment from the QA Agent should appear within ~90 seconds

---

## Step 3 — Manual Trigger Button (Optional)

To add a one-click "Run QA" button visible on every ticket:

1. **Project Settings → Automation → Create rule**
2. **Trigger:** Manual trigger → Issue (allow users to run on individual issues)
3. **Action:** Send web request — same URL and body as Step 2.3 above
4. **Name:** `Run QA AI Analysis`
5. Save and enable

A **lightning bolt** icon will appear on every ticket — any team member can trigger a QA
analysis on demand without transitioning the ticket.

---

## Step 4 — Webhook Payload Reference

Full payload schema for `POST /api/v1/webhooks/jira`:

```json
{
  "issue_key": "CRFLT-123",
  "components": ["CR-statements"],
  "team_id": null,
  "triggered_by": "jira-automation",
  "post_to_jira": true,
  "custom_prompt": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `issue_key` | string | ✅ | Jira ticket ID |
| `components` | string[] | ❌ | Component names from the ticket — used for team auto-detection |
| `team_id` | string | ❌ | Explicit team override. One of: `statements`, `confirms`, `letters` |
| `triggered_by` | string | ❌ | Label for audit log (e.g. Jira account ID) |
| `post_to_jira` | bool | ❌ | Default `true` — post result as Jira comment |
| `custom_prompt` | string | ❌ | Extra context injected into the AI prompt |

**Team resolution order:**
1. `team_id` field if provided
2. First matching entry in components against `CR-statements / CR-confirms / CR-letters`
3. Falls back to `default_team` in settings (`statements`)

---

## Step 5 — Verify the Webhook

### Test with curl (wrong secret → 403)
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: wrong-secret" \
  -d '{"issue_key": "CRFLT-1"}'
# Expected: 403
```

### Test with curl (correct secret → 202)
```bash
curl -s \
  -X POST http://localhost:8000/api/v1/webhooks/jira \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: <your JIRA_WEBHOOK_SECRET>" \
  -d '{
    "issue_key": "CRFLT-1",
    "components": ["CR-statements"],
    "triggered_by": "curl-test",
    "post_to_jira": true
  }'
# Expected: {"status":"accepted","jira_id":"CRFLT-1","team_id":"statements",...}
```

Check CRFLT-1 in Jira ~90 seconds later — a new QA Agent comment should appear.

---

## Step 6 — Jira Forge App (Advanced — Permanent Panel Button)

The Forge app adds a **"QA Agent"** panel to the right sidebar of every CRFLT issue.
QA engineers see the grade and score inline without leaving the ticket.

> **Prerequisite:** The platform must be publicly accessible via HTTPS.
> The Forge backend (resolver) cannot reach `localhost`.

### 6.1 Install Forge CLI

```bash
npm install -g @forge/cli
forge login   # opens browser to authenticate with your Atlassian account
```

### 6.2 Deploy the App

```bash
cd forge-app
npm install
forge deploy
forge install --site shrikantpatil.atlassian.net
```

### 6.3 Local Development (Tunnel)

```bash
# In one terminal — keep the platform running
uvicorn app.main:app --reload --port 8000

# In another terminal — expose via ngrok (Forge needs a public URL)
ngrok http 8000

# Update PLATFORM_URL in forge-app/.env.forge with the ngrok URL

# In another terminal — start Forge tunnel
cd forge-app && forge tunnel
```

Open any CRFLT ticket in Jira — the **"QA Agent Analysis"** panel appears on the right sidebar.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Jira Automation shows "400 Bad Request" | Body JSON malformed | Validate JSON in the Automation rule editor; use hardcoded `team_id` instead of smart values |
| Jira Automation shows "403 Forbidden" | Wrong or missing `X-Webhook-Secret` header | Check the header value matches `JIRA_WEBHOOK_SECRET` in `.env` exactly |
| Automation shows "200 OK" but no Jira comment appears | `post_to_jira` is `false` or `USE_MOCK_JIRA=true` | Set `"post_to_jira": true` in body; verify `USE_MOCK_JIRA=false` in `.env` |
| Automation shows "504 Gateway Timeout" | Jira waited for a response that took >30s | The webhook should return 202 immediately — check the platform is running and the URL is correct |
| Forge panel not appearing | App not installed on correct site | Run `forge install --site <your-site>.atlassian.net` and select the CRFLT project |
| Team resolved as "statements" for a confirms ticket | Component name not matching | Pass explicit `"team_id": "confirms"` in the webhook body, or check that the Jira component is named exactly `CR-confirms` |
