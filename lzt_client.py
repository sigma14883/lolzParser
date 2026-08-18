from lolzteam import MarketClient
from config import lzt_token, search_keyword

async def search_gifts():
    async with MarketClient(token=lzt_token) as market:
        # поиск 
        response = await market.accounts_list.accounts_search_async()
        items = response.get('items', [])
        results = []
        for item in items:
            title = item.get('title', '').lower()
            if search_keyword.lower() in title:
                results.append({
                    'id': item['item_id'],
                    'title': item['title'],
                    'price': item['price'],
                    'created_at': item['date_create'],  # unix timestamp
                    'url': f"https://lzt.market/item/{item['item_id']}"
                })
        return results

async def buy_item(item_id, price):
    async with MarketClient(token=lzt_token) as market:
        try:
            result = await market.purchasing.purchasing_fast_buy_async(item_id=item_id, price=price)
            return result
        except Exception as e:
            return {'error': str(e)}