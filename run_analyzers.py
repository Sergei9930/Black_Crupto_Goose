"""Запуск нескольких анализаторов параллельно."""
import argparse
import asyncio
from pathlib import Path

from analyzer import run_analyzer, load_cfg
from exchanges import EXCHANGE_MAP


async def main() -> None:
    cfg = load_cfg()
    parser = argparse.ArgumentParser(description="запуск всех анализаторов")
    parser.add_argument("--exchange", choices=EXCHANGE_MAP.keys(), help="биржа")
    parser.add_argument("--snap-dir", help="каталог снимков")
    parser.add_argument(
        "--intervals", nargs="*", type=int, help="список интервалов через пробел"
    )
    args = parser.parse_args()

    if args.exchange:
        cfg["exchange"] = args.exchange
    if args.snap_dir:
        cfg["snap_dir"] = args.snap_dir
    if args.intervals:
        cfg["analysis_intervals"] = args.intervals

    tasks = []
    for interval in cfg.get("analysis_intervals", [10, 30, 60]):
        snap_dir = Path(cfg["snap_dir"]) / cfg["exchange"]
        results_dir = Path(f"results_{interval}s") / cfg["exchange"]
        tasks.append(run_analyzer(interval, snap_dir, results_dir))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
