# Team Context Files

Each `.md` file in this directory is a team-specific context block loaded at runtime and injected into every LLM prompt.

## Current Teams

| File | Team | Component |
|------|------|-----------|
| `global.md` | Default fallback | — |
| `statements.md` | Statements | CR-statements |
| `confirms.md` | Confirms | CR-confirms |
| `letters.md` | Client Correspondence | CR-letters |
| `mobile.md` | Mobile (cross-team) | — |

## File Format

Each file is free-form Markdown containing:
- Jira project key and board URL
- GitHub repo URLs
- Custom field names and valid values
- Automation directory structure
- pytest-bdd tags and feature file paths
- Business rules with compliance criticality
- Test environment URLs

## Adding a New Team

1. Copy an existing file: `cp statements.md newteam.md`
2. Edit the context to match the new team's domain
3. Restart the server (context is loaded per-request, but a restart ensures clean state)
4. Use `team_id=newteam` in API calls or the UI dropdown

No code changes required.
