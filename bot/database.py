import aiosqlite
import os
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "botbuilder.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                credits INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                service_id TEXT,
                dashboard_url TEXT,
                is_active INTEGER DEFAULT 0,
                hosting_until TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                credits_delta INTEGER DEFAULT 0,
                amount_rub REAL DEFAULT 0,
                payment_method TEXT,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.commit()


async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> dict:
    from bot.config import NEW_USER_CREDITS
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        await db.execute(
            "INSERT INTO users (telegram_id, username, first_name, credits) VALUES (?, ?, ?, ?)",
            (telegram_id, username, first_name, NEW_USER_CREDITS),
        )
        await db.execute(
            "INSERT INTO transactions (user_id, type, credits_delta, description) "
            "SELECT id, 'bonus', ?, 'Приветственные кредиты' FROM users WHERE telegram_id = ?",
            (NEW_USER_CREDITS, telegram_id),
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            return dict(await cursor.fetchone())


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_credits(user_id: int, delta: int, description: str, payment_method: str = None, amount_rub: float = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET credits = credits + ? WHERE id = ?", (delta, user_id)
        )
        await db.execute(
            "INSERT INTO transactions (user_id, type, credits_delta, amount_rub, payment_method, description) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, "topup" if delta > 0 else "spend", delta, amount_rub, payment_method, description),
        )
        await db.commit()


async def save_bot(user_id: int, name: str, description: str, service_id: str, dashboard_url: str, hosting_until: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO bots (user_id, name, description, service_id, dashboard_url, is_active, hosting_until) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (user_id, name, description, service_id, dashboard_url, hosting_until),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_bots(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_bot(bot_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def extend_hosting(bot_id: int, days: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT hosting_until FROM bots WHERE id = ?", (bot_id,)) as cursor:
            row = await cursor.fetchone()

        from datetime import timedelta
        now = datetime.now(timezone.utc)
        current = datetime.fromisoformat(row[0]) if row and row[0] else now
        base = max(current, now)
        new_until = (base + timedelta(days=days)).isoformat()

        await db.execute("UPDATE bots SET hosting_until = ?, is_active = 1 WHERE id = ?", (new_until, bot_id))
        await db.commit()
        return new_until
