# Backend Team — QA Configuration

## Team Overview

| Field              | Value                                                        |
|--------------------|--------------------------------------------------------------|
| **Team Name**      | Backend                                                      |
| **Jira Project**   | SCRUM                                                        |
| **Jira Dashboard** | https://shrikantpatil.atlassian.net/jira/software/projects/SCRUM/boards |
| **Primary App**    | REST API (FastAPI + PostgreSQL)                               |
| **App GitHub**     | https://github.com/shrikantkingdom/sow_ui                    |
| **Automation Repo**| https://github.com/shrikantkingdom/playwright_project        |
| **Tech Stack**     | Python, FastAPI, PostgreSQL, Redis, Docker                   |

## Application Architecture

- FastAPI REST API (async, Python 3.12)
- PostgreSQL (primary database)
- Redis (session cache, rate limiting)
- JWT + OAuth2 authentication
- Docker Compose for local development
- GitHub Actions CI/CD pipeline

## QA Focus Areas

1. **API contract compliance** — all responses must match OpenAPI schema
2. **Authentication & authorisation** — JWT validation, role-based access, token expiry
3. **Data integrity** — CRUD operations, constraint violations, concurrent writes
4. **Performance** — P95 response time ≤ 500ms for read endpoints
5. **Error handling** — standardised error responses (RFC 9457), no stack traces in production

## Automation Conventions

- API tests in `playwright_project/tests/api/`
- Use `api_client` fixture for all HTTP calls (session-scoped)
- Use `schema_validator` from `utils/schema_validator.py` to validate response bodies
- Tag performance tests with `@pytest.mark.performance`
- All API tests must clean up created data in teardown

## Custom QA Instructions

When generating test cases for this team:
- Include schema validation assertions for every response
- Always test both authenticated and unauthenticated variants of protected endpoints
- Include rate limiting / throttling tests for public endpoints
- Test pagination (first page, last page, empty page, out-of-bounds page)
- Ensure CORS headers are correct on all cross-origin endpoints

## Environment Config

| Variable         | Default Value                             |
|------------------|-------------------------------------------|
| API_BASE_URL     | https://jsonplaceholder.typicode.com      |
| API_MAX_RESPONSE | 2000ms                                    |
| AUTH_HEADER      | Authorization: Bearer <token>             |
