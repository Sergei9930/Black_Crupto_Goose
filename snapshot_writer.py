"""Асинхронная запись снимков цен из WebSocket."""
import asyncio
import json
import time
from pathlib import Path
import websockets

from exchanges import EXCHANGE_MAP

# где хранить папки snap_XX
SNAP_DIR = Path("snapshots")
# какую биржу используем
EXCHANGE = "binance"


async def receive_prices(stream_url: str, parse_func, holder: dict) -> None:
    """Слушает WebSocket и обновляет последние цены."""
    async with websockets.connect(stream_url, ping_interval=20) as ws:
        async for message in ws:
            prices = parse_func(message)
            holder["data"] = prices
            holder["ts"] = time.time()


async def write_snapshots(holder: dict) -> None:
    """Записывает снимок каждую секунду в циклические папки."""
    while True:
        await asyncio.sleep(1)
        data = holder.get("data")
        if not data:
            continue
        ts = int(time.time())
        idx = ts % 60
        snap_path = SNAP_DIR / f"snap_{idx:02d}"
        snap_path.mkdir(parents=True, exist_ok=True)
        file = snap_path / "snapshot.json"
        snapshot = {"timestamp": holder.get("ts", ts), "prices": data}
        with file.open("w", encoding="utf-8") as f:
            json.dump(snapshot, f)


def main() -> None:
    exchange_mod = EXCHANGE_MAP[EXCHANGE]
    holder: dict = {}
    tasks = [
        receive_prices(exchange_mod.STREAM_URL, exchange_mod.parse_prices, holder),
        write_snapshots(holder),
    ]
    asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))


if __name__ == "__main__":
    main()
