# Mobile Team — QA Configuration

## Team Overview

| Field              | Value                                                        |
|--------------------|--------------------------------------------------------------|
| **Team Name**      | Mobile                                                       |
| **Jira Project**   | SCRUM                                                        |
| **Jira Dashboard** | https://shrikantpatil.atlassian.net/jira/software/projects/SCRUM/boards |
| **Primary App**    | iOS + Android native app                                     |
| **App GitHub**     | https://github.com/shrikantkingdom/sow_ui                    |
| **Automation Repo**| https://github.com/shrikantkingdom/playwright_project        |
| **Tech Stack**     | React Native, TypeScript, Detox (iOS), Espresso (Android)   |

## Application Architecture

- React Native cross-platform app (iOS 16+, Android 13+)
- REST API backend shared with web frontend
- Push notifications via FCM/APNs
- Offline-first architecture with local SQLite cache
- Biometric authentication (Face ID / fingerprint)
- Deep links and universal links

## QA Focus Areas

1. **Platform parity** — every feature must be tested on both iOS and Android
2. **Network conditions** — test on 3G, 4G, WiFi, and offline/airplane mode
3. **Device variance** — test on small (5"), medium (6.1"), and large (6.7") screens
4. **Biometric auth** — Face ID / fingerprint enrolment, error handling
5. **Push notifications** — receipt, display, and deep-link navigation
6. **Background/foreground transitions** — app state preservation

## Automation Conventions

- UI automation uses Detox (iOS) and Espresso (Android)
- API automation in `playwright_project/tests/api/` (shared with backend)
- Playwright tests cover mobile-viewport browser scenarios exclusively
- Use `@pytest.mark.mobile` marker for mobile-specific tests

## Custom QA Instructions

When generating test cases for this team:
- Always specify the target platform (iOS, Android, or Both)
- Include network condition as a test parameter for critical user journeys
- Flag any test that requires physical device vs simulator/emulator
- Offline mode tests must verify sync behaviour when connectivity returns
- Deep link tests must cover both cold-start and already-running app scenarios
- Include battery-drain and memory leak checks for long-running sessions

## Device Test Matrix

| Device          | OS          | Form Factor |
|-----------------|-------------|-------------|
| iPhone 15 Pro   | iOS 17      | 6.1" OLED   |
| iPhone SE 3     | iOS 16      | 4.7" LCD    |
| Pixel 8 Pro     | Android 14  | 6.7"        |
| Samsung S23     | Android 13  | 6.1"        |
| iPad Air 5      | iPadOS 17   | Tablet      |
