"""Анализатор изменений между снимками."""
import argparse
import asyncio
import json
import time
from pathlib import Path

SNAP_DIR = Path("snapshots")


def load_snapshot(idx: int) -> dict[str, float] | None:
    """Читает snapshot.json из папки snap_XX."""
    path = SNAP_DIR / f"snap_{idx:02d}" / "snapshot.json"
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


def save_result(interval: int, data: dict) -> None:
    """Сохраняет результат в results_Xs/result.json."""
    dir_path = Path(f"results_{interval}s")
    dir_path.mkdir(parents=True, exist_ok=True)
    file = dir_path / "result.json"
    with file.open("w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "interval": interval, "data": data}, f)


async def run_analyzer(interval: int) -> None:
    """Основной цикл анализатора."""
    while True:
        t = int(time.time())
        cur_idx = t % 60
        prev_idx = (t - interval) % 60

        cur = load_snapshot(cur_idx)
        prev = load_snapshot(prev_idx)
        if cur is not None and prev is not None:
            diff = compare(prev, cur)
            save_result(interval, diff)
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="анализатор снимков")
    parser.add_argument("--interval", type=int, required=True, help="секунд между сравнениями")
    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(run_analyzer(args.interval))


if __name__ == "__main__":
    main()
