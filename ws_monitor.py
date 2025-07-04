import os, csv, json, asyncio, time, argparse
from datetime import datetime
from pathlib import Path
import websockets

# ─── параметры командной строки ─────────────────────────────
p = argparse.ArgumentParser(description="Binance USDT-монитор")
p.add_argument("--focus", help="Точечная пара, напр. FUNUSDT")
args = p.parse_args()
FOCUS = args.focus.upper() if args.focus else None
# ─────────────────────────────────────────────────────────────

STREAM        = "wss://stream.binance.com:9443/ws/!ticker@arr"
SNAP_DIR      = Path("snapshots")
MAX_FILES     = 50
THRESHOLD_PCT = 0.1          # выводим, если |Δ| ≥ …
INTERVAL      = 20           # сек между сравнениями
TOP_TO_PRINT  = 20           # для общего режима

def save_snapshot(prices: dict[str, float]) -> None:
    """Пишем CSV и чистим папку до MAX_FILES файлов."""
    SNAP_DIR.mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    file = SNAP_DIR / f"{ts}.csv"
    with file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["#", "symbol", "price"])
        for i, (sym, pr) in enumerate(prices.items(), 1):
            w.writerow([i, sym, pr])
    # авто-очистка
    files = sorted(p for p in SNAP_DIR.iterdir() if p.suffix == ".csv")
    while len(files) > MAX_FILES:
        files[0].unlink(); files.pop(0)

async def monitor_focus(pair: str):
    """Режим: следим только за одной парой."""
    prev_price = None
    last_tick  = 0

    async with websockets.connect(STREAM, ping_interval=20) as ws:
        async for msg in ws:
            cur_time = time.time()
            data = json.loads(msg)
            # ищем нужную пару
            price = next(
                (float(t["c"]) for t in data if t["s"] == pair),
                None
            )
            if price is None:
                continue

            # первый приход — просто запоминаем
            if prev_price is None:
                prev_price = price
                last_tick  = cur_time
                continue

            # ждём INTERVAL сек
            if cur_time - last_tick < INTERVAL:
                continue

            pct = (price - prev_price) / prev_price * 100
            if abs(pct) >= THRESHOLD_PCT:
                sign = "+" if pct > 0 else ""
                now  = datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] {pair:<10} {price:.6f}  {sign}{pct:.2f}% за {INTERVAL}s")

            prev_price = price
            last_tick  = cur_time

async def monitor_global():
    """Режим: полный рынок USDT-пар."""
    prev = {}
    last_save = time.time()

    async with websockets.connect(STREAM, ping_interval=20) as ws:
        async for msg in ws:
            cur = {t["s"]: float(t["c"]) for t in json.loads(msg)
                   if t["s"].endswith("USDT")}
            if time.time() - last_save < INTERVAL:
                continue

            if prev:
                diffs = [(s, (cur[s]-p)/p*100) for s, p in prev.items()
                         if s in cur and p != 0 and abs((cur[s]-p)/p*100) >= THRESHOLD_PCT]
                if diffs:
                    diffs.sort(key=lambda x: abs(x[1]), reverse=True)
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"\n[{now}] изменения ≥ {THRESHOLD_PCT}% за {INTERVAL}s:")
                    for s, pct in diffs[:TOP_TO_PRINT]:
                        sign = "+" if pct > 0 else ""
                        print(f"  {s:<10} {sign}{pct:.2f}%")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] нет значимых изменений")

            save_snapshot(cur)
            prev = cur
            last_save = time.time()

# ─── точка входа ─────────────────────────────────────────────
if __name__ == "__main__":
    if FOCUS:
        print(f"▶ Фокус-режим: {FOCUS} | Δ ≥ {THRESHOLD_PCT}% | шаг {INTERVAL}s")
        coro = monitor_focus(FOCUS)
    else:
        print(f"▶ Глобальный режим | Δ ≥ {THRESHOLD_PCT}% | шаг {INTERVAL}s")
        coro = monitor_global()

    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
