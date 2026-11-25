"""SQLite persistence for user preferences, deduplicated alerts, and schedule snapshots."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from i18n import DEFAULT_LANG, normalize_lang


@dataclass(frozen=True)
class UserConfig:
    chat_id: int
    queue: str | None
    lead_minutes: int
    notify_on_restore: bool
    notify_on_change: bool
    notify_on_emergency: bool
    paused: bool
    lang: str = DEFAULT_LANG


class Storage:
    """Thread-safe SQLite storage wrapper for the Telegram bot."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    queue TEXT,
                    lead_minutes INTEGER NOT NULL DEFAULT 15,
                    notify_on_restore INTEGER NOT NULL DEFAULT 1,
                    notify_on_change INTEGER NOT NULL DEFAULT 1,
                    notify_on_emergency INTEGER NOT NULL DEFAULT 1,
                    paused INTEGER NOT NULL DEFAULT 0,
                    lang TEXT NOT NULL DEFAULT 'uk',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sent_notifications (
                    chat_id INTEGER NOT NULL,
                    event_key TEXT NOT NULL,
                    created_ts INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, event_key)
                );

                CREATE TABLE IF NOT EXISTS schedule_snapshots (
                    chat_id INTEGER NOT NULL,
                    day_ts TEXT NOT NULL,
                    queue TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    PRIMARY KEY (chat_id, day_ts)
                );

                CREATE TABLE IF NOT EXISTS channel_watermarks (
                    channel TEXT PRIMARY KEY,
                    last_post_id INTEGER NOT NULL
                );
                """
            )
            cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(users)").fetchall()}
            if "notify_on_emergency" not in cols:
                self._conn.execute(
                    "ALTER TABLE users ADD COLUMN notify_on_emergency INTEGER NOT NULL DEFAULT 1"
                )
            if "lang" not in cols:
                self._conn.execute(
                    "ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT 'uk'"
                )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> UserConfig:
        keys = row.keys()
        lang_val = row["lang"] if "lang" in keys else DEFAULT_LANG
        return UserConfig(
            chat_id=int(row["chat_id"]),
            queue=row["queue"],
            lead_minutes=int(row["lead_minutes"]),
            notify_on_restore=bool(row["notify_on_restore"]),
            notify_on_change=bool(row["notify_on_change"]),
            notify_on_emergency=bool(row["notify_on_emergency"]),
            paused=bool(row["paused"]),
            lang=normalize_lang(lang_val),
        )

    def ensure_user(self, chat_id: int) -> UserConfig:
        existing = self.get_user(chat_id)
        if existing is not None:
            return existing
        now = self._now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO users (chat_id, queue, lead_minutes, notify_on_restore, notify_on_change, notify_on_emergency, paused, lang, created_at, updated_at)
                VALUES (?, NULL, 15, 1, 1, 1, 0, ?, ?, ?)
                """,
                (chat_id, DEFAULT_LANG, now, now),
            )
        user = self.get_user(chat_id)
        assert user is not None
        return user

    def get_user(self, chat_id: int) -> UserConfig | None:
        row = self._conn.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
        return self._row_to_user(row) if row else None

    def list_active_users(self) -> list[UserConfig]:
        rows = self._conn.execute(
            "SELECT * FROM users WHERE queue IS NOT NULL AND paused = 0"
        ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def list_emergency_users(self) -> list[UserConfig]:
        rows = self._conn.execute(
            "SELECT * FROM users WHERE notify_on_emergency = 1 AND paused = 0"
        ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def set_queue(self, chat_id: int, queue: str) -> UserConfig:
        self.ensure_user(chat_id)
        with self._conn:
            self._conn.execute(
                "UPDATE users SET queue = ?, updated_at = ? WHERE chat_id = ?",
                (queue, self._now_iso(), chat_id),
            )
            # Reset old schedule snapshots when user switches queue
            self._conn.execute("DELETE FROM schedule_snapshots WHERE chat_id = ?", (chat_id,))
            self._conn.execute("DELETE FROM sent_notifications WHERE chat_id = ?", (chat_id,))
        user = self.get_user(chat_id)
        assert user is not None
        return user

    def set_lead_minutes(self, chat_id: int, minutes: int) -> UserConfig:
        self.ensure_user(chat_id)
        with self._conn:
            self._conn.execute(
                "UPDATE users SET lead_minutes = ?, updated_at = ? WHERE chat_id = ?",
                (minutes, self._now_iso(), chat_id),
            )
        user = self.get_user(chat_id)
        assert user is not None
        return user

    def set_lang(self, chat_id: int, lang: str) -> UserConfig:
        normalized = normalize_lang(lang)
        self.ensure_user(chat_id)
        with self._conn:
            self._conn.execute(
                "UPDATE users SET lang = ?, updated_at = ? WHERE chat_id = ?",
                (normalized, self._now_iso(), chat_id),
            )
        user = self.get_user(chat_id)
        assert user is not None
        return user

    def toggle_field(self, chat_id: int, field: str) -> UserConfig:
        if field not in ("notify_on_restore", "notify_on_change", "notify_on_emergency", "paused"):
            raise ValueError(f"Unsupported toggle field: {field}")
        user = self.ensure_user(chat_id)
        new_val = 0 if getattr(user, field) else 1
        with self._conn:
            self._conn.execute(
                f"UPDATE users SET {field} = ?, updated_at = ? WHERE chat_id = ?",
                (new_val, self._now_iso(), chat_id),
            )
        updated = self.get_user(chat_id)
        assert updated is not None
        return updated

    def was_notified(self, chat_id: int, event_key: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sent_notifications WHERE chat_id = ? AND event_key = ?",
            (chat_id, event_key),
        ).fetchone()
        return row is not None

    def mark_notified(self, chat_id: int, event_key: str, now_ts: int) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO sent_notifications (chat_id, event_key, created_ts) VALUES (?, ?, ?)",
                (chat_id, event_key, now_ts),
            )

    def cleanup_old_notifications(self, older_than_ts: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM sent_notifications WHERE created_ts < ?",
                (older_than_ts,),
            )

    def get_snapshot(self, chat_id: int, day_ts: str) -> tuple[str, str] | None:
        row = self._conn.execute(
            "SELECT queue, signature FROM schedule_snapshots WHERE chat_id = ? AND day_ts = ?",
            (chat_id, day_ts),
        ).fetchone()
        return (row["queue"], row["signature"]) if row else None

    def set_snapshot(self, chat_id: int, day_ts: str, queue: str, signature: str) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO schedule_snapshots (chat_id, day_ts, queue, signature)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, day_ts) DO UPDATE SET
                    queue = excluded.queue,
                    signature = excluded.signature
                """,
                (chat_id, day_ts, queue, signature),
            )

    def get_channel_watermark(self, channel: str) -> int | None:
        row = self._conn.execute(
            "SELECT last_post_id FROM channel_watermarks WHERE channel = ?",
            (channel,),
        ).fetchone()
        return int(row["last_post_id"]) if row else None

    def set_channel_watermark(self, channel: str, last_post_id: int) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO channel_watermarks (channel, last_post_id)
                VALUES (?, ?)
                ON CONFLICT(channel) DO UPDATE SET last_post_id = excluded.last_post_id
                """,
                (channel, last_post_id),
            )
