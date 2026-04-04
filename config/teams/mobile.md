# Mobile QA — Cross-Team Configuration
## Scope: Statements · Confirms · Letters (CRFLT)

> This file defines additional QA instructions that apply when running the
> **Statements**, **Confirms**, or **Letters** test suites on **mobile devices**.
> It extends — but does not replace — the individual team files and `global.md`.

---

## Overview

The client-facing portal and operations UIs for all three Client Reporting teams
are responsive web applications. The same Playwright test suites used for
desktop are re-executed against **mobile viewports** to verify layout, touch
interactions, and API behaviour under mobile network conditions.

| Field | Value |
|-------|-------|
| **Jira Project** | `CRFLT` (Client Reporting) |
| **Teams in scope** | Statements, Confirms, Letters |
| **Automation Repo** | https://github.com/shrikantkingdom/playwright_project |
| **Test marker** | `@pytest.mark.mobile` |
| **Viewport approach** | Playwright `--device` emulation (Chrome DevTools device descriptors) |

---

## Mobile Test Strategy per Team

### Statements
Mobile scenarios focus on the client portal — statement listing, PDF download,
and date-range filtering on small screens.

| Priority | Scenario | Platform |
|----------|----------|----------|
| P1 | Statement list renders on 375 px viewport | iOS + Android |
| P1 | PDF download link visible and tappable | iOS + Android |
| P2 | Date-range picker usable on touch screen | Both |
| P2 | "No activity" state renders correctly at 375 px | Both |
| P3 | Statement viewer scroll behaviour | iOS |

### Confirms
Mobile scenarios focus on the exception management dashboard — viewing
unmatched confirms and performing manual match/escalate actions.

| Priority | Scenario | Platform |
|----------|----------|----------|
| P1 | Exception list renders on 375 px viewport | iOS + Android |
| P1 | Manual match action accessible via touch | Both |
| P2 | SLA timer visible without horizontal scroll | Both |
| P2 | Escalate action confirmation modal usable on mobile | Both |
| P3 | Filter by instrument type on mobile | Both |

### Letters
Mobile scenarios focus on the correspondence search, suppression status
display, and bulk job status monitoring.

| Priority | Scenario | Platform |
|----------|----------|----------|
| P1 | Correspondence search renders at 375 px | iOS + Android |
| P1 | Suppression status badge visible on mobile | Both |
| P2 | Bulk job progress bar renders correctly | Both |
| P2 | Template management read-only view on mobile | Both |
| P3 | Audit trail pagination on small screen | Both |

---

## Device Emulation Matrix

Tests run using Playwright's built-in device emulation — no physical device required in CI.

| Playwright Device Descriptor | Form Factor | Represents |
|------------------------------|-------------|-----------|
| `iPhone 15` | 393 × 852 px | Small-medium iOS phone |
| `iPhone SE` | 375 × 667 px | Smallest common iOS phone |
| `Pixel 7` | 412 × 915 px | Android phone |
| `iPad Mini` | 768 × 1024 px | Tablet / iPad Mini |

Add to Playwright config:
```python
# conftest.py or playwright.config
MOBILE_DEVICES = ["iPhone 15", "iPhone SE", "Pixel 7", "iPad Mini"]
```

---

## Automation Conventions

- **Marker**: Tag all mobile-specific tests with `@pytest.mark.mobile`
- **Suite location**: Same feature files as desktop — parametrised by device
- **Page Objects**: Reuse existing Page Objects; add `is_mobile: bool` guard for touch-only steps
- **Viewport assertion**: Always assert `page.viewport_size["width"] <= 430` at start of mobile tests
- **No separate feature files**: Mobile tests use the same Gherkin scenarios with a `@mobile` tag

```gherkin
@mobile @statements @smoke
Scenario: Statement list renders on mobile
  Given I am on the statements portal on a mobile device
  When I view my account statements
  Then the statement list should be visible without horizontal scrolling
  And the PDF download button should be tappable
```

---

## Custom QA Instructions (Mobile Layer)

When generating test cases for mobile execution:

- Always parametrise by device using the Device Emulation Matrix above
- Test both **portrait** (default) and **landscape** orientations for P1 flows
- Assert no horizontal overflow (`scrollWidth <= clientWidth`) on list/table views
- Verify touch targets are ≥ 44 × 44 px (Apple HIG minimum)
- For PDF download scenarios on mobile: verify the download intent fires (do not assert file open — OS-dependent)
- API test behaviour is identical on mobile; only UI viewport tests differ
- Flag any scenario requiring native push notification or biometric auth — those are **out of scope** for Playwright emulation and require a separate native app test run

---

## Network Condition Testing

Run the following network profiles for P1 mobile tests using Playwright's CDP:

| Profile | Use case |
|---------|----------|
| `Fast 3G` (1.5 Mbps / 40ms RTT) | Confirms SLA timer accuracy under slow network |
| `Slow 3G` (750 kbps / 300ms RTT) | Statements PDF download timeout handling |
| `Offline` | Letters suppression list graceful error state |

```python
# Example: set network in test
await context.route("**/*", lambda route: route.abort())  # Offline simulation
```

---

## CI Integration

Mobile tests run as a separate job step in the GitHub Actions workflow (after desktop tests pass):

```yaml
- name: Run mobile viewport tests
  run: |
    pytest playwright_project/tests/ -m "mobile" \
      --device "iPhone 15" \
      --device "Pixel 7" \
      --junitxml=outputs/reports/mobile_results.xml
```

The `team_id` input in the workflow scopes the run to the correct team's suite.
