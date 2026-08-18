import asyncio
import logging
import os
import aiosqlite
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

logging.basicConfig(level=logging.INFO)

bot_token = os.getenv('bot_token')
lzt_token = os.getenv('lzt_token')
check_interval = 60
db_name = 'data.db'
search_keyword = 'лимитный'

bot = Bot(token=bot_token)
dp = Dispatcher()
monitor_task = None

async def init_db():
    async with aiosqlite.connect(db_name) as db:
        await db.execute('create table if not exists listings (id integer primary key, title text, price integer, created_at integer, url text)')
        await db.execute('create table if not exists settings (user_id integer primary key, autobuy_enabled integer default 0, max_price integer default 1000, check_required integer default 1)')
        await db.commit()

async def save_listing(item):
    async with aiosqlite.connect(db_name) as db:
        await db.execute('insert or ignore into listings (id, title, price, created_at, url) values (?,?,?,?,?)',
                         (item['id'], item['title'], item['price'], item['created_at'], item['url']))
        await db.commit()

async def get_known_ids():
    async with aiosqlite.connect(db_name) as db:
        cursor = await db.execute('select id from listings')
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

async def get_settings(user_id):
    async with aiosqlite.connect(db_name) as db:
        cursor = await db.execute('select autobuy_enabled, max_price, check_required from settings where user_id = ?', (user_id,))
        row = await cursor.fetchone()
        if row:
            return {'enabled': bool(row[0]), 'max_price': row[1], 'check': bool(row[2])}
        return {'enabled': False, 'max_price': 1000, 'check': True}

async def save_settings(user_id, enabled, max_price, check):
    async with aiosqlite.connect(db_name) as db:
        await db.execute('insert or replace into settings (user_id, autobuy_enabled, max_price, check_required) values (?,?,?,?)',
                         (user_id, 1 if enabled else 0, max_price, 1 if check else 0))
        await db.commit()

async def search_gifts():
    url = 'https://api.lolz.live/market/accounts/search'
    headers = {'Authorization': f'Bearer {lzt_token}'}
    params = {'price_max': 5000}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    logging.error(f'api error {resp.status}')
                    return []
                data = await resp.json()
                items = data.get('items', [])
                results = []
                for item in items:
                    if search_keyword.lower() in item.get('title', '').lower():
                        results.append({
                            'id': item['item_id'],
                            'title': item['title'],
                            'price': item['price'],
                            'created_at': item.get('date_create', 0),
                            'url': f"https://lzt.market/item/{item['item_id']}"
                        })
                return results
        except Exception as e:
            logging.error(f'search error: {e}')
            return []

async def buy_item(item_id, price):
    url = 'https://api.lolz.live/market/purchase/fast_buy'
    headers = {'Authorization': f'Bearer {lzt_token}'}
    data = {'item_id': item_id, 'price': price}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as resp:
                return await resp.json()
        except Exception as e:
            return {'error': str(e)}

async def try_autobuy(chat_id, item, check_required):
    if check_required:
        pass
    result = await buy_item(item['id'], item['price'])
    if 'error' in result:
        await bot.send_message(chat_id, f"ошибка покупки {item['url']}: {result['error']}")
    else:
        await bot.send_message(chat_id, f"куплен {item['url']} за {item['price']}₽")

async def start_monitor(chat_id):
    known = await get_known_ids()
    while True:
        try:
            items = await search_gifts()
            new_items = [it for it in items if it['id'] not in known]
            if new_items:
                for it in new_items:
                    await save_listing(it)
                    known.add(it['id'])
                new_items.sort(key=lambda x: x['price'])
                reply = 'новые лимитные подарки:\n'
                for it in new_items:
                    reply += f"{it['created_at']} | {it['price']}₽ | {it['url']}\n"
                await bot.send_message(chat_id, reply[:4000])
                settings = await get_settings(chat_id)
                if settings['enabled']:
                    for it in new_items:
                        if it['price'] <= settings['max_price']:
                            await try_autobuy(chat_id, it, settings['check'])
            await asyncio.sleep(check_interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f'monitor error: {e}')
            await asyncio.sleep(check_interval)

@dp.message(Command('start'))
async def start(msg: types.Message):
    await msg.answer('бот для поиска лимитных подарков. команды: /search, /monitor on/off, /set_autobuy')

@dp.message(Command('search'))
async def search_cmd(msg: types.Message):
    await msg.answer('ищу...')
    items = await search_gifts()
    if not items:
        await msg.answer('ничего не найдено')
        return
    items.sort(key=lambda x: (x['created_at'], x['price']))
    reply = 'найденные объявления:\n'
    for it in items:
        reply += f"{it['created_at']} | {it['price']}₽ | {it['url']}\n"
    await msg.answer(reply[:4000])

@dp.message(Command('monitor'))
async def monitor_cmd(msg: types.Message):
    global monitor_task
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer('укажи on или off')
        return
    if args[1].lower() == 'on':
        if monitor_task and not monitor_task.done():
            await msg.answer('мониторинг уже запущен')
        else:
            monitor_task = asyncio.create_task(start_monitor(msg.chat.id))
            await msg.answer('мониторинг включён')
    elif args[1].lower() == 'off':
        if monitor_task:
            monitor_task.cancel()
            monitor_task = None
            await msg.answer('мониторинг выключен')
        else:
            await msg.answer('мониторинг не был запущен')

@dp.message(Command('set_autobuy'))
async def set_autobuy(msg: types.Message):
    args = msg.text.split()
    if len(args) < 3:
        await msg.answer('формат: /set_autobuy <макс_цена> <проверка_да/нет>')
        return
    try:
        max_price = int(args[1])
        check = args[2].lower() in ('да', 'yes', 'true')
    except:
        await msg.answer('неверный формат')
        return
    await save_settings(msg.chat.id, True, max_price, check)
    await msg.answer(f'автопокупка: цена ≤ {max_price}, проверка {"вкл" if check else "выкл"}')

async def health_check(request):
    return web.Response(text='ok')

async def run_web():
    app = web.Application()
    app.router.add_get('/', health_check)
    port = int(os.environ.get('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f'веб-сервер запущен на порту {port}')
    await asyncio.Event().wait()

async def main():
    await init_db()
    await asyncio.gather(
        dp.start_polling(bot),
        run_web()
    )

if __name__ == '__main__':
    asyncio.run(main())