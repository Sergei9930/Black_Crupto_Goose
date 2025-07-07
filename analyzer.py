"""Анализатор изменений между снимками."""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import yaml

from exchanges import EXCHANGE_MAP

DEFAULTS = {
    "snap_dir": "snapshots",
    "exchange": "binance",
    "analysis_intervals": [10, 30, 60],
}


def load_cfg(path: str = "config.yaml") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    return {**DEFAULTS, **data}


def load_snapshot(idx: int, snap_dir: Path) -> dict[str, float] | None:
    """Читает snapshot.json из папки snap_XX."""
    path = snap_dir / f"snap_{idx:02d}" / "snapshot.json"
    if not path.exists():
        return None
    with path.open() as f:
        data = json.load(f)
    return data.get("prices", {})


def compare(old: dict[str, float], new: dict[str, float]) -> dict[str, dict]:
    """Возвращает изменения в процентах между двумя снимками."""
    result: dict[str, dict] = {}
    for symbol, old_price in old.items():
        new_price = new.get(symbol)
        if new_price is None or old_price == 0:
            continue
        pct = (new_price - old_price) / old_price * 100
        result[symbol] = {"old": old_price, "new": new_price, "pct": pct}
    return result


def save_result(interval: int, results_dir: Path, data: dict) -> None:
    """Сохраняет результат в results_Xs/<exchange>/result.json."""
    results_dir.mkdir(parents=True, exist_ok=True)
    for old in results_dir.glob("*.json"):
        old.unlink()
    file = results_dir / "result.json"
    with file.open("w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "interval": interval, "data": data}, f)


async def run_analyzer(interval: int, snap_dir: Path, results_dir: Path) -> None:
    """Основной цикл анализатора."""
    while True:
        t = int(time.time())
        cur_idx = t % 60
        prev_idx = (t - interval) % 60

        cur = load_snapshot(cur_idx, snap_dir)
        prev = load_snapshot(prev_idx, snap_dir)
        if cur is not None and prev is not None:
            diff = compare(prev, cur)
            save_result(interval, results_dir, diff)
        await asyncio.sleep(interval)


def main() -> None:
    cfg = load_cfg()
    parser = argparse.ArgumentParser(description="анализатор снимков")
    parser.add_argument("--interval", type=int, help="секунд между сравнениями")
    parser.add_argument("--exchange", choices=EXCHANGE_MAP.keys(), help="биржа")
    parser.add_argument("--snap-dir", help="где лежат снимки")
    args = parser.parse_args()

    if args.interval:
        cfg_interval = args.interval
    else:
        cfg_interval = cfg.get("interval") or cfg.get("analysis_intervals", [])[0]

    if args.exchange:
        cfg["exchange"] = args.exchange
    if args.snap_dir:
        cfg["snap_dir"] = args.snap_dir

    snap_dir = Path(cfg["snap_dir"]) / cfg["exchange"]
    results_dir = Path(f"results_{cfg_interval}s") / cfg["exchange"]

    asyncio.get_event_loop().run_until_complete(
        run_analyzer(cfg_interval, snap_dir, results_dir)
    )


if __name__ == "__main__":
    main()
