# config/

Runtime configuration files loaded by the platform at request time.

## Directories

| Directory | Purpose |
|-----------|---------|
| `teams/` | Per-team Markdown context files injected into every LLM prompt |
| `jira/` | CRFLT project metadata, filters, and dashboard reference |

## How Team Context Works

`workflow_service._load_team_context(team_id)` reads `teams/{team_id}.md` and appends it to the user section of every LLM prompt. This turns generic AI output into domain-specific output — real fixtures, real paths, real business rules.

**To add a new team:** create `teams/<team_id>.md` with project key, Jira fields, GitHub repos, business rules, and test environment URLs. No code changes required.

See [docs/05-team-onboarding.md](../docs/05-team-onboarding.md) for the full onboarding guide.
