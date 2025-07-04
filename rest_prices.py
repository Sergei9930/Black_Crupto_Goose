import requests

URL = "https://api.binance.com/api/v3/ticker/price"

def main() -> None:
    data = requests.get(URL, timeout=10).json()

    counter = 1                            # ← счётчик
    for item in data:
        symbol = item["symbol"]
        if not symbol.endswith("USDT"):
            continue

        price = item["price"]
        print(f"{counter:>4}. {symbol:<10} {price}")  # 0001. BTCUSDT  62694.12
        counter += 1

if __name__ == "__main__":
    main()
