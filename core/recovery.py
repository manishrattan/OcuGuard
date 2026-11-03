from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class CapacityExceededError(Exception):
    """The configured per-user storage capacity has been reached."""


class InstructionNotFoundError(Exception):
    """The requested instruction does not belong to the supplied user."""


def validate_user_id(value: object, max_chars: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > max_chars
        or not USER_ID_PATTERN.fullmatch(value)
    ):
        raise ValueError(
            f"user_id must be 1-{max_chars} characters and contain only "
            "letters, digits, dot, underscore, or hyphen."
        )
    return value


def validate_timezone(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("timezone must be a valid IANA timezone name.")
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("timezone must be a valid IANA timezone name.") from error
    return value


def parse_scheduled_at(value: object) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("scheduled_at must be an ISO-8601 datetime.") from error
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("scheduled_at must include a timezone offset.")
    return value.astimezone(timezone.utc)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RecoveryStore:
    """Local SQLite persistence for prototype instruction cards and reminders."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
            isolation_level="IMMEDIATE",
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS instructions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    instruction_text TEXT NOT NULL,
                    source_label TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_instructions_user_created
                ON instructions (user_id, created_at DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    instruction_id TEXT NOT NULL REFERENCES instructions(id)
                        ON DELETE CASCADE,
                    scheduled_at TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    recurrence_minutes INTEGER,
                    status TEXT NOT NULL CHECK (
                        status IN ('active', 'paused', 'completed')
                    ),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reminders_user_schedule
                ON reminders (user_id, scheduled_at)
                """
            )
            connection.execute("PRAGMA user_version = 1")

    def list_instructions(self, user_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, title, instruction_text, source_label, created_at,
                    updated_at
                FROM instructions
                WHERE user_id = ?
                ORDER BY created_at DESC, id
                """,
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_instruction(
        self, user_id: str, instruction_id: str
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, title, instruction_text, source_label, created_at,
                    updated_at
                FROM instructions
                WHERE user_id = ? AND id = ?
                """,
                (user_id, instruction_id),
            ).fetchone()
            return dict(row) if row else None

    def create_instruction(
        self,
        user_id: str,
        title: str,
        instruction_text: str,
        source_label: str,
        max_items: int,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        item = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "instruction_text": instruction_text,
            "source_label": source_label,
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM instructions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if int(count["count"]) >= max_items:
                raise CapacityExceededError(
                    "The configured instruction-card limit was reached."
                )
            connection.execute(
                """
                INSERT INTO instructions (
                    id, user_id, title, instruction_text, source_label,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(item.values()),
            )
        return {key: value for key, value in item.items() if key != "user_id"}

    def update_instruction(
        self,
        user_id: str,
        instruction_id: str,
        title: str,
        instruction_text: str,
        source_label: str,
    ) -> dict[str, Any] | None:
        now = utc_now_iso()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE instructions
                SET title = ?, instruction_text = ?, source_label = ?,
                    updated_at = ?
                WHERE user_id = ? AND id = ?
                """,
                (title, instruction_text, source_label, now, user_id, instruction_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_instruction(user_id, instruction_id)

    def delete_instruction(self, user_id: str, instruction_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM instructions WHERE user_id = ? AND id = ?",
                (user_id, instruction_id),
            )
            return cursor.rowcount > 0

    def create_reminder(
        self,
        user_id: str,
        instruction_id: str,
        scheduled_at: datetime,
        timezone_name: str,
        recurrence_minutes: int | None,
        max_items: int,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        reminder = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "instruction_id": instruction_id,
            "scheduled_at": scheduled_at.isoformat(),
            "timezone": timezone_name,
            "recurrence_minutes": recurrence_minutes,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            instruction = connection.execute(
                "SELECT 1 FROM instructions WHERE id = ? AND user_id = ?",
                (instruction_id, user_id),
            ).fetchone()
            if instruction is None:
                raise InstructionNotFoundError
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM reminders WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if int(count["count"]) >= max_items:
                raise CapacityExceededError(
                    "The configured reminder limit was reached."
                )
            connection.execute(
                """
                INSERT INTO reminders (
                    id, user_id, instruction_id, scheduled_at, timezone,
                    recurrence_minutes, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(reminder.values()),
            )
        return self._public_reminder(reminder, None)

    def list_reminders(
        self, user_id: str, now: datetime | None = None
    ) -> list[dict[str, Any]]:
        current_time = now or datetime.now(timezone.utc)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT r.id, r.instruction_id, i.title AS instruction_title,
                    r.scheduled_at, r.timezone, r.recurrence_minutes, r.status,
                    r.created_at, r.updated_at
                FROM reminders AS r
                JOIN instructions AS i ON i.id = r.instruction_id
                WHERE r.user_id = ?
                ORDER BY r.scheduled_at, r.id
                """,
                (user_id,),
            ).fetchall()
            return [
                self._public_reminder(dict(row), current_time)
                for row in rows
            ]

    def update_reminder_action(
        self,
        user_id: str,
        reminder_id: str,
        action: str,
        snooze_minutes: int | None = None,
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT id, instruction_id, scheduled_at, timezone,
                    recurrence_minutes, status, created_at, updated_at
                FROM reminders
                WHERE user_id = ? AND id = ?
                """,
                (user_id, reminder_id),
            ).fetchone()
            if row is None:
                return None

            reminder = dict(row)
            now = datetime.now(timezone.utc)
            if action == "pause" and reminder["status"] == "active":
                reminder["status"] = "paused"
            elif action == "resume" and reminder["status"] == "paused":
                reminder["status"] = "active"
            elif (
                action == "snooze"
                and reminder["status"] == "active"
                and snooze_minutes is not None
            ):
                reminder["scheduled_at"] = (
                    now + timedelta(minutes=snooze_minutes)
                ).isoformat()
            elif action == "acknowledge" and reminder["status"] == "active":
                interval = reminder["recurrence_minutes"]
                if interval is None:
                    reminder["status"] = "completed"
                else:
                    reminder["scheduled_at"] = _next_occurrence(
                        datetime.fromisoformat(reminder["scheduled_at"]),
                        int(interval),
                        reminder["timezone"],
                        now,
                    ).isoformat()
            else:
                raise ValueError(
                    f"Cannot perform '{action}' while reminder is "
                    f"{reminder['status']} or without a valid snooze interval."
                )
            reminder["updated_at"] = now.isoformat()
            connection.execute(
                """
                UPDATE reminders
                SET scheduled_at = ?, status = ?, updated_at = ?
                WHERE user_id = ? AND id = ?
                """,
                (
                    reminder["scheduled_at"],
                    reminder["status"],
                    reminder["updated_at"],
                    user_id,
                    reminder_id,
                ),
            )
        return self._public_reminder(reminder, now)

    def delete_reminder(self, user_id: str, reminder_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM reminders WHERE user_id = ? AND id = ?",
                (user_id, reminder_id),
            )
            return cursor.rowcount > 0

    def delete_user_data(self, user_id: str) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM reminders WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM instructions WHERE user_id = ?", (user_id,))

    @staticmethod
    def _public_reminder(
        reminder: dict[str, Any], now: datetime | None
    ) -> dict[str, Any]:
        scheduled_at = datetime.fromisoformat(reminder["scheduled_at"])
        current_time = now or datetime.now(timezone.utc)
        return {
            key: value
            for key, value in {
                **reminder,
                "due": (
                    reminder["status"] == "active"
                    and scheduled_at <= current_time
                ),
            }.items()
            if key != "user_id"
        }


def _next_occurrence(
    scheduled_at: datetime,
    recurrence_minutes: int,
    timezone_name: str,
    now: datetime,
) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_scheduled = scheduled_at.astimezone(zone)
    delta = timedelta(minutes=recurrence_minutes)
    next_time = local_scheduled + delta
    while next_time.astimezone(timezone.utc) <= now:
        next_time += delta
    return next_time.astimezone(timezone.utc)
