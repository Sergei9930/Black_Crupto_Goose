import csv
import os
from pathlib import Path

SNAP_DIR      = Path("snapshots")   # где лежат CSV-снимки
THRESHOLD_PCT = 0.5                 # выводить, если |Δ| ≥ 0.5 %

def load_last_two() -> tuple[dict[str, float], dict[str, float]]:
    """Читает два последних CSV и возвращает пары {symbol: price}."""
    files = sorted(p for p in SNAP_DIR.iterdir() if p.suffix == ".csv")
    if len(files) < 2:
        raise RuntimeError("Нужно минимум два снимка в папке snapshots/")
    prev, newest = files[-2], files[-1]

    def read(path: Path) -> dict[str, float]:
        with path.open(newline="") as f:
            return {row["symbol"]: float(row["price"]) for row in csv.DictReader(f)}

    return read(prev), read(newest)

def main() -> None:
    old, new = load_last_two()
    rows: list[tuple[str, float, float, float]] = []

    for symbol, p_old in old.items():
        p_new = new.get(symbol)
        if p_new is None or p_old == 0:          # нет цены или деление на 0
            continue
        pct = (p_new - p_old) / p_old * 100
        if abs(pct) >= THRESHOLD_PCT:            # фильтр по порогу
            rows.append((symbol, p_old, p_new, pct))

    rows.sort(key=lambda x: x[3], reverse=True)  # по величине изменения

    # вывод
    print(f"{'SYMBOL':<10} {'OLD':>12} {'NEW':>12} {'Δ%':>8}")
    for s, o, n, p in rows:
        print(f"{s:<10} {o:>12.6f} {n:>12.6f} {p:>8.2f}")

if __name__ == "__main__":
    main()
