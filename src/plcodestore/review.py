"""Local transactional review approvals bound to exact metadata revisions."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .standards import content_hash, validate, public_snapshot

CHECKS = ("identity", "description", "real_screenshots", "working_links", "privacy", "security", "seo")

class ReviewStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                digest TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'needs_review',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL, digest TEXT NOT NULL, action TEXT NOT NULL,
                comment TEXT NOT NULL, checks TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS published (
                project_id TEXT PRIMARY KEY, digest TEXT NOT NULL,
                snapshot TEXT NOT NULL, published_at TEXT NOT NULL
            );
            """)

    def connection(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def stage(self, meta: dict):
        validate(meta)
        digest = content_hash(meta)
        with self.connection() as db:
            old = db.execute("SELECT digest, state FROM drafts WHERE id=?", (meta["id"],)).fetchone()
            if old and old["digest"] == digest:
                return digest
            db.execute("""INSERT INTO drafts(id,payload,digest,state,updated_at) VALUES(?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,digest=excluded.digest,
                       state=excluded.state,updated_at=excluded.updated_at""",
                       (meta["id"], json.dumps(meta, ensure_ascii=False), digest, "needs_review", self.now()))
        return digest

    def cards(self):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM drafts ORDER BY updated_at DESC").fetchall()
        return [dict(id=r["id"], meta=json.loads(r["payload"]), digest=r["digest"], state=r["state"]) for r in rows]

    def decide(self, project_id: str, digest: str, action: str, comment: str = "", checks: list[str] | None = None):
        if action not in ("approved", "changes_requested", "deferred"):
            raise ValueError("Unknown action")
        if action == "changes_requested" and not comment.strip():
            raise ValueError("Comment required on rejection")
        checks = list(checks or [])
        if action == "approved" and set(checks) != set(CHECKS):
            raise ValueError("All required checks must be complete")
        with self.connection() as db:
            row = db.execute("SELECT * FROM drafts WHERE id=?", (project_id,)).fetchone()
            if row is None:
                raise KeyError(project_id)
            if row["digest"] != digest:
                raise ValueError("Stale draft: refresh review before deciding")
            if action == "approved":
                public_snapshot(json.loads(row["payload"]))
            db.execute("UPDATE drafts SET state=? WHERE id=?",
                       ({"approved": "approved", "changes_requested": "changes_requested", "deferred": "deferred"}[action], project_id))
            db.execute("INSERT INTO decisions(project_id,digest,action,comment,checks,created_at) VALUES(?,?,?,?,?,?)",
                       (project_id, digest, action, comment.strip(), json.dumps(checks), self.now()))

    def publish(self, project_id: str):
        with self.connection() as db:
            row = db.execute("SELECT * FROM drafts WHERE id=?", (project_id,)).fetchone()
            if not row or row["state"] != "approved":
                raise ValueError("Current revision is not approved")
            snapshot = public_snapshot(json.loads(row["payload"]))
            db.execute("""INSERT INTO published(project_id,digest,snapshot,published_at) VALUES(?,?,?,?)
                       ON CONFLICT(project_id) DO UPDATE SET digest=excluded.digest,
                       snapshot=excluded.snapshot,published_at=excluded.published_at""",
                       (project_id, row["digest"], json.dumps(snapshot, ensure_ascii=False), self.now()))
            db.execute("UPDATE drafts SET state='published' WHERE id=?", (project_id,))
        return snapshot

    def published(self):
        with self.connection() as db:
            rows = db.execute("SELECT snapshot FROM published ORDER BY project_id").fetchall()
        return [json.loads(x["snapshot"]) for x in rows]

    def history(self, project_id: str):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM decisions WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
        return [dict(row) for row in rows]
