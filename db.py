import aiosqlite
from config import db_name

async def init_db():
    async with aiosqlite.connect(db_name) as db:
        await db.execute('''
            create table if not exists listings (
                id integer primary key,
                title text,
                price integer,
                created_at integer,
                url text
            )
        ''')
        await db.execute('''
            create table if not exists settings (
                user_id integer primary key,
                autobuy_enabled integer default 0,
                max_price integer default 1000,
                check_required integer default 1
            )
        ''')
        await db.commit()

async def save_listing(item):
    async with aiosqlite.connect(db_name) as db:
        await db.execute(
            'insert or ignore into listings (id, title, price, created_at, url) values (?, ?, ?, ?, ?)',
            (item['id'], item['title'], item['price'], item['created_at'], item['url'])
        )
        await db.commit()

async def get_known_ids():
    async with aiosqlite.connect(db_name) as db:
        cursor = await db.execute('select id from listings')
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

async def get_settings(user_id):
    async with aiosqlite.connect(db_name) as db:
        cursor = await db.execute(
            'select autobuy_enabled, max_price, check_required from settings where user_id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {'enabled': bool(row[0]), 'max_price': row[1], 'check': bool(row[2])}
        return {'enabled': False, 'max_price': 1000, 'check': True}

async def save_settings(user_id, enabled, max_price, check):
    async with aiosqlite.connect(db_name) as db:
        await db.execute(
            'insert or replace into settings (user_id, autobuy_enabled, max_price, check_required) values (?, ?, ?, ?)',
            (user_id, 1 if enabled else 0, max_price, 1 if check else 0)
        )
        await db.commit()