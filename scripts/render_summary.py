#!/usr/bin/env python3
"""
scripts/render_summary.py
──────────────────────────
Reads the qa_summary_<jira_id>.json produced by trigger_qa.py
and writes a GitHub-flavoured Markdown job summary to stdout.

Usage (in GitHub Actions):
  python scripts/render_summary.py qa_summary_CRFLT-123.json >> $GITHUB_STEP_SUMMARY
"""

import json
import sys
from pathlib import Path


GRADE_EMOJI = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "❌"}
SCORE_BAR   = lambda v: "█" * int(v // 10) + "░" * (10 - int(v // 10))


def render(summary_path: str) -> None:
    data = json.loads(Path(summary_path).read_text())

    grade     = data.get("grade", "N/A")
    score     = data.get("overall_score", 0)
    jira_id   = data.get("jira_id", "")
    team_id   = data.get("team_id", "")
    run_id    = data.get("run_id", "")
    by        = data.get("triggered_by", "")
    scores    = data.get("scores", {})
    n_issues  = data.get("issues_count", 0)
    outputs   = data.get("outputs", {})

    emoji = GRADE_EMOJI.get(str(grade).upper(), "⚪")

    lines = [
        f"## {emoji} QA Analysis — {jira_id}",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| **Jira ticket** | `{jira_id}` |",
        f"| **Team** | {team_id} |",
        f"| **Run ID** | `{run_id}` |",
        f"| **Triggered by** | {by} |",
        f"| **Grade** | **{grade}** {emoji} |",
        f"| **Overall score** | {score}/100 `{SCORE_BAR(score)}` |",
        f"| **Issues found** | {n_issues} |",
        "",
    ]

    if scores:
        lines += [
            "### Step Scores",
            "",
            "| Step | Score |",
            "|---|---|",
        ]
        for step, val in scores.items():
            bar = SCORE_BAR(val) if isinstance(val, (int, float)) else ""
            lines.append(f"| {step.replace('_', ' ').title()} | {val} {bar} |")
        lines.append("")

    if outputs:
        lines += [
            "### Artefacts",
            "",
            "> Download from the **Artifacts** section of this run.",
            "",
            "| Type | File |",
            "|---|---|",
        ]
        label_map = {
            "report":          "HTML Report",
            "testcases_csv":   "Test Cases CSV",
            "testcases_json":  "Test Cases JSON",
            "bdd_feature":     "BDD Feature file",
            "step_definitions":"Step Definitions",
        }
        for key, path in outputs.items():
            label = label_map.get(key, key)
            fname = Path(path).name if path else "—"
            lines.append(f"| {label} | `{fname}` |")
        lines.append("")

    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: render_summary.py <qa_summary_*.json>", file=sys.stderr)
        sys.exit(1)
    render(sys.argv[1])
