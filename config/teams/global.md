# Global QA Standards

> This file is loaded as baseline context for ALL teams. Team-specific files extend these standards.

## Quality Bar

- Every ticket must have measurable, testable acceptance criteria (Given/When/Then preferred)
- Minimum quality score required for release: **75/100**
- Code-to-requirement alignment score must be **≥ 70/100**
- Critical issues in validation output must be resolved before release sign-off

## Testing Requirements

- Minimum **8 test cases** per feature ticket (3 Happy Path, 3 Negative, 2 Edge Case)
- All regression-risk scenarios must be tagged `@regression`
- Performance-sensitive paths must include a `@performance` tagged test
- Security-critical flows (auth, payments, PII) require dedicated negative tests for auth bypass, injection, and token expiry

## BDD Standards

- Scenarios use British English, present tense
- "Given" sets context only — no actions in Given steps
- One "When" action per scenario (compound actions use "And")
- "Then" assertions are observable and specific (avoid "should work correctly")
- Tags: `@smoke`, `@regression`, `@negative`, `@security`, `@performance`, `@edge-case`

## Jira Ticket Quality Checklist

- [ ] Summary: ≤ 60 chars, verb-noun format ("Add OAuth2 login")
- [ ] Description: explains WHY, not just WHAT
- [ ] Acceptance criteria: explicit pass/fail conditions
- [ ] Assignee, reporter, story points, priority all set
- [ ] Sprint and fix-version populated
- [ ] Linked to epic and/or parent story
- [ ] No placeholder text ("TBD", "to be defined")

## Definition of Ready

A ticket is ready for development when:
1. Acceptance criteria reviewed and approved by QA
2. Design mockups linked (for UI tickets)
3. API contract defined (for backend tickets)
4. Dependencies identified and linked

## Definition of Done

A ticket is done when:
1. Code reviewed and merged
2. All generated test cases pass in CI
3. QA Agent score ≥ 75
4. No open critical or blocker bugs
5. Release notes updated
