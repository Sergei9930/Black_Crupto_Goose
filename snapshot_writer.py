"""Асинхронная запись снимков цен из WebSocket."""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import websockets
import yaml

from exchanges import EXCHANGE_MAP

DEFAULTS = {
    "snap_dir": "snapshots",
    "exchange": "binance",
    "snap_interval": 1,
    "analysis_intervals": [10, 30, 60],
}


def load_cfg(path: str = "config.yaml") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    return {**DEFAULTS, **data}


async def receive_prices(stream_url: str, parse_func, holder: dict) -> None:
    """Слушает WebSocket и обновляет последние цены."""
    async with websockets.connect(stream_url, ping_interval=20) as ws:
        async for message in ws:
            prices = parse_func(message)
            holder["data"] = prices
            holder["ts"] = time.time()


async def write_snapshots(holder: dict, snap_dir: Path, interval: int) -> None:
    """Записывает снимок каждую секунду в циклические папки."""
    while True:
        await asyncio.sleep(interval)
        data = holder.get("data")
        if not data:
            continue
        ts = int(time.time())
        idx = ts % 60
        snap_path = snap_dir / f"snap_{idx:02d}"
        snap_path.mkdir(parents=True, exist_ok=True)
        file = snap_path / "snapshot.json"
        if file.exists():
            file.unlink()
        snapshot = {"timestamp": holder.get("ts", ts), "prices": data}
        with file.open("w", encoding="utf-8") as f:
            json.dump(snapshot, f)


def main() -> None:
    cfg = load_cfg()
    cli = argparse.ArgumentParser(description="запись snapshot.json каждую секунду")
    cli.add_argument("--exchange", choices=EXCHANGE_MAP.keys(), help="биржа")
    cli.add_argument("--snap-dir", help="каталог для снимков")
    cli.add_argument("--interval", type=int, help="частота записи, сек")
    args = cli.parse_args()

    if args.exchange:
        cfg["exchange"] = args.exchange
    if args.snap_dir:
        cfg["snap_dir"] = args.snap_dir
    if args.interval:
        cfg["snap_interval"] = args.interval

    exchange_mod = EXCHANGE_MAP[cfg["exchange"]]

    snap_root = Path(cfg["snap_dir"]) / cfg["exchange"]
    snap_root.mkdir(parents=True, exist_ok=True)

    for interval in cfg.get("analysis_intervals", [10, 30, 60]):
        (Path(f"results_{interval}s") / cfg["exchange"]).mkdir(parents=True, exist_ok=True)

    holder: dict = {}
    tasks = [
        receive_prices(exchange_mod.STREAM_URL, exchange_mod.parse_prices, holder),
        write_snapshots(holder, snap_root, cfg["snap_interval"]),
    ]
    asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))


if __name__ == "__main__":
    main()
