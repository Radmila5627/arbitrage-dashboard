import csv
from datetime import datetime

def log_arbitrage_to_csv(symbol, buy_exchange, sell_exchange, buy_price, sell_price, profit, profit_pct):
    filename = 'orders.csv'

    data = {
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': symbol,
        'buy_exchange': buy_exchange,
        'sell_exchange': sell_exchange,
        'buy_price': round(buy_price, 6),
        'sell_price': round(sell_price, 6),
        'profit': round(profit, 6),
        'profit_%': round(profit_pct, 4),
    }

    file_exists = False
    try:
        with open(filename, 'r', newline='') as f:
            file_exists = True
    except FileNotFoundError:
        pass

    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['datetime', 'symbol', 'buy_exchange', 'sell_exchange', 'buy_price', 'sell_price', 'profit', 'profit_%']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
