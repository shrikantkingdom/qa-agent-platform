# 05 — Team Onboarding

Add a new team to the QA Agent Platform in 30 minutes. No code changes required.

---

## How Team Context Works

Every LLM prompt is injected with a team-specific context block loaded from `config/teams/<team_id>.md`. This transforms generic AI output into domain-specific output:

**Without team context:**
> "Test that the form validates required fields and handles edge cases."

**With Statements team context:**
> "Test PDF date range inclusivity (off-by-one is historically recurring). Test zero-transaction period generates 'no activity' statement, not error. Verify 7-year soft-delete retention (hard delete is compliance violation)."

## Step 1 — Create the Context File

```bash
cp config/teams/statements.md config/teams/newteam.md
```

## Step 2 — Fill in Team Details

Edit `config/teams/newteam.md` with the following sections:

### Required Sections

```markdown
# New Team — QA Context

## Jira Configuration
- **Project Key**: CRFLT
- **Board**: https://your-org.atlassian.net/jira/software/c/projects/CRFLT/boards/40
- **Component**: CR-newteam
- **Sprint**: CRFLT Sprint 1

## GitHub Repositories
- **Service repo**: your-org/newteam-service
- **UI repo**: your-org/newteam-ui
- **Automation repo**: your-org/playwright_project

## Business Rules
1. Rule one — description and compliance criticality
2. Rule two — what must always be tested
3. Rule three — known edge cases

## Test Environment
- **Base URL**: https://staging.your-app.com/newteam
- **Test accounts**: user1@test.com / password123

## pytest-bdd Conventions
- Feature files: `features/newteam/`
- Step defs: `tests/step_defs/newteam/`
- Tags: `@newteam`, `@smoke`, `@regression`
```

### Optional Sections

- Custom Jira field names and valid values
- Automation directory structure
- Known flaky tests to exclude
- Regulatory requirements (GDPR, MiFID II, etc.)

## Step 3 — Map Component to Team

If using Jira Automation webhooks, add the component mapping in `app/api/routes.py`:

```python
_COMPONENT_TEAM_MAP: dict = {
    "cr-statements": "statements",
    "cr-confirms": "confirms",
    "cr-letters": "letters",
    "cr-newteam": "newteam",          # ← add this line
}
```

## Step 4 — Test

```bash
curl -X POST http://localhost:8000/api/v1/run-qa \
  -H "Content-Type: application/json" \
  -d '{"jira_id": "CRFLT-14", "team_id": "newteam"}'
```

Check that the generated test cases reference your team's business rules, environment URLs, and automation conventions.

## Step 5 — Add to Jira Board (Optional)

If the new team has its own Jira board, add it to `_CRFLT_BOARDS` in `routes.py` so the UI dropdown includes it.

## Current Teams

| Team ID | Component | Board | Context File |
|---------|-----------|-------|-------------|
| `statements` | CR-statements | Board 37 | `config/teams/statements.md` |
| `confirms` | CR-confirms | Board 38 | `config/teams/confirms.md` |
| `letters` | CR-letters | Board 39 | `config/teams/letters.md` |
| `mobile` | — | — | `config/teams/mobile.md` |

## Tips

- **Be specific** — vague rules like "test security" produce vague tests. Write "test that non-admin users receive HTTP 403 when accessing /admin endpoints"
- **Include real paths** — the LLM uses file paths verbatim in generated step definitions
- **Version control** — team context files are Git-tracked, so changes are auditable
- **No restart needed** — context is loaded per-request, so edits take effect immediately
