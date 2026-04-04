# Team: Confirms (Trade Confirmations)
## Business Unit: Client Reporting — Wealth Management

---

## Overview

The Confirms team owns the generation and delivery of legally-binding trade confirmation documents
for all executed trades across equities, fixed income, derivatives, and FX. Confirms must meet
MiFID II T+1 SLA for equities, support SWIFT MT515/MT518 formats, and handle exception escalation
for unmatched trades. Regulatory reporting to EMIR and MiFID II is also within scope.

---

## Key Links

| Resource | URL |
|----------|-----|
| **Jira Board** | https://shrikantpatil.atlassian.net/jira/software/projects/SCRUM/boards/35 |
| **Confluence** | https://shrikantpatil.atlassian.net/wiki/spaces/CONF |
| **Backend Services Repo** | https://github.com/shrikantkingdom/confirms |
| **Database / Stored Procedures Repo** | https://github.com/shrikantkingdom/confirms-db |
| **UI Application Repo** | https://github.com/shrikantkingdom/confirms-ui |
| **QA Automation Repo (Playwright)** | https://github.com/shrikantkingdom/playwright_project |

---

## Jira Configuration

- **Project Key**: `SCRUM` (Client Reporting)
- **Component**: `CR-confirms`
- **Board URL**: https://shrikantpatil.atlassian.net/jira/software/projects/SCRUM/boards/35
- **Board Filter JQL**: `project = SCRUM AND component = "CR-confirms" ORDER BY created DESC`

### Custom Fields

| Field Name | Values |
|------------|--------|
| Instrument Type | Equity / Fixed Income / Derivative / FX / All |
| Delivery Channel | SWIFT / Email / Portal / FTP / All |
| Regulatory Scope | MiFID II / EMIR / Dodd-Frank / None |
| Risk Level | Low / Medium / High / Critical |
| Exception Impact | Low / Medium / High / Critical |
| STP Flag | Yes / No |

### Labels
`confirms`, `regulatory`, `swift`, `matching`, `exception`

---

## Architecture

### Backend Stack
- **Runtime**: Java 17 + Spring Boot 3.x
- **Messaging**: Apache Kafka (trade event stream)
- **Database**: PostgreSQL (confirms metadata), Oracle (trade data, legacy integration)
- **SWIFT**: HSM-managed credentials; SWIFT Alliance Gateway integration
- **External**: SWIFT Sandbox at `swift-sandbox.internal`

### Frontend Stack
- **Framework**: React 18 + TypeScript
- **State**: Redux Toolkit
- **Operations UI**: Exception management, confirms tracking, manual override

### Microservices
| Service | Responsibility |
|---------|---------------|
| `confirms-generator` | Document rendering for all instruments |
| `confirms-matching` | Trade vs confirm matching engine, tolerance checks |
| `confirms-delivery` | SWIFT dispatch, email, portal, FTP |
| `confirms-exceptions` | Exception queue management, escalation timers |
| `trade-data-service` | Trade event ingestion from Kafka |
| `regulatory-reporter` | EMIR / MiFID II reporting, idempotent submission |

---

## Business Rules (CRITICAL for test coverage)

1. **MiFID II T+1 SLA** — Equity confirms must be delivered by end of T+1 business day. Always test against late-arriving trade events (e.g., trade booked at 23:58 on T).
2. **SWIFT format validation** — MT515 (equities) and MT518 (repo) — a single field exceeding its length limit fails silently. Always test message format, not just happy-path delivery.
3. **Price matching tolerance** — Tolerance is ±0.0001 and is configurable per instrument class. Never hardcode the tolerance value in tests — read from config.
4. **Exception escalation timer** — Unmatched trades must escalate to the exception queue after >4 hours. Timezone edge cases (DST transitions, UTC vs local time) have historically broken this timer.
5. **Regulatory idempotency** — EMIR and MiFID II reports must not be re-submitted on service restart or batch re-run. Test that restart-after-partial-submission does not create duplicates.
6. **Cancelled trade handling** — A cancelled trade must suppress the original confirm AND generate a cancellation notice via all original delivery channels.
7. **FX rounding** — Amounts must be rounded to the currency standard (JPY = 0 decimals, USD = 2 decimals, etc.). Incorrect rounding is a source of counterparty disputes.
8. **BIC validation** — Counterparty BIC must be validated against the internal reference data store BEFORE SWIFT dispatch. Invalid BICs must route to the exception queue, not cause a failed delivery.

---

## Automation Structure (playwright_project)

```
playwright_project/
├── features/
│   └── confirms/            ← Gherkin feature files for confirms
│       ├── confirm_generation.feature
│       ├── swift_delivery.feature
│       ├── trade_matching.feature
│       ├── exception_handling.feature
│       └── regulatory_reporting.feature
├── tests/
│   └── step_defs/
│       └── confirms/        ← pytest-bdd step definition files
│           ├── test_confirm_generation_steps.py
│           ├── test_swift_delivery_steps.py
│           ├── test_trade_matching_steps.py
│           └── test_exception_handling_steps.py
├── pages/
│   └── confirms/            ← Page Object classes
│       ├── confirms_dashboard_page.py
│       ├── exception_queue_page.py
│       └── confirms_detail_page.py
└── test-data/
    └── confirms/            ← Test data fixtures and factories
        ├── trade_fixtures.py
        ├── swift_message_fixtures.py
        └── counterparty_fixtures.py
```

### Step Definition Conventions
- **Language**: Python (pytest-bdd)
- **Naming**: `snake_case` — `test_confirm_generation_steps.py`
- **Tags**: `@confirms`, `@smoke`, `@regression`, `@swift`, `@matching`, `@exceptions`
- **Feature file path**: `features/confirms/<feature_name>.feature`
- **Step def path**: `tests/step_defs/confirms/test_<feature_name>_steps.py`

### Key Reusable Steps
```
Given a trade of type {instrument_type} is booked at {booking_time}
When the confirms-generator processes the trade event
Then a confirm document should be created within T+1 SLA
And the confirm should be delivered via {channel}
Given a SWIFT MT515 message is generated for trade {trade_id}
Then all message fields should comply with SWIFT field length constraints
Given a trade with price {price1} is received and confirm shows {price2}
When the matching engine processes the pair
Then the match result should be {expected_result} given tolerance {tolerance}
Given a trade has been unmatched for {hours} hours
Then the trade should appear in the exception queue
And the exception severity should be escalated
```

---

## Test Environments

| Environment | Base URL |
|-------------|----------|
| Development | https://dev.confirms.internal |
| QA | https://qa.confirms.internal |
| UAT | https://uat.confirms.internal |
| SWIFT Sandbox | https://swift-sandbox.internal |

---

## Team Contacts

| Role | Responsibility |
|------|----------------|
| QA Lead | Functional + regression test ownership |
| Regulatory SME | Sign-off on EMIR/MiFID II test scenarios |
| SWIFT Operations | SWIFT sandbox access, certificate management |
| Matching Engine Lead | Tolerance configuration, matching algorithm changes |

---

## Glossary

| Term | Definition |
|------|------------|
| MT515 | SWIFT message type for equity confirms |
| MT518 | SWIFT message type for repo/SFT confirms |
| STP | Straight-Through Processing — automated confirm without manual intervention |
| T+1 SLA | Delivery must occur by end of the next business day from trade date |
| Matching Tolerance | Acceptable price deviation between trade and confirm (default ±0.0001) |
| Exception Queue | Unmatched or undeliverable confirms pending manual review |
| BIC | Bank Identifier Code — SWIFT address for counterparty routing |
