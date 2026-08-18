from lzt_client import buy_item
from aiogram import Bot
from config import bot_token

bot = Bot(token=bot_token)

async def try_autobuy(chat_id, item, check_required):
    if check_required:
        # доп проверкa
      
    result = await buy_item(item['id'], item['price'])
    if 'error' in result:
        await bot.send_message(chat_id, f"ошибка покупки {item['url']}: {result['error']}")
    else:
        await bot.send_message(chat_id, f"куплен {item['url']} за {item['price']}₽")