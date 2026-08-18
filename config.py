import os

bot_token = os.getenv("bot_token")
lzt_token = os.getenv("lzt_token")
check_interval = 60  # между проверками(сек)
db_name = "data.db"
search_keyword = "лимитный"  # запрос
max_price_default = 1000     # лимит для автопокупкт