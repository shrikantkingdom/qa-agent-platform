# 10 — Interview Questions & Answers

Deep Q&A covering architecture, design decisions, LLM engineering, security, scalability, and career context. Useful for interviews, knowledge transfer, and stakeholder presentations.

---

## About the Problem

**Q: Why not just use Jira plugins or existing test management tools like Zephyr or Xray?**

A: Jira plugins manage test execution but do not generate test cases, validate ticket quality, or check requirement-code alignment. They require a QA engineer to author everything manually and then enter it into the tool. The platform automates the authoring step — the most time-consuming part — and integrates with existing Jira workflows, not against them.

---

**Q: How do you know the AI-generated test cases are correct?**

A: They are not assertions of correctness — they are a structured first draft. The QA engineer reviews every generated test case before it is uploaded to Jira. The platform's value is in reducing blank-page authoring time by 85%, not in removing the engineer's judgment. Incorrect suggestions are edited or deleted in the review UI.

---

**Q: Couldn't a junior QA write faster test cases once experienced?**

A: Experienced QAs write faster test cases, yes. But they still start from scratch on every ticket, which is cognitively expensive and inconsistent across engineers. The platform produces a consistent structure (test ID, scenario, steps, expected result, tags, priority) that a junior and a senior both review and improve. Consistency at scale is the larger benefit.

---

**Q: What is the ROI case?**

A: At 60–80 hours saved per sprint across three teams, and 26 sprints per year (2-week sprints):
- Hours saved annually: 1,560–2,080 hr
- At £400/day (8hr day): £78,000–£104,000/year in engineering time
- Platform build + maintenance estimated at £30,000 annually
- **Net annual saving: ~£48,000–£74,000** — not counting the compounding value of earlier defect detection.

---

## Architecture & Design

**Q: Why FastAPI over Flask or Django?**

A: Three technical reasons. (1) **Async-first**: every external call (Jira, GitHub, LLM) is `await`-ed. Flask's sync routes would block per-request; Django async support requires ASGI configuration overhead. FastAPI is async-native. (2) **Pydantic integration**: request/response schemas are Pydantic models. Validation, serialisation, and OpenAPI documentation are automatic. (3) **Developer experience**: auto-generated Swagger UI at `/docs` means the API is self-documenting.

---

**Q: Why not use LangChain or a full agent framework?**

A: The workflow is deterministic: 9 steps, always in the same order, with the same inputs and expected JSON outputs. LangChain adds abstraction and dependency surface area without benefit for a sequential, structured-output pipeline. Direct `AsyncOpenAI` calls with structured JSON prompts are simpler, more debuggable, and faster.

---

**Q: Why five separate LLM prompts instead of one mega-prompt?**

A: Five reasons: (1) **Failure isolation** — if BDD generation fails, test cases are still available. (2) **Prompt optimisation** — each prompt has a distinct system role (QA principal, code reviewer, test architect). (3) **Output shape** — five different JSON schemas in one response requires the LLM to maintain structure coherence across a much larger generation. (4) **Independent tuning** — each step can be improved independently. (5) **Inspectability** — intermediate outputs are visible in the UI, allowing partial results even if later steps fail.

---

**Q: Why is the human review step mandatory and not optional?**

A: Because auto-posting AI content to Jira corrupts the authoritative project record. Sprint velocity is measured from Jira. QA coverage decisions are made from Jira. If the AI posts hallucinated test cases, teams make planning decisions based on false data. The staged review is a correctness gate, not a friction point.

---

**Q: Why are team context files plain Markdown rather than a database or structured config?**

A: Markdown files are editable by non-engineers (QA leads, business analysts) without a UI. They are version-controlled in Git alongside the application, so context changes are auditable. Structured database records would require a migration every time a business rule changes.

---

**Q: How does the platform handle a Jira ticket with no acceptance criteria?**

A: The quality validator scores it low (typically 30–50/100) and generates a specific issue: `severity: "critical", message: "No acceptance criteria defined..."`. The workflow can still generate test cases using the description alone, but the quality gate is explicit.

---

**Q: Why did you build a REST API rather than a standalone CLI tool?**

A: The platform needs to serve both a browser UI and automated systems (GitHub Actions, Jira webhooks) simultaneously. REST makes the workflow reachable from any language or platform. The API enables concurrency: multiple tickets can be processed in parallel by separate callers.

---

**Q: Why did you choose Web UI as the primary mode rather than Jira-native or Slack?**

A: Three reasons: (1) **Review gate** — QA engineers need to read and edit generated content before it posts to Jira. (2) **Adoption curve** — QA teams unfamiliar with AI tools are more comfortable with a browser form. (3) **Iteration speed** — changing the UI is faster than releasing a Jira Forge app update. Jira-native and Slack modes are roadmap items once the team trusts the output quality.

---

## LLM & Prompt Engineering

**Q: What temperature setting is used and why?**

A: `temperature=0.3`. For QA outputs — test IDs, step sequences, JSON schemas — consistency and parsability matter more than novelty. At 0.0, some providers produce slightly less varied test case coverage. At 0.3, outputs vary slightly between runs (reflecting legitimate scenario diversity) while remaining well-structured.

---

**Q: How do you prevent the LLM from ignoring team context?**

A: The `additional_context` is appended to the **user section** of every prompt (not the system section). User-section content has higher instruction-following weight in most RLHF-tuned models. The context block is prefixed with `--- Team Context ---` headings, helping the model identify it as authoritative input.

---

**Q: How does `call_structured()` handle provider differences in JSON mode support?**

A: All currently supported providers support `response_format={"type": "json_object"}` when the system prompt explicitly instructs JSON-only output. For providers that don't support JSON mode (older Ollama models), the `supports_json_mode: false` flag disables the parameter. A multi-tier extraction fallback (direct parse → markdown strip → regex outermost-object) handles remaining inconsistencies.

---

**Q: What happens when the LLM hallucinates a step definition that doesn't match any Gherkin?**

A: Caught at review time. The UI renders both the feature file and step definitions side by side. A QA engineer verifies step text alignment before pushing. Phase 2 will add automated step text extraction and matching to surface misalignments in the UI before push.

---

## Security

**Q: How are credentials secured?**

A: All secrets are loaded exclusively from environment variables via `pydantic.BaseSettings`. They are never written to source code, logged, returned in API responses, or stored in `outputs/`. Pydantic marks sensitive fields with `repr=False` to prevent accidental logging during debug.

---

**Q: Is the Jira API token exposed in generated HTML reports?**

A: No. `report_service.generate_html_report()` receives the `QAResponse` dict which contains only processed results (scores, issues, test cases) — not the raw Jira ticket payload. No authentication context is carried through.

---

**Q: What happens if an attacker submits a malicious Jira ticket ID like `../../etc/passwd`?**

A: The Jira REST API rejects any ID that doesn't match the `PROJECT-NNN` format with a 400 or 404. The app does not use the ticket ID to construct local file paths — artefact paths use `sanitize_filename(jira_id)` which strips all characters except alphanumerics and hyphens.

---

**Q: How is the "Upload to Jira" content sanitised?**

A: The `JiraUploadRequest` body is validated by Pydantic (string fields with max length). Before the Jira comment POST, content is escaped for Atlassian Document Format (ADF). ADF, not HTML, so XSS via Jira's editor is not applicable.

---

**Q: How would you handle Jira Automation webhook authentication if deployed externally?**

A: The `POST /webhooks/jira` endpoint is protected by an HMAC-verified shared secret header (`X-Webhook-Secret`). Jira Automation sends the secret as a custom header. The endpoint validates via `hmac.compare_digest` before processing, preventing unauthenticated callers from triggering expensive LLM workflows.

---

## Scalability & Risk

**Q: What happens if the LLM generates a hallucinated business rule?**

A: Two defences. First, the team context file provides explicit business rules that ground the LLM output. Second, the QA engineer reviews all generated content before upload. The platform does not auto-publish.

---

**Q: What if the LLM provider goes down?**

A: The platform falls back to mock responses, and `LLM_PROVIDER` can be switched to any of 9 supported providers in seconds by changing one environment variable. The workflow is provider-agnostic.

---

**Q: How does this scale to 100 tickets per sprint?**

A: `POST /release-qa` processes a full release in parallel. 100 tickets at the current GitHub Models rate limit (60 RPM) takes approximately 10–15 minutes. An Azure OpenAI deployment with higher rate limits processes the same batch in under 4 minutes.

---

**Q: If the platform serves 10 teams, 500 tickets per sprint — how does the architecture hold?**

A: The API is stateless and async. Each `/run-qa` call is a coroutine; FastAPI handles concurrent requests naturally. Horizontal scaling path: 2–3 API instances behind a load balancer, shard LLM calls across Azure OpenAI deployments in different regions, use `POST /release-qa` with a concurrency limiter.

---

**Q: What is the privacy and data security posture?**

A: Credentials are stored in environment variables, never in application code or API responses. Jira and GitHub tokens are never logged. The LLM provider receives ticket text and commit summaries — no PII should exist in Jira tickets; if it does, that is a pre-existing data hygiene issue, not introduced by this platform.

---

**Q: Can this be used across other business units?**

A: Yes. New teams are onboarded by creating a single Markdown context file with no code changes. The workflow, UI, and LLM prompts are generic by design; team context files provide the domain specificity. An Investment Banking or Retail Banking team could be onboarded in under an hour.

---

## Testing & Reliability

**Q: How is the platform itself tested?**

A: Three levels: (1) **Unit tests** — each service method tested with mocked httpx/LLM responses. (2) **Integration tests** — full 9-step workflow against real Jira/GitHub using test ticket CRFLT-1. (3) **Contract tests** — Pydantic schema validation confirms LLM mock responses match the expected `QAResponse` shape.

---

**Q: How do you handle Jira API downtime?**

A: `jira_service.get_ticket()` has a configurable timeout (default 30s). On timeout or non-2xx response, it raises `JiraServiceError`. The workflow catches this at Step 1 and returns a `QAResponse` with `error: "Jira fetch failed: <message>"`. The UI renders the error instead of a crash.

---

## Execution Models

**Q: What would it take to add a Slack bot trigger?**

A: ~40–60 lines of code. The Slack bolt app receives a slash command, extracts `jira_id`, calls `POST /api/v1/run-qa` via `httpx`, and posts `grade + score + report_url` back to the channel thread. The entire QA workflow logic is unchanged.

---

**Q: How do you prevent automated runs from spamming Jira with duplicate comments?**

A: Two mechanisms. First, `post_to_jira` defaults to `false` — callers must explicitly opt in. Second, the run history tracks `run_id` per `jira_id`; deduplication checks prevent double-commenting within a short window.

---

**Q: In GitHub Actions, the server starts cold on every run. How do you mitigate startup latency?**

A: Three mitigations: (1) The workflow polls `/health` before calling the API. (2) Dependencies are cached via `actions/setup-python`. (3) For latency-sensitive use cases, the platform can be deployed as a persistent service and the Actions workflow points to the external URL.

---

## Career & Growth Context

**Q: What was the most instructive mistake during this build?**

A: Generating plain pytest functions before auditing the target repo's framework. The first implementation assumed "pytest + Playwright = standard pytest functions". When the repo used pytest-bdd, the output was structurally incompatible. Fixing it required rewriting prompts, mock responses, and file writers. The lesson: always read the target repo's existing files before writing a code generator for it.

---

**Q: If you were advising another engineer building a similar AI workflow, what would you tell them?**

A: Five things: (1) Separate prompts for separate concerns. (2) Always validate LLM output against a Pydantic schema. (3) Keep the human review gate mandatory. (4) Build mock mode first — makes unit tests fast and deterministic. (5) Store team context in editable flat files, not code.

---

**Q: What would you add with two more weeks?**

A: In priority order: (1) PostgreSQL persistence for quality trend dashboards. (2) GitHub Actions trigger on PR open. (3) Duplicate step detection before push. (4) Step execution loop — trigger test run, pull results. (5) MCP server for AI agent composability.

---

## One-Line Summary

> "We built an API-first agentic QA platform using FastAPI and direct LLM integration, exposed it via a review-first Web UI for daily QA use, wired it to Jira Automation webhooks and GitHub Actions for CI/CD — with the architecture designed so that new triggers (Slack, cron, Forge app) can be added as thin layers without changing any workflow logic."
