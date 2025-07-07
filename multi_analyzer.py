import asyncio
import time

from analyzer import load_snapshot, compare, save_result

INTERVALS = [10, 30, 60]

async def analyze_interval(interval: int) -> None:
    """Analyze snapshots every `interval` seconds."""
    await asyncio.sleep(interval - time.time() % interval)
    while True:
        now = int(time.time())
        cur_idx = now % 60
        prev_idx = (now - interval) % 60

        cur = load_snapshot(cur_idx)
        prev = load_snapshot(prev_idx)
        if cur is not None and prev is not None:
            diff = compare(prev, cur)
            save_result(interval, diff)
        await asyncio.sleep(interval)

def main() -> None:
    tasks = [analyze_interval(i) for i in INTERVALS]
    asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))


if __name__ == "__main__":
    main()
