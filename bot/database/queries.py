# /bot/database/queries.py

import aiosqlite
from .core import DB_FILE

# -- User Management --

async def get_or_create_user(telegram_id: int) -> int:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (telegram_id,))
        await db.commit()
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

# -- Source Management --

async def add_source(user_id: int, url: str) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            await db.execute("INSERT INTO sources (user_id, url) VALUES (?, ?)", (user_id, url))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_source(user_id: int, url: str) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "DELETE FROM sources WHERE user_id = ? AND url = ?", (user_id, url)
        )
        await db.commit()
        return cursor.rowcount > 0

async def get_sources(user_id: int) -> list[str]:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT url FROM sources WHERE user_id = ?", (user_id,))
        return [row[0] for row in await cursor.fetchall()]

# -- Target Management --

async def add_target(source_url: str, chat_id: int) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT id FROM sources WHERE url = ?", (source_url,))
        row = await cursor.fetchone()
        if not row:
            return False
        source_id = row[0]
        try:
            await db.execute("INSERT INTO targets (source_id, chat_id) VALUES (?, ?)", (source_id, chat_id))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_targets_by_source(source_url: str) -> list[int]:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            SELECT t.chat_id FROM targets t
            JOIN sources s ON t.source_id = s.id
            WHERE s.url = ?
        """, (source_url,))
        return [row[0] for row in await cursor.fetchall()]

# -- Filter Management --

async def add_filter(source_url: str, keyword: str) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT id FROM sources WHERE url = ?", (source_url,))
        row = await cursor.fetchone()
        if not row:
            return False
        source_id = row[0]
        try:
            await db.execute("INSERT INTO filters (source_id, keyword) VALUES (?, ?)", (source_id, keyword))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_filters_by_source(source_url: str) -> list[str]:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            SELECT f.keyword FROM filters f
            JOIN sources s ON f.source_id = s.id
            WHERE s.url = ?
        """, (source_url,))
        return [row[0] for row in await cursor.fetchall()]

# -- Article Deduplication --

async def is_article_sent(source_url: str, article_url: str) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT id FROM sources WHERE url = ?", (source_url,))
        row = await cursor.fetchone()
        if not row:
            return False
        source_id = row[0]
        cursor = await db.execute(
            "SELECT id FROM sent_articles WHERE source_id = ? AND url = ?", (source_id, article_url)
        )
        return bool(await cursor.fetchone())

async def mark_article_sent(source_url: str, article_url: str):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT id FROM sources WHERE url = ?", (source_url,))
        row = await cursor.fetchone()
        if not row:
            return
        source_id = row[0]
        await db.execute("INSERT OR IGNORE INTO sent_articles (source_id, url) VALUES (?, ?)", (source_id, article_url))
        await db.commit()

async def remove_target(source_url: str, chat_id: int) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            DELETE FROM targets
            WHERE chat_id = ? AND source_id IN (
                SELECT id FROM sources WHERE url = ?
            )
        """, (chat_id, source_url))
        await db.commit()
        return cursor.rowcount > 0

async def remove_filter(source_url: str, keyword: str) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            DELETE FROM filters
            WHERE keyword = ? AND source_id IN (
                SELECT id FROM sources WHERE url = ?
            )
        """, (keyword, source_url))
        await db.commit()
        return cursor.rowcount > 0

async def get_admin_stats() -> dict:
    async with aiosqlite.connect(DB_FILE) as db:
        cursor1 = await db.execute("SELECT COUNT(*) FROM users")
        users = (await cursor1.fetchone())[0]
        cursor2 = await db.execute("SELECT COUNT(*) FROM sources")
        sources = (await cursor2.fetchone())[0]
        cursor3 = await db.execute("SELECT COUNT(*) FROM targets")
        targets = (await cursor3.fetchone())[0]
        return {"users": users, "sources": sources, "targets": targets}
