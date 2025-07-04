import json

STREAM_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"


def parse_prices(message: str) -> dict[str, float]:
    """Возвращает словарь {symbol: price} из сообщения Binance."""
    tickers = json.loads(message)
    return {t["s"]: float(t["c"]) for t in tickers if t["s"].endswith("USDT")}
