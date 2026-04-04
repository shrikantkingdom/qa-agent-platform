# Team: Letters (Client Correspondence)
## Business Unit: Client Reporting — Wealth Management

---

## Overview

The Letters team (formally: Client Correspondence Platform) owns the generation and delivery of all
non-transactional client communications — welcome letters, regulatory notices, marketing materials,
and compliance-driven correspondence. The platform handles template management, personalisation,
suppression (GDPR and preference-based), bulk broadcast throttling, audit trail, and multi-channel
delivery (email, postal, portal, SMS).

GDPR compliance is the highest-risk area for this team. Any suppression bypass, incorrect opt-out
handling, or audit trail mutation is a critical compliance violation.

---

## Key Links

| Resource | URL |
|----------|-----|
| **Jira Board** | https://shrikantpatil.atlassian.net/jira/software/projects/CORCX/boards/1 |
| **Confluence** | https://shrikantpatil.atlassian.net/wiki/spaces/CORCX |
| **Services Repo** | https://github.com/shrikantkingdom/client-correspondence |
| **UI App Repo** | https://github.com/shrikantkingdom/correspondence-ui |
| **Template Repo** | https://github.com/shrikantkingdom/correspondence-templates |
| **Automation Repo** | https://github.com/shrikantkingdom/playwright_project |

---

## Jira Configuration

- **Project Key**: `CORCX`
- **Board URL**: https://shrikantpatil.atlassian.net/jira/software/projects/CORCX/boards/1

### Custom Fields

| Field Name | Values |
|------------|--------|
| Correspondence Type | Welcome / Regulatory Notice / Marketing / Opt-out Confirmation / Ad-hoc |
| Delivery Channel | Email / Postal / Portal / SMS / All |
| Regulatory Scope | GDPR / FCA / PSD2 / None |
| Bulk Broadcast | Yes / No |
| Template Change | Yes / No |
| Risk Level | Low / Medium / High / Critical |
| Audit Impact | Yes / No |

### Labels
`correspondence`, `regulatory`, `template`, `bulk`, `suppression`, `audit`

### Special Reviewers
All tickets with `Regulatory Scope = GDPR` or `Audit Impact = Yes` require **`@compliance-team`** review before closure.

---

## Architecture

### Backend Stack
- **Runtime**: Java 17 + Spring Boot 3.x
- **Messaging**: Apache Kafka (correspondence trigger events)
- **Database**: PostgreSQL (correspondence records, suppression list, audit trail)
- **Storage**: AWS S3 (rendered PDFs, bulk export archives)
- **Print Vendor API**: Async callback-based print dispatch; `printvendor-sandbox.internal` for testing

### Frontend Stack
- **Framework**: React 18 + TypeScript
- **State**: Redux Toolkit
- **Operations UI**: Template management, suppression list management, bulk job monitoring, correspondence search

### Microservices
| Service | Responsibility |
|---------|---------------|
| `correspondence-generator` | Letter rendering, template binding, PDF output |
| `personalisation-engine` | Client data merge, null-safety fallbacks, locale handling |
| `correspondence-delivery` | Multi-channel dispatch (email, postal queue, portal, SMS) |
| `template-management` | Template versioning, lock enforcement, approval workflow |
| `suppression-service` | GDPR and preference suppression lookup, absolute rule enforcement |
| `audit-trail` | INSERT-only event log; every correspondence lifecycle event recorded |
| `client-profile-service` | Client contact data, opt-out preferences, delivery preferences |

---

## Business Rules (CRITICAL for test coverage)

1. **GDPR suppression is absolute** — No correspondence of ANY type (including regulatory notices) must be sent to a GDPR-suppressed client. Only court-ordered bypasses are permitted. This is the HIGHEST compliance risk. Test that suppressed clients receive nothing, and that re-running the job does not change this.
2. **Template versioning lock** — A template that is in use (has been sent to at least one client) must NEVER be modified in-place. All changes must create a new version. Test that the system rejects in-place modification of a locked template.
3. **Postal queue cut-off** — Daily postal queue cut-off is **3pm GMT**. Letters submitted after cut-off are queued for the next business day. SLA-sensitive tests must account for this; use mocked time in automated tests.
4. **Personalisation null safety** — If any personalisation field is null, the fallback must always be `"Valued Client"`. A rendered letter must never contain the literal string `null` or an empty personalisation slot.
5. **Bulk broadcast throttling** — Broadcasts exceeding 10,000 clients must be throttled to a maximum of 1,000 dispatches per minute. Test that the throttle is respected and that the job completes fully within the expected time window.
6. **Audit trail immutability** — The audit trail schema uses INSERT-only semantics. No UPDATE or DELETE operations are permitted on audit records. Any code that adds UPDATE/DELETE to audit tables must be flagged and rejected in code review.
7. **Duplicate dispatch prevention** — The same correspondence type for the same client on the same date must only be dispatched once within a 24-hour window. Test the idempotency key mechanism to confirm re-triggers do not result in duplicate sends.
8. **Opt-out confirmation** — When a client opts out of marketing, a confirmation letter MUST be sent via their registered email — even if marketing email is suppressed. This is a legal requirement under FCA rules.
9. **HTML vs PDF consistency** — The HTML portal view and PDF download must contain identical content. Visual/formatting differences are acceptable; content differences (different data, missing sections) are not.

---

## Automation Structure (playwright_project)

```
playwright_project/
├── features/
│   └── correspondence/      ← Gherkin feature files for correspondence
│       ├── letter_generation.feature
│       ├── suppression_rules.feature
│       ├── template_management.feature
│       ├── bulk_broadcast.feature
│       ├── delivery_channels.feature
│       └── audit_trail.feature
├── tests/
│   └── step_defs/
│       └── correspondence/  ← pytest-bdd step definition files
│           ├── test_letter_generation_steps.py
│           ├── test_suppression_rules_steps.py
│           ├── test_template_management_steps.py
│           ├── test_bulk_broadcast_steps.py
│           └── test_audit_trail_steps.py
├── pages/
│   └── correspondence/      ← Page Object classes
│       ├── correspondence_dashboard_page.py
│       ├── template_management_page.py
│       ├── suppression_management_page.py
│       └── bulk_job_monitor_page.py
└── test-data/
    └── correspondence/      ← Test data fixtures and factories
        ├── client_fixtures.py
        ├── template_fixtures.py
        └── suppression_fixtures.py
```

### Step Definition Conventions
- **Language**: Python (pytest-bdd)
- **Naming**: `snake_case` — `test_letter_generation_steps.py`
- **Tags**: `@correspondence`, `@smoke`, `@regression`, `@template`, `@bulk`, `@suppression`, `@gdpr`
- **Feature file path**: `features/correspondence/<feature_name>.feature`
- **Step def path**: `tests/step_defs/correspondence/test_<feature_name>_steps.py`

### Key Reusable Steps
```
Given a client {client_id} has GDPR suppression active
When a {correspondence_type} letter is triggered for client {client_id}
Then no correspondence should be dispatched to the client
Given a template {template_id} has been used in a live run
When an attempt is made to modify the template in-place
Then the system should reject the modification with a versioning error
Given a null personalisation field for client {client_id}
When the personalisation-engine processes the letter
Then the rendered letter should contain "Valued Client" and not "null"
Given a bulk broadcast for {client_count} clients
When the job is dispatched
Then the dispatch rate should not exceed 1000 per minute
```

---

## Test Environments

| Environment | Base URL |
|-------------|----------|
| Development | https://dev.correspondence.internal |
| QA | https://qa.correspondence.internal |
| UAT | https://uat.correspondence.internal |
| Print Vendor Sandbox | https://printvendor-sandbox.internal |

---

## Team Contacts

| Role | Responsibility |
|------|----------------|
| QA Lead | Functional + regression test ownership |
| Compliance Team | Sign-off on GDPR / FCA / suppression test scenarios |
| Template Designer | Template versioning, approval workflow |
| Print Vendor Integration Lead | Print dispatch SLA, callback handling |

---

## Glossary

| Term | Definition |
|------|------------|
| GDPR Suppression | Absolute prohibition on all correspondence for a suppressed client — highest compliance risk |
| Template Versioning Lock | Prevents in-place modification of templates that have been used in live correspondence |
| Personalisation | Merging client-specific data (name, account, locale) into a template |
| Bulk Broadcast | A single correspondence campaign sent to >1,000 clients |
| Throttle | Rate-limiting mechanism capping bulk dispatch at 1,000/min for large audiences |
| Opt-out Confirmation | System-generated email confirming marketing opt-out — legally mandated even for suppressed clients |
| Audit Trail | INSERT-only event log capturing every correspondence lifecycle event (immutable) |
| Idempotency Key | Unique identifier preventing duplicate dispatch of the same correspondence within 24 hours |
| Postal Cut-off | 3pm GMT daily — letters submitted after this time are queued for next business day |
