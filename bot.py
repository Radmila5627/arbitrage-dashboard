import os
import json
import asyncio
import ccxt.async_support as ccxt
import requests
import csv
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3

# Učitavanje .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")
PROVIDER_URL = os.getenv("PROVIDER_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ABI_PATH = os.getenv("ABI_PATH")

# Web3 inicijalizacija
w3 = Web3(Web3.HTTPProvider(PROVIDER_URL))
with open(ABI_PATH, 'r') as abi_file:
    abi = json.load(abi_file)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)

# Tokeni i njihove adrese (Polygon Mainnet)
TOKENS = {
    "MATIC/USDT": "0x0000000000000000000000000000000000001010",
    "ETH/USDT": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    "BNB/USDT": "0xE2eF524fbfBbFe6eF9Af3C1A8Aefdd5a75bBedb0",
    "LINK/USDT": "0x53e0bca35ec356bd5dddfebbd1fc0fd03fabad39",
    "USDC/USDT": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
}

# Slanje Telegram poruke
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

# Zapis u CSV
def log_arbitrage_to_csv(symbol, buy_exchange, sell_exchange, buy_price, sell_price, profit, profit_percentage):
    filename = "app/orders.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Symbol", "Buy Exchange", "Sell Exchange", "Buy Price", "Sell Price", "Profit", "Profit %"])
        writer.writerow([datetime.now(), symbol, buy_exchange, sell_exchange, buy_price, sell_price, profit, profit_percentage])

# Dohvati cijenu
async def get_price(exchange, symbol):
    try:
        orderbook = await exchange.fetch_order_book(symbol)
        bid = orderbook['bids'][0][0] if orderbook['bids'] else None
        ask = orderbook['asks'][0][0] if orderbook['asks'] else None
        return bid, ask
    except Exception as e:
        print(f"Error fetching order book for {symbol}: {e}")
        return None, None

# Provjeri arbitražu za simbol
async def check_symbol(symbol, token_address):
    exchange1 = ccxt.binance()
    exchange2 = ccxt.kucoin()

    bid1, ask1 = await get_price(exchange1, symbol)
    bid2, ask2 = await get_price(exchange2, symbol)

    await exchange1.close()
    await exchange2.close()

    if None in [bid1, ask1, bid2, ask2]:
        print(f"❌ Podaci nedostupni za {symbol}")
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
        print(f"📉 Nema arbitraže za {symbol}")
        return

    profit = sell_price - buy_price
    profit_percentage = (profit / buy_price) * 100

    if profit_percentage < 0.5:
        print(f"⚠️ Profit prenizak za {symbol}")
        return

    # Zapiši i pošalji poruku
    log_arbitrage_to_csv(symbol, buy_exchange, sell_exchange, buy_price, sell_price, profit, profit_percentage)

    message = (
        f"*💰 Arbitraža Detektirana!*\n"
        f"Token: `{symbol}`\n"
        f"Kupi na *{buy_exchange}* po cijeni `${buy_price:.4f}`\n"
        f"Prodaj na *{sell_exchange}* po `${sell_price:.4f}`\n"
        f"Profit: `${profit:.4f}` ({profit_percentage:.2f}%)\n\n"
        f"[📊 Otvori Dashboard CSV](https://arbitraža-nadzorna-ploča-y1ij.vercel.app/csv.html)"
    )
    send_telegram_message(message)
    print(message)

    # Pokreni FlashLoan ako želiš
    amount = w3.to_wei(100, 'ether')
    nonce = w3.eth.get_transaction_count(PUBLIC_ADDRESS)
    tx = contract.functions.startArbitrage(token_address, amount, token_address).build_transaction({
        'from': PUBLIC_ADDRESS,
        'gas': 500000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': nonce
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    send_telegram_message(f"✅ FlashLoan za {symbol} izvršen: [PolygonScan](https://polygonscan.com/tx/{tx_hash.hex()})")
    print(f"✅ FlashLoan tx: {tx_hash.hex()}")

# Glavna petlja
async def main():
    while True:
        try:
            for symbol, address in TOKENS.items():
                await check_symbol(symbol, address)
            await asyncio.sleep(60)
        except Exception as e:
            print(f"❗ Glavna greška: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
