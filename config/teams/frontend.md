# Frontend Team — QA Configuration

## Team Overview

| Field              | Value                                                        |
|--------------------|--------------------------------------------------------------|
| **Team Name**      | Frontend                                                     |
| **Jira Project**   | SCRUM                                                        |
| **Jira Dashboard** | https://shrikantpatil.atlassian.net/jira/software/projects/SCRUM/boards |
| **Primary App**    | SauceDemo UI (https://www.saucedemo.com)                    |
| **App GitHub**     | https://github.com/shrikantkingdom/sow_ui                    |
| **Automation Repo**| https://github.com/shrikantkingdom/playwright_project        |
| **Tech Stack**     | React, TypeScript, Playwright, pytest                        |

## Application Architecture

- Single-page React application
- REST API backend (FastAPI)
- JWT-based authentication
- State management: React Context + Zustand
- Browser support: Chrome, Firefox, Safari (latest 2 versions)

## QA Focus Areas

1. **Cross-browser compatibility** — all critical flows must pass on Chrome + Firefox
2. **Responsive design** — test at 375px (mobile), 768px (tablet), 1280px (desktop) breakpoints
3. **Authentication flows** — login, logout, session expiry, OAuth callbacks
4. **Form validation** — client-side and server-side error messages
5. **Accessibility** — ARIA labels, keyboard navigation, contrast ratios

## Automation Conventions

- Tests in `playwright_project/tests/ui/`
- Page Objects in `playwright_project/pages/`
- Use `authenticated_page` fixture for tests that require login
- Use `page` fixture + `LoginPage` for authentication tests
- Screenshot on failure is automatic (via `conftest.py`)
- Traces saved to `reports/traces/`

## Custom QA Instructions

When generating test cases for this team:
- Always include mobile viewport tests for UI features
- Flag any test that requires real OAuth credentials (these run in CI only)
- Prioritise smoke tests that can run in under 2 minutes
- Use `config.sauce_username` and `config.sauce_password` for SauceDemo credentials

## Environment URLs

| Environment | URL                              |
|-------------|----------------------------------|
| QA          | https://www.saucedemo.com        |
| Staging     | https://staging.saucedemo.com    |
| Production  | https://www.saucedemo.com        |
