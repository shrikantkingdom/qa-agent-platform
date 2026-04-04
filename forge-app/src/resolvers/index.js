import Resolver from "@forge/resolver";
import api, { fetch } from "@forge/api";

// ── Configuration ─────────────────────────────────────────────────────────────
// Set PLATFORM_URL and JIRA_WEBHOOK_SECRET in your Forge environment variables:
//   forge variables set --environment production PLATFORM_URL https://your-platform.com
//   forge variables set --environment production JIRA_WEBHOOK_SECRET your-secret
const PLATFORM_URL = process.env.PLATFORM_URL || "http://localhost:8000";
const WEBHOOK_SECRET = process.env.JIRA_WEBHOOK_SECRET || "";

const resolver = new Resolver();

// ── runQA invocation ──────────────────────────────────────────────────────────
// Called from the UI panel when the QA engineer clicks "Run QA AI Analysis".
// Sends a webhook to the FastAPI backend and waits for the 202 acceptance.
// The actual workflow result is posted to Jira as a comment by the backend.
resolver.define("runQA", async ({ payload, context }) => {
  const { issueKey } = payload;

  if (!issueKey) {
    return { error: "No issue key provided." };
  }

  // Resolve team from Jira components field (fetch issue details to get components)
  let components = [];
  let summary = "";
  try {
    const issueResponse = await api
      .asUser()
      .requestJira(`/rest/api/3/issue/${issueKey}?fields=components,summary`);
    if (issueResponse.ok) {
      const issueData = await issueResponse.json();
      components = (issueData.fields?.components ?? []).map((c) => c.name);
      summary = issueData.fields?.summary ?? "";
    }
  } catch (_) {
    // Non-fatal — backend will fall back to default team if components is empty
  }

  const requestBody = {
    issue_key: issueKey,
    components,
    triggered_by: context.accountId || "forge-app",
    post_to_jira: true,
    custom_prompt: null,
  };

  let response;
  try {
    response = await fetch(`${PLATFORM_URL}/api/v1/webhooks/jira`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(WEBHOOK_SECRET ? { "X-Webhook-Secret": WEBHOOK_SECRET } : {}),
      },
      body: JSON.stringify(requestBody),
    });
  } catch (networkErr) {
    return {
      error: `Could not reach the QA platform at ${PLATFORM_URL}. Check PLATFORM_URL env var and ensure the server is running.`,
    };
  }

  if (response.status === 403) {
    return {
      error:
        "Authentication failed (403). Check that JIRA_WEBHOOK_SECRET in the Forge environment matches the platform setting.",
    };
  }

  if (response.status !== 202) {
    const body = await response.text();
    return {
      error: `Unexpected response from platform: HTTP ${response.status} — ${body}`,
    };
  }

  const data = await response.json();

  return {
    accepted: true,
    jira_id: data.jira_id,
    team_id: data.team_id,
    quality_score: null,   // score available only after background workflow completes
    grade: null,
    summary: `Analysis for ${issueKey} (${summary}) is running in the background. A comment will appear on this ticket when complete.`,
  };
});

export const handler = resolver.getDefinitions();
