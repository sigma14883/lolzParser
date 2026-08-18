import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import bot_token, check_interval
from db import init_db, save_listing, get_known_ids, get_settings, save_settings
from lzt_client import search_gifts, buy_item
from monitor import start_monitor, stop_monitor

logging.basicConfig(level=logging.INFO)
bot = Bot(token=bot_token)
dp = Dispatcher()
monitor_task = None

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
    #сорт по дате (новые сверху) и цене
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

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())