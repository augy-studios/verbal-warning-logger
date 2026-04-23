import aiosqlite
from contextlib import asynccontextmanager
from .config import WARNINGS_DB, POLLS_DB, TEMPLATES_DB


@asynccontextmanager
async def get_warnings_db():
    async with aiosqlite.connect(WARNINGS_DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute("PRAGMA synchronous=NORMAL")
        yield db


@asynccontextmanager
async def get_polls_db():
    async with aiosqlite.connect(POLLS_DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute("PRAGMA synchronous=NORMAL")
        yield db


@asynccontextmanager
async def get_templates_db():
    async with aiosqlite.connect(TEMPLATES_DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute("PRAGMA synchronous=NORMAL")
        yield db
