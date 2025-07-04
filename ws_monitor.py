import os, csv, json, asyncio, time, argparse, yaml
from datetime import datetime
from pathlib import Path
import websockets

# ─────────────────────────────────────────────────────────────
# 1️⃣  Читаем YAML-конфиг  (config.yaml)  +  значения по умолчанию
# ─────────────────────────────────────────────────────────────
DEFAULTS = dict(
    interval       = 20,        # сек между циклами сравнения/сохранения
    threshold_pct  = 0.1,       # выводить, если |Δ| ≥ threshold_pct
    max_files      = 50,        # хранить не более N CSV-снимков
    snap_dir       = "snapshots",
    top_to_print   = 20,        # сколько пар выводить в глобальном режиме
    focus          = None,      # например "FUNUSDT" — точечный режим
)

def load_cfg(path="config.yaml") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    return {**DEFAULTS, **data}   # YAML перекрывает дефолты

CFG = load_cfg()

# ─────────────────────────────────────────────────────────────
# 2️⃣  CLI-аргументы — перекрывают YAML только на текущий запуск
# ─────────────────────────────────────────────────────────────
cli = argparse.ArgumentParser(description="Binance USDT-монитор")
cli.add_argument("--focus", help="точечная пара, напр. FUNUSDT")
cli.add_argument("--interval", type=int, help="секунд между циклами")
cli.add_argument("--thr", "--threshold", dest="threshold_pct", type=float,
                 help="порог Δ%")
args = cli.parse_args()
for k, v in vars(args).items():
    if v is not None:
        CFG[k] = v

# ─────────────────────────────────────────────────────────────
# 3️⃣  Переменные  (используются ниже в коде)
# ─────────────────────────────────────────────────────────────
INTERVAL      = CFG["interval"]
THRESHOLD_PCT = CFG["threshold_pct"]
MAX_FILES     = CFG["max_files"]
SNAP_DIR      = Path(CFG["snap_dir"])
TOP_TO_PRINT  = CFG["top_to_print"]
FOCUS         = CFG["focus"].upper() if CFG["focus"] else None

STREAM = "wss://stream.binance.com:9443/ws/!ticker@arr"

# ─────────────────────────────────────────────────────────────
def save_snapshot(prices: dict[str, float]) -> None:
    """Записывает CSV-снимок и чистит папку до MAX_FILES."""
    SNAP_DIR.mkdir(exist_ok=True)
    ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file = SNAP_DIR / f"{ts}.csv"

    with file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["#", "symbol", "price"])
        for i, (sym, pr) in enumerate(prices.items(), 1):
            w.writerow([i, sym, pr])

    files = sorted(p for p in SNAP_DIR.iterdir() if p.suffix == ".csv")
    while len(files) > MAX_FILES:
        files[0].unlink(); files.pop(0)

# ─────────────────────────────────────────────────────────────
# 4️⃣  Режим «точечная пара»
# ─────────────────────────────────────────────────────────────
async def monitor_focus(pair: str):
    prev_price = None
    last_tick  = 0

    async with websockets.connect(STREAM, ping_interval=20) as ws:
        async for msg in ws:
            tickers = json.loads(msg)
            price = next((float(t["c"]) for t in tickers if t["s"] == pair), None)
            if price is None:
                continue

            if prev_price is None:
                prev_price, last_tick = price, time.time()
                continue

            if time.time() - last_tick < INTERVAL:
                continue

            pct = (price - prev_price) / prev_price * 100
            if abs(pct) >= THRESHOLD_PCT:
                sign = "+" if pct > 0 else ""
                now  = datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] {pair:<10} {price:.6f}  {sign}{pct:.2f}% за {INTERVAL}s")

            prev_price, last_tick = price, time.time()

# ─────────────────────────────────────────────────────────────
# 5️⃣  Режим «глобальный рынок»
# ─────────────────────────────────────────────────────────────
async def monitor_global():
    prev = {}
    last_save = time.time()

    async with websockets.connect(STREAM, ping_interval=20) as ws:
        async for msg in ws:
            cur = {t["s"]: float(t["c"])
                   for t in json.loads(msg) if t["s"].endswith("USDT")}

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
            prev, last_save = cur, time.time()

# ─────────────────────────────────────────────────────────────
# 6️⃣  Точка входа
# ─────────────────────────────────────────────────────────────
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
