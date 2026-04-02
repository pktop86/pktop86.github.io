import json
import random
from pathlib import Path
import requests

# ===== GitHub 최신 회차 파일 =====
URL = "https://raw.githubusercontent.com/pktop86/pktop86.github.io/main/draw-history-261-latest.json"

# ===== 출력 폴더 =====
OUT_DIR = Path("generated_pools")
OUT_DIR.mkdir(exist_ok=True)

# ===== 생성 설정 =====
POOL_CONFIGS = [
    {"count": 5, "total_sets": 1000},
    {"count": 10, "total_sets": 1000},
    {"count": 20, "total_sets": 1000},
]

# True  -> 최신 회차 + 1 생성
# False -> 최신 회차 그대로 생성
USE_NEXT_ROUND = True


def get_latest_round():
    res = requests.get(URL, timeout=20)
    res.raise_for_status()
    data = res.json()

    rounds = [int(d["round"]) for d in data if isinstance(d, dict) and "round" in d]
    if not rounds:
        raise ValueError("draw-history-261-latest.json 에서 round 값을 찾지 못했습니다.")

    latest = max(rounds)
    return latest + 1 if USE_NEXT_ROUND else latest


def pick6():
    return sorted(random.sample(range(1, 46), 6))


def valid(nums):
    s = sum(nums)
    if s < 90 or s > 180:
        return False

    odd = sum(1 for n in nums if n % 2 == 1)
    if odd == 0 or odd == 6:
        return False

    run = 1
    max_run = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1

    if max_run >= 4:
        return False

    return True


def score_ticket(nums):
    s = sum(nums)
    score = 0

    if 110 <= s <= 170:
        score += 10
    else:
        score += 5

    score += len(set(n % 10 for n in nums))

    low = sum(1 for n in nums if 1 <= n <= 15)
    mid = sum(1 for n in nums if 16 <= n <= 30)
    high = sum(1 for n in nums if 31 <= n <= 45)
    score += sum(1 for x in [low, mid, high] if x > 0)

    return score


def build_one_set(line_count):
    tickets = []
    seen = set()
    total_score = 0

    while len(tickets) < line_count:
        nums = pick6()
        key = ",".join(map(str, nums))

        if key in seen:
            continue
        if not valid(nums):
            continue

        seen.add(key)
        tickets.append({"nums": nums})
        total_score += score_ticket(nums)

    return tickets, round(total_score / line_count, 2)


def build_pool(round_no, line_count, total_sets):
    items = []

    for i in range(1, total_sets + 1):
        set_id = f"set_{i:06d}"
        tickets, avg_score = build_one_set(line_count)

        items.append({
            "setId": set_id,
            "round": round_no,
            "count": line_count,
            "score": avg_score,
            "issued": False,
            "issuedTo": None,
            "issuedAt": None,
            "sourceEngine": "v4_pool_prebuilt",
            "tickets": tickets,
        })

    return {
        "meta": {
            "round": round_no,
            "count": line_count,
            "status": "open",
            "issuedSets": 0,
            "totalSets": total_sets,
            "version": "v4_pool_auto"
        },
        "items": items
    }


def main():
    round_no = get_latest_round()
    print(f"target round = {round_no}")

    for cfg in POOL_CONFIGS:
        count = cfg["count"]
        total_sets = cfg["total_sets"]

        payload = build_pool(round_no, count, total_sets)

        out_file = OUT_DIR / f"pool_{round_no}_{count}.json"
        out_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"saved: {out_file}")


if __name__ == "__main__":
    main()
