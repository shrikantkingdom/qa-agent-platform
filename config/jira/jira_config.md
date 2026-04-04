# Jira Configuration — CRFLT (Client Reporting)

## Project Structure

All three Client Reporting teams (**Statements**, **Confirms**, **Letters**) share a single Jira project:

| Field | Value |
|-------|-------|
| **Project Key** | `CRFLT` |
| **Project Name** | Client Reporting |
| **Project URL** | https://shrikantpatil.atlassian.net/jira/software/c/projects/CRFLT |
| **Project Type** | Scrum / Kanban (team-level boards) |
| **Single project?** | Yes — do NOT create separate projects per team |

---

## Component-Based Team Segregation

Teams are separated inside the shared project using **Jira Components**. Every issue must have its team component set before creation.

| Team | Component Name | Board Filter |
|------|---------------|--------------|
| Statements | `CR-statements` | `project = CRFLT AND component = "CR-statements"` |
| Confirms | `CR-confirms` | `project = CRFLT AND component = "CR-confirms"` |
| Letters | `CR-letters` | `project = CRFLT AND component = "CR-letters"` |

### Why Components?

- One Jira project = one set of workflows, permissions, and notification schemes — less admin overhead.
- Components allow each team to have its own Kanban/Scrum board by simply filtering on the component.
- Cross-team dependency links work natively (no cross-project linking needed).
- The shared QA dashboard can aggregate metrics across all three teams in a single view.

---

## Component Setup in Jira UI

1. Open **CRFLT** project → **Project settings** (bottom-left gear icon)
2. Click **Components** in the left sidebar
3. Add each component:
   - **Name**: `CR-statements` | **Lead**: Statements QA Lead | **Default Assignee**: Project default
   - **Name**: `CR-confirms` | **Lead**: Confirms QA Lead
   - **Name**: `CR-letters` | **Lead**: Letters QA Lead
4. Click **Save** after each entry

---

## Kanban Boards (Live)

Three Kanban boards are provisioned via the Jira Agile API and scoped to their respective
team component. Each board uses a saved JQL filter as its data source.

| Team | Board Name | Board ID | Board URL |
|------|-----------|----------|-----------|
| Statements | Statements | 37 | https://shrikantpatil.atlassian.net/jira/software/c/projects/CRFLT/boards/37 |
| Confirms | Confirms | 38 | https://shrikantpatil.atlassian.net/jira/software/c/projects/CRFLT/boards/38 |
| Letters | Letters | 39 | https://shrikantpatil.atlassian.net/jira/software/c/projects/CRFLT/boards/39 |

**Board filter JQLs:**

```sql
-- Statements Board (filter 10033)
project = CRFLT AND component = "CR-statements" ORDER BY created DESC

-- Confirms Board (filter 10034)
project = CRFLT AND component = "CR-confirms" ORDER BY created DESC

-- Letters Board (filter 10035)
project = CRFLT AND component = "CR-letters" ORDER BY created DESC
```

> All JQL filters are also stored in `config/jira/jira_filters.json`.

---

## Code Integration — Automatic Component Assignment

The `jira_service.py` service handles component assignment automatically.
Team names are mapped to components via `TEAM_COMPONENT_MAP`:

```python
TEAM_COMPONENT_MAP = {
    "statements": "CR-statements",
    "confirms":   "CR-confirms",
    "letters":    "CR-letters",
}
```

### Creating an Issue Programmatically

```python
from app.services.jira_service import JiraService

service = JiraService()

# Component is injected automatically based on team_name
issue_key = await service.create_issue(
    team_name="statements",
    summary="[API] Statement generation REST endpoint v2",
    description="New v2 API for statement generation...",
    issue_type="Story",
    priority="High",
    labels=["statements", "api"],
)
# Returns "CRFLT-42" (or None on failure)
```

### Validation

Passing an invalid team name raises `ValueError` immediately:

```python
await service.create_issue(team_name="payments", ...)
# ValueError: Invalid team 'payments'. Valid teams: ['confirms', 'letters', 'statements']
```

### Adding a New Team

1. Add an entry to `TEAM_COMPONENT_MAP` in `jira_service.py`
2. Add the component in Jira UI (see above)
3. Create a new board with the corresponding JQL filter
4. Add the filter entry to `config/jira/jira_filters.json`

---

## Dashboard Overview

A unified **CRFLT QA Dashboard** covers all three teams. The dashboard uses saved Jira filters as widget data sources.

| Widget | JQL | Widget Type |
|--------|-----|------------|
| All Work | `project = CRFLT ORDER BY created DESC` | Issue Statistics |
| Bugs Overview | `project = CRFLT AND issuetype = Bug ORDER BY priority DESC` | Issue Statistics |
| High Priority | `project = CRFLT AND priority in (High, Highest)` | Issue Statistics |
| Active Sprint | `project = CRFLT AND sprint in openSprints()` | Sprint Health Gadget |
| Statements Issues | `project = CRFLT AND component = "CR-statements"` | Two Dimensional Filter Stats |
| Confirms Issues | `project = CRFLT AND component = "CR-confirms"` | Two Dimensional Filter Stats |
| Letters Issues | `project = CRFLT AND component = "CR-letters"` | Two Dimensional Filter Stats |
| In Progress | `project = CRFLT AND status = "In Progress"` | Issue Statistics |

See `dashboard_guide.md` for step-by-step instructions to build this dashboard in the Jira UI.

---

## QA Automation Integration

All three teams share one automation repo:

| Resource | URL |
|----------|-----|
| QA Automation (Playwright) | https://github.com/shrikantkingdom/playwright_project |

Each team has a dedicated suite folder inside that repo:

```
playwright_project/
├── features/
│   ├── statements/     ← Gherkin feature files
│   ├── confirms/
│   └── letters/
├── tests/
│   └── step_defs/
│       ├── statements/
│       ├── confirms/
│       └── letters/
└── pages/
    ├── statements/
    ├── confirms/
    └── letters/
```

The `team_id` parameter in the QA Agent workflow selects which team's suite to run and which Jira component to use when uploading results.

---

## GitHub Repositories per Team

| Team | Backend Services | Database / Stored Procs | UI Application |
|------|-----------------|------------------------|----------------|
| Statements | `shrikantkingdom/statements` | `shrikantkingdom/statements-db` | `shrikantkingdom/statements-ui` |
| Confirms | `shrikantkingdom/confirms` | `shrikantkingdom/confirms-db` | `shrikantkingdom/confirms-ui` |
| Letters | `shrikantkingdom/client-correspondence` | `shrikantkingdom/correspondence-db` | `shrikantkingdom/correspondence-ui` |
