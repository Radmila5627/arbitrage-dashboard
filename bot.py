import os
import json
import asyncio
import ccxt.async_support as ccxt
import requests
from dotenv import load_dotenv
from web3 import Web3

# Učitavanje .env varijabli
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")
PROVIDER_URL = os.getenv("PROVIDER_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ABI_PATH = os.getenv("ABI_PATH")

# Web3 setup
w3 = Web3(Web3.HTTPProvider(PROVIDER_URL))
with open(ABI_PATH, 'r') as abi_file:
    abi = json.load(abi_file)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

async def get_price(exchange, symbol):
    try:
        orderbook = await exchange.fetch_order_book(symbol)
        bid = orderbook['bids'][0][0] if orderbook['bids'] else None
        ask = orderbook['asks'][0][0] if orderbook['asks'] else None
        return bid, ask
    except Exception as e:
        print(f"Error fetching order book: {e}")
        return None, None

SYMBOLS = ["MATIC/USDT", "ETH/USDT", "BTC/USDT", "USDC/USDT", "DAI/USDT"]

async def check_arbitrage_and_execute():
    exchange1 = ccxt.binance()
    exchange2 = ccxt.kucoin()

    for symbol in SYMBOLS:
        bid1, ask1 = await get_price(exchange1, symbol)
        bid2, ask2 = await get_price(exchange2, symbol)

        if None in [bid1, ask1, bid2, ask2]:
            print(f"[{symbol}] Failed to fetch data.")
            continue

        if bid1 > ask2:
            buy_exchange = "KuCoin"
            sell_exchange = "Binance"
            buy_price = ask2
            sell_price = bid1
        elif bid2 > ask1:
            buy_exchange = "Binance"
            sell_exchange = "KuCoin"
            buy_price = ask1
            sell_price = bid2
        else:
            print(f"[{symbol}] No arbitrage opportunity.")
            continue

        profit = sell_price - buy_price
        profit_percentage = (profit / buy_price) * 100

        if profit_percentage < 0.5:
            print(f"[{symbol}] Profit too low to execute.")
            continue

        message = (
            f"*Arbitrage Opportunity!*\n"
            f"Symbol: {symbol}\n"
            f"Buy on {buy_exchange} at ${buy_price:.4f}\n"
            f"Sell on {sell_exchange} at ${sell_price:.4f}\n"
            f"Profit: ${profit:.4f} ({profit_percentage:.2f}%)"
        )
        send_telegram_message(message)
        print(message)

    await exchange1.close()
    await exchange2.close()

async def main():
    while True:
        try:
            await check_arbitrage_and_execute()
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Loop error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
