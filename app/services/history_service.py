"""
history_service.py — SQLite-backed audit log for all QA platform triggers.

Each workflow run, quick-task execution, or Jira operation is recorded with:
  - who triggered it (user_name — passed from UI)
  - what task was run (task_type)
  - which Jira ticket / release / team was involved
  - which workflow steps were selected
  - when it ran and how long it took
  - summary metrics (score, test count, etc.)
  - links to generated output files
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = Path("outputs/history.db")


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id          TEXT NOT NULL UNIQUE,
                task_type       TEXT NOT NULL,
                jira_id         TEXT,
                release         TEXT,
                team_id         TEXT,
                team_name       TEXT,
                triggered_by    TEXT DEFAULT 'anonymous',
                triggered_at    TEXT NOT NULL,
                duration_secs   REAL,
                status          TEXT DEFAULT 'running',
                steps_selected  TEXT,          -- JSON array of step keys
                quality_score   INTEGER,
                alignment_score INTEGER,
                test_case_count INTEGER DEFAULT 0,
                bdd_count       INTEGER DEFAULT 0,
                error_message   TEXT,
                outputs         TEXT           -- JSON dict of {type: filename}
            );

            CREATE INDEX IF NOT EXISTS idx_runs_jira   ON runs(jira_id);
            CREATE INDEX IF NOT EXISTS idx_runs_team   ON runs(team_id);
            CREATE INDEX IF NOT EXISTS idx_runs_date   ON runs(triggered_at);
            CREATE INDEX IF NOT EXISTS idx_runs_type   ON runs(task_type);
        """)


@contextmanager
def _conn():
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


class HistoryService:
    def __init__(self):
        _init_db()

    # ── Write ──────────────────────────────────────────────────────────────────

    def create_run(
        self,
        run_id: str,
        task_type: str,
        jira_id: Optional[str],
        release: Optional[str],
        team_id: Optional[str],
        team_name: Optional[str],
        triggered_by: str,
        steps_selected: Optional[list],
    ) -> None:
        with _conn() as con:
            con.execute(
                """INSERT INTO runs
                   (run_id, task_type, jira_id, release, team_id, team_name,
                    triggered_by, triggered_at, status, steps_selected)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    task_type,
                    jira_id,
                    release,
                    team_id,
                    team_name,
                    triggered_by,
                    datetime.utcnow().isoformat(),
                    "running",
                    json.dumps(steps_selected or []),
                ),
            )

    def complete_run(
        self,
        run_id: str,
        duration_secs: float,
        quality_score: Optional[int] = None,
        alignment_score: Optional[int] = None,
        test_case_count: int = 0,
        bdd_count: int = 0,
        outputs: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> None:
        status = "failed" if error_message else "completed"
        with _conn() as con:
            con.execute(
                """UPDATE runs SET
                   duration_secs=?, status=?, quality_score=?,
                   alignment_score=?, test_case_count=?, bdd_count=?,
                   outputs=?, error_message=?
                   WHERE run_id=?""",
                (
                    round(duration_secs, 2),
                    status,
                    quality_score,
                    alignment_score,
                    test_case_count,
                    bdd_count,
                    json.dumps(outputs or {}),
                    error_message,
                    run_id,
                ),
            )

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        team_id: Optional[str] = None,
        jira_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> dict:
        filters, params = [], []
        if team_id:
            filters.append("team_id = ?"); params.append(team_id)
        if jira_id:
            filters.append("jira_id = ?"); params.append(jira_id)
        if task_type:
            filters.append("task_type = ?"); params.append(task_type)

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        params_count = list(params)
        params += [limit, offset]

        with _conn() as con:
            total = con.execute(
                f"SELECT COUNT(*) FROM runs {where}", params_count
            ).fetchone()[0]
            rows = con.execute(
                f"SELECT * FROM runs {where} ORDER BY triggered_at DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "runs": [_row_to_dict(r) for r in rows],
        }

    def get_run(self, run_id: str) -> Optional[dict]:
        with _conn() as con:
            row = con.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def get_stats(self) -> dict:
        with _conn() as con:
            total = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            completed = con.execute("SELECT COUNT(*) FROM runs WHERE status='completed'").fetchone()[0]
            avg_score = con.execute(
                "SELECT AVG(quality_score) FROM runs WHERE quality_score IS NOT NULL"
            ).fetchone()[0]
            by_team = con.execute(
                "SELECT team_name, COUNT(*) c FROM runs WHERE team_name IS NOT NULL GROUP BY team_name"
            ).fetchall()
            by_type = con.execute(
                "SELECT task_type, COUNT(*) c FROM runs GROUP BY task_type"
            ).fetchall()
            recent = con.execute(
                "SELECT * FROM runs ORDER BY triggered_at DESC LIMIT 5"
            ).fetchall()

        return {
            "total_runs": total,
            "completed_runs": completed,
            "failed_runs": total - completed,
            "avg_quality_score": round(avg_score, 1) if avg_score else None,
            "by_team": {r["team_name"]: r["c"] for r in by_team},
            "by_task_type": {r["task_type"]: r["c"] for r in by_type},
            "recent_runs": [_row_to_dict(r) for r in recent],
        }

    def delete_run(self, run_id: str) -> bool:
        with _conn() as con:
            cur = con.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
        return cur.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for field in ("steps_selected", "outputs"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                pass
    return d


history_service = HistoryService()
