import json
import random
from pathlib import Path

ROUND = 1218
COUNT = 5
SET_TOTAL = 1000
OUT_FILE = Path("pool_1218_5.json")


def pick6():
    nums = sorted(random.sample(range(1, 46), 6))
    return nums


def valid(nums):
    s = sum(nums)
    if s < 90 or s > 180:
        return False
    odd = sum(1 for n in nums if n % 2 == 1)
    if odd == 0 or odd == 6:
        return False
    return True


def build_one_set(line_count=5):
    tickets = []
    seen = set()

    while len(tickets) < line_count:
        nums = pick6()
        key = ",".join(map(str, nums))
        if key in seen:
            continue
        if not valid(nums):
            continue
        seen.add(key)
        tickets.append({"nums": nums})

    return tickets


def main():
    items = []
    for i in range(1, SET_TOTAL + 1):
        set_id = f"set_{i:06d}"
        item = {
            "setId": set_id,
            "round": ROUND,
            "count": COUNT,
            "score": 90.0,
            "issued": False,
            "sourceEngine": "v4_pool_prebuilt",
            "tickets": build_one_set(COUNT),
        }
        items.append(item)

    payload = {
        "meta": {
            "round": ROUND,
            "count": COUNT,
            "status": "open",
            "issuedSets": 0,
            "totalSets": SET_TOTAL,
            "version": "v4_pool"
        },
        "items": items
    }

    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
