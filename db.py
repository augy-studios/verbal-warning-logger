from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import aiosqlite


@dataclass(slots=True)
class VerbalWarning:
    id: int
    createdAt: str
    userId: int
    reason: str
    evidenceLink: str
    modId: int


class Database:
    def __init__(self, path: str = "warnings.db") -> None:
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.execute("PRAGMA journal_mode = WAL;")
        await self._conn.execute("PRAGMA synchronous = NORMAL;")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def init_schema(self) -> None:
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verbal_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                createdAt TEXT NOT NULL DEFAULT (datetime('now')),
                userId INTEGER NOT NULL,
                reason TEXT NOT NULL,
                evidenceLink TEXT NOT NULL,
                modId INTEGER NOT NULL
            );
            """
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vw_userId ON verbal_warnings(userId);"
        )
        await self.conn.commit()

    async def add_warning(self, user_id: int, reason: str, evidence_link: str, mod_id: int) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO verbal_warnings (userId, reason, evidenceLink, modId)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, reason, evidence_link, mod_id),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_warning(self, warning_id: int) -> Optional[VerbalWarning]:
        cur = await self.conn.execute(
            "SELECT id, createdAt, userId, reason, evidenceLink, modId FROM verbal_warnings WHERE id = ?",
            (warning_id,),
        )
        row = await cur.fetchone()
        return self._row_to_warning(row)

    async def list_warnings(self) -> list[VerbalWarning]:
        cur = await self.conn.execute(
            "SELECT id, createdAt, userId, reason, evidenceLink, modId FROM verbal_warnings ORDER BY id DESC"
        )
        rows = await cur.fetchall()
        return [self._row_to_warning(r) for r in rows if r is not None]

    async def search_by_user(self, user_id: int) -> list[VerbalWarning]:
        cur = await self.conn.execute(
            """
            SELECT id, createdAt, userId, reason, evidenceLink, modId
            FROM verbal_warnings
            WHERE userId = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        rows = await cur.fetchall()
        return [self._row_to_warning(r) for r in rows if r is not None]

    async def delete_warning(self, warning_id: int) -> int:
        cur = await self.conn.execute("DELETE FROM verbal_warnings WHERE id = ?", (warning_id,))
        await self.conn.commit()
        return cur.rowcount

    async def update_warning(
        self,
        warning_id: int,
        user_id: int,
        reason: str,
        evidence_link: str,
        mod_id: int,
    ) -> int:
        cur = await self.conn.execute(
            """
            UPDATE verbal_warnings
            SET userId = ?, reason = ?, evidenceLink = ?, modId = ?
            WHERE id = ?
            """,
            (user_id, reason, evidence_link, mod_id, warning_id),
        )
        await self.conn.commit()
        return cur.rowcount

    @staticmethod
    def _row_to_warning(row: aiosqlite.Row | None) -> Optional[VerbalWarning]:
        if row is None:
            return None
        return VerbalWarning(
            id=int(row["id"]),
            createdAt=str(row["createdAt"]),
            userId=int(row["userId"]),
            reason=str(row["reason"]),
            evidenceLink=str(row["evidenceLink"]),
            modId=int(row["modId"]),
        )