"""SQLite cache so papers already scored are not scored (or downloaded) again."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = (
    "title",
    "published",
    "abstract_assessment",
    "fulltext_assessment",
    "final_score",
    "pdf_path",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    project_key TEXT NOT NULL,
    arxiv_id TEXT NOT NULL,
    title TEXT,
    published TEXT,
    abstract_assessment TEXT,
    fulltext_assessment TEXT,
    final_score INTEGER,
    pdf_path TEXT,
    updated_at TEXT,
    PRIMARY KEY (project_key, arxiv_id)
)
"""


def project_key(project_title: str) -> str:
    """Scores depend on the project, so the cache is keyed by project too."""
    return hashlib.sha1(project_title.strip().lower().encode("utf-8")).hexdigest()[:12]


class Store:
    def __init__(self, path: str | os.PathLike, project_title: str):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.key = project_key(project_title)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(_SCHEMA)
        self.conn.commit()

    def get(self, arxiv_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM papers WHERE project_key = ? AND arxiv_id = ?", (self.key, arxiv_id)
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        for name in ("abstract_assessment", "fulltext_assessment"):
            data[name] = json.loads(data[name]) if data[name] else None
        return data

    def upsert(self, arxiv_id: str, **fields) -> None:
        unknown = set(fields) - set(COLUMNS)
        if unknown:
            raise ValueError(f"Unknown column(s): {', '.join(sorted(unknown))}")
        values = {
            name: json.dumps(value) if name.endswith("_assessment") and value is not None else value
            for name, value in fields.items()
        }
        values["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        names = list(values)
        placeholders = ", ".join("?" for _ in range(len(names) + 2))
        updates = ", ".join(f"{n} = excluded.{n}" for n in names)
        self.conn.execute(
            f"INSERT INTO papers (project_key, arxiv_id, {', '.join(names)}) VALUES ({placeholders}) "
            f"ON CONFLICT(project_key, arxiv_id) DO UPDATE SET {updates}",
            (self.key, arxiv_id, *values.values()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
