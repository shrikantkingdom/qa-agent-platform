# Jira Dashboard — Manual Setup Guide

## Overview

This guide explains how to create the shared **SCRUM QA Dashboard** in Jira Cloud.
The dashboard is visible to all three teams and provides a unified view of project health.

---

## Prerequisites

- You must have **Jira Administrator** or **Project Administrator** access for SCRUM
- All three components (`CR-statements`, `CR-confirms`, `CR-letters`) must already be created
  (see `jira_config.md` → Component Setup)

---

## Step 1 — Create Saved Filters

Each dashboard widget needs a saved filter. Create these first so they are reusable.

1. Navigate to **Filters** → **View all filters** → **Create filter**
2. Create the following filters (name and JQL exactly as shown):

| Filter Name | JQL |
|-------------|-----|
| SCRUM — All Work | `project = SCRUM ORDER BY created DESC` |
| SCRUM — Bugs | `project = SCRUM AND issuetype = Bug ORDER BY priority DESC` |
| SCRUM — High Priority | `project = SCRUM AND priority in (High, Highest) ORDER BY priority DESC, updated DESC` |
| SCRUM — Active Sprint | `project = SCRUM AND sprint in openSprints() ORDER BY assignee ASC` |
| SCRUM — In Progress | `project = SCRUM AND status = "In Progress" ORDER BY updated DESC` |
| CR-statements — Issues | `project = SCRUM AND component = "CR-statements" ORDER BY issuetype ASC` |
| CR-confirms — Issues | `project = SCRUM AND component = "CR-confirms" ORDER BY issuetype ASC` |
| CR-letters — Issues | `project = SCRUM AND component = "CR-letters" ORDER BY issuetype ASC` |
| SCRUM — Open Blockers | `project = SCRUM AND priority = Highest AND status not in (Done, Closed)` |

3. For each filter, click **Save as** and set **View access** to **All logged-in users** so all team members can see the dashboard.

---

## Step 2 — Create the Dashboard

1. Click the **Dashboards** menu in the Jira top navigation
2. Select **Create dashboard**
3. Set:
   - **Name**: `SCRUM QA Overview`
   - **Description**: `Unified QA reporting dashboard for Client Reporting — Statements, Confirms, and Letters teams`
   - **Shared with**: `All logged-in users`
4. Click **Create**

---

## Step 3 — Add Widgets

You are now on a blank dashboard. Click **Add gadget** to add each widget below.
Organise them in a **two-column layout** (click **Edit layout** → select two-column).

### Row 1 — Project Health Summary

#### Widget A: All Open Work
- **Gadget**: Issues Statistics
- **Filter**: `SCRUM — All Work`
- **Statistic**: Issue Type
- **Title**: `All Open Work`

#### Widget B: Active Sprint
- **Gadget**: Sprint Health Gadget *(or "Sprint Burndown")* 
- **Filter**: `SCRUM — Active Sprint`
- **Title**: `Active Sprint`

---

### Row 2 — Issues by Priority

#### Widget C: Bugs Overview
- **Gadget**: Issue Statistics
- **Filter**: `SCRUM — Bugs`
- **Statistic**: Priority
- **Title**: `Bugs by Priority`

#### Widget D: High Priority Issues
- **Gadget**: Issue Statistics
- **Filter**: `SCRUM — High Priority`
- **Statistic**: Assignee
- **Title**: `High Priority Issues`

---

### Row 3 — Team Distribution

#### Widget E: Statements Team Issues
- **Gadget**: Two Dimensional Filter Statistics
- **Filter**: `CR-statements — Issues`
- **X-Axis**: Issue Type
- **Y-Axis**: Status
- **Title**: `Statements Team — Issues by Type & Status`

#### Widget F: Confirms Team Issues
- **Gadget**: Two Dimensional Filter Statistics
- **Filter**: `CR-confirms — Issues`
- **X-Axis**: Issue Type
- **Y-Axis**: Status
- **Title**: `Confirms Team — Issues by Type & Status`

---

### Row 4 — Operational View

#### Widget G: Letters Team Issues
- **Gadget**: Two Dimensional Filter Statistics
- **Filter**: `CR-letters — Issues`
- **X-Axis**: Issue Type
- **Y-Axis**: Status
- **Title**: `Letters Team — Issues by Type & Status`

#### Widget H: Open Blockers
- **Gadget**: Issue Statistics
- **Filter**: `SCRUM — Open Blockers`
- **Statistic**: Assignee
- **Title**: `Open Blockers`

---

### Row 5 — In Progress Work

#### Widget I: In Progress Issues (full-width)
- **Gadget**: Assigned to Me *(or "Filter Results")* 
- **Filter**: `SCRUM — In Progress`
- **Number of results**: 20
- **Title**: `Currently In Progress`

---

## Step 4 — Share with Teams

1. Open the dashboard → click **...** (More actions) → **Share dashboard**
2. Add each team member or team group
3. For read-only access: set permission to **View**
4. For team leads who need to edit: set permission to **Edit**

---

## Step 5 — Set as Favourite (Optional)

1. From the Dashboards menu, find `SCRUM QA Overview`
2. Click the ☆ star icon to mark it as a favourite
3. Ask all team members to do the same — it will then appear in their default dashboard list

---

## Maintenance

| Task | How |
|------|-----|
| Add a new widget | Dashboard → **Add gadget** |
| Update a filter JQL | Filters → find filter → **Edit** |
| Add a new team board | See `jira_config.md` → Board Setup |
| Change layout | Dashboard → **Edit layout** |
| Clone this dashboard for a specific team | Dashboard → **...** → **Copy dashboard** |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Widget shows "No data" | Verify the saved filter returns results when run manually |
| Team board shows wrong team's issues | Check the board's Filter Query in Board Settings → General |
| `CR-statements` component not available | Create it in SCRUM Project Settings → Components |
| Permission denied on dashboard | Set dashboard sharing to "All logged-in users" |
