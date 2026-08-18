import asyncio
from config import check_interval
from db import save_listing, get_known_ids, get_settings
from lzt_client import search_gifts
from autobuy import try_autobuy
from aiogram import Bot
from config import bot_token

bot = Bot(token=bot_token)

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
                # сорт по цене
                new_items.sort(key=lambda x: x['price'])
                reply = 'новые лимитные подарки:\n'
                for it in new_items:
                    reply += f"{it['created_at']} | {it['price']}₽ | {it['url']}\n"
                await bot.send_message(chat_id, reply[:4000])
                #автопокупка
                settings = await get_settings(chat_id)
                if settings['enabled']:
                    for it in new_items:
                        if it['price'] <= settings['max_price']:
                            await try_autobuy(chat_id, it, settings['check'])
            await asyncio.sleep(check_interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print('ошибка мониторинга:', e)
            await asyncio.sleep(check_interval)