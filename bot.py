import os
import json
import asyncio
import ccxt.async_support as ccxt
import requests
from dotenv import load_dotenv
from web3 import Web3
from log_to_csv import log_arbitrage_to_csv  # CSV logger

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

# Funkcija za slanje poruke na Telegram
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

# Dohvati cijene s burze
async def get_price(exchange, symbol):
    try:
        orderbook = await exchange.fetch_order_book(symbol)
        bid = orderbook['bids'][0][0] if orderbook['bids'] else None
        ask = orderbook['asks'][0][0] if orderbook['asks'] else None
        return bid, ask
    except Exception as e:
        print(f"Error fetching order book: {e}")
        return None, None

# Glavna funkcija za provjeru i arbitražu
async def check_arbitrage_and_execute():
    symbol = "MATIC/USDT"
    exchange1 = ccxt.binance()
    exchange2 = ccxt.kucoin()

    bid1, ask1 = await get_price(exchange1, symbol)
    bid2, ask2 = await get_price(exchange2, symbol)

    await exchange1.close()
    await exchange2.close()

    if None in [bid1, ask1, bid2, ask2]:
        print("Failed to fetch data.")
        return

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
        print("No arbitrage opportunity.")
        return

    profit = sell_price - buy_price
    profit_percentage = (profit / buy_price) * 100

    if profit_percentage < 0.5:
        print("Profit too low to execute.")
        return

    # Poruka i CSV log
    message = (
        f"*Arbitrage Opportunity!*\n"
        f"Symbol: {symbol}\n"
        f"Buy on {buy_exchange} at ${buy_price:.4f}\n"
        f"Sell on {sell_exchange} at ${sell_price:.4f}\n"
        f"Profit: ${profit:.4f} ({profit_percentage:.2f}%)"
    )
    send_telegram_message(message)
    print(message)

    log_arbitrage_to_csv(symbol, buy_exchange, sell_exchange, buy_price, sell_price, profit, profit_percentage)

    # FlashLoan transakcija
    token_borrow = "0x0000000000000000000000000000000000001010"  # MATIC
    amount = w3.to_wei(100, 'ether')

    nonce = w3.eth.get_transaction_count(PUBLIC_ADDRESS)
    tx = contract.functions.startArbitrage(token_borrow, amount, token_borrow).build_transaction({
        'from': PUBLIC_ADDRESS,
        'gas': 500000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': nonce
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    send_telegram_message(f"FlashLoan executed: [View on PolygonScan](https://polygonscan.com/tx/{tx_hash.hex()})")
    print(f"FlashLoan tx: {tx_hash.hex()}")

# Glavna petlja
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
