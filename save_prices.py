import os, csv, time
from datetime import datetime
import requests

URL         = "https://api.binance.com/api/v3/ticker/price"
INTERVAL    = 10      # секунд между снимками
MAX_FILES   = 50      # сколько CSV храним
SNAP_DIR    = "snapshots"

def fetch_usdt() -> list[list[str]]:
    """Возвращает список [№, SYMBOL, PRICE] только по парам *USDT."""
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    rows, counter = [], 1
    for item in data:
        symbol = item["symbol"]
        if not symbol.endswith("USDT"):
            continue
        rows.append([counter, symbol, item["price"]])
        counter += 1
    return rows

def save_snapshot(rows: list[list[str]]) -> None:
    os.makedirs(SNAP_DIR, exist_ok=True)

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    file = f"{SNAP_DIR}/{ts}.csv"

    # записываем CSV
    with open(file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["#", "symbol", "price"])
        w.writerows(rows)

    print(f"[{ts}] сохранено → {file}")

    # ----------------  авто-очистка  ----------------
    files = sorted(f for f in os.listdir(SNAP_DIR) if f.endswith(".csv"))
    while len(files) > MAX_FILES:
        old = files.pop(0)                         # самый ранний
        os.remove(os.path.join(SNAP_DIR, old))
        print(f"Удалён старый снимок → {old}")

def main():
    while True:
        try:
            rows = fetch_usdt()
            save_snapshot(rows)
        except Exception as e:
            print("Ошибка:", e)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
