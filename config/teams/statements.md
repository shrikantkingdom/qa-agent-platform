# Team: Statements
## Business Unit: Client Reporting — Wealth Management

---

## Overview

The Statements team owns the end-to-end lifecycle of periodic account statements delivered to wealth
management clients — monthly, quarterly, ad-hoc, and tax statements — in PDF, email, and portal
formats. Data flows from core banking through a Kafka pipeline into the statement engine, with results
archived in S3 and surfaced via the React portal.

---

## Key Links

| Resource | URL |
|----------|-----|
| **Jira Board** | https://shrikantpatil.atlassian.net/jira/software/projects/SCRUM/boards/1 |
| **Confluence** | https://shrikantpatil.atlassian.net/wiki/spaces/STMT |
| **Services Repo** | https://github.com/shrikantkingdom/statements |
| **UI App Repo** | https://github.com/shrikantkingdom/sow_ui |
| **Automation Repo** | https://github.com/shrikantkingdom/playwright_project |

---

## Jira Configuration

- **Project Key**: `SCRUM`
- **Board URL**: https://shrikantpatil.atlassian.net/jira/software/projects/SCRUM/boards/1

### Custom Fields

| Field Name | Values |
|------------|--------|
| Statement Type | Monthly / Quarterly / Ad-hoc / Tax |
| Delivery Channel | Email / Portal / Print / All |
| Account Type | Individual / Joint / Corporate / Trust |
| Regulatory Flag | Yes / No |
| Risk Level | Low / Medium / High / Critical |
| Batch Job Impact | Yes / No |

### Labels
`statements`, `regulatory`, `pdf-generation`, `batch`

---

## Architecture

### Backend Stack
- **Runtime**: Java 17 + Spring Boot 3.x
- **Messaging**: Apache Kafka (account data events)
- **Database**: PostgreSQL (statement metadata, delivery status)
- **Storage**: AWS S3 (generated PDFs, archival)
- **PDF Engine**: iText / Apache FOP

### Frontend Stack
- **Framework**: React 18 + TypeScript
- **State**: Redux Toolkit
- **Client Portal**: Statement viewer, download, filter by date range and account

### Microservices
| Service | Responsibility |
|---------|---------------|
| `statement-generator` | PDF rendering, iText engine |
| `statement-scheduler` | Cron/Quartz job scheduling, batch orchestration |
| `statement-delivery` | Email dispatch, portal upload, print queue |
| `statement-archive` | S3 storage, retention enforcement |
| `account-data-service` | Account feed from core banking via Kafka |

---

## Business Rules (CRITICAL for test coverage)

1. **PDF date range inclusivity** — Period must include first and last day of range. Off-by-one bugs are historically recurring; always test boundary dates.
2. **Zero-transaction statements** — A period with no activity must generate a "no activity" statement, NOT an error or a skipped record.
3. **Tax statement column order** — Column order in tax statements is legally mandated. Any column reordering requires regulatory sign-off. Do not auto-generate reordering changes.
4. **Batch idempotency** — Re-running a batch job must not create duplicate statements. Test that re-runs produce identical output, not additional records.
5. **Archival retention — 7 years** — Statements are soft-deleted only. Hard deletion is a compliance violation. Flag and reject any code that hard-deletes statements.
6. **PDF vs portal consistency** — The PDF download and portal view must be byte-for-byte content-identical. Visual formatting differences acceptable; data differences are not.
7. **Email delivery failure tolerance** — If email delivery fails, the statement must still appear on the portal. The batch job is NOT marked as failed for email delivery failures.

---

## Automation Structure (playwright_project)

```
playwright_project/
├── features/
│   └── statements/          ← Gherkin feature files for statements
│       ├── statement_generation.feature
│       ├── statement_delivery.feature
│       ├── statement_archive.feature
│       └── batch_processing.feature
├── tests/
│   └── step_defs/
│       └── statements/      ← pytest-bdd step definition files
│           ├── test_statement_generation_steps.py
│           ├── test_statement_delivery_steps.py
│           └── test_batch_processing_steps.py
├── pages/
│   └── statements/          ← Page Object classes
│       ├── statements_page.py
│       ├── statement_viewer_page.py
│       └── statement_filter_page.py
└── test-data/
    └── statements/          ← Test data fixtures and factories
        ├── account_fixtures.py
        └── statement_payloads.py
```

### Step Definition Conventions
- **Language**: Python (pytest-bdd)
- **Naming**: `snake_case` — `test_statement_generation_steps.py`
- **Tags**: `@statements`, `@smoke`, `@regression`, `@pdf`, `@batch`
- **Feature file path**: `features/statements/<feature_name>.feature`
- **Step def path**: `tests/step_defs/statements/test_<feature_name>_steps.py`

### Key Reusable Steps
```
Given a statement run is triggered for account {account_id} for period {start_date} to {end_date}
When the statement-generator service processes the job
Then a PDF statement should be generated with {page_count} pages
And the statement should be available on the portal
And the statement PDF should match the portal view content
Given an account with no transactions in the statement period
Then a "no activity" statement should be generated
Given a batch job has already completed for period {period}
When the batch job is re-run
Then no duplicate statements should be created
```

---

## Test Environments

| Environment | Base URL |
|-------------|----------|
| Development | https://dev.statements.internal |
| QA | https://qa.statements.internal |
| UAT | https://uat.statements.internal |

---

## Team Contacts

| Role | Responsibility |
|------|----------------|
| QA Lead | Functional + regression test ownership |
| Compliance Liaison | Sign-off on regulatory test cases (tax statements, archival) |
| Batch Operations | Batch job scheduling, environment resets for test runs |

---

## Glossary

| Term | Definition |
|------|------------|
| Ad-hoc Statement | On-demand statement generated outside the scheduled batch window |
| Tax Statement | Year-end/period-end statement with regulatory-mandated format |
| Soft Delete | Marking a record as deleted without removing from DB — required for 7-year retention |
| Idempotency Key | Unique identifier preventing duplicate statement creation on batch re-run |
| Portal View | Rendered HTML view of the statement in the client-facing web portal |
