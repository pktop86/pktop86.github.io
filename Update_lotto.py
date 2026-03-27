#!/usr/bin/env python3
"""
Update_lotto.py
매주 토요일 21:15 KST (12:15 UTC) GitHub Actions 실행
draw-history-261-latest.js 최신 회차 자동 추가 + 최근 회차 재검증
"""

import json
import re
import urllib.request
from datetime import datetime, timezone, timedelta

JS_FILE = "draw-history-261-latest.js"
LOTTO_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
START_ROUND = 261
RECHECK_COUNT = 3  # 최신 3회 재검증

def fetch_round(round_num):
    url = LOTTO_API.format(round_num)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
        if data.get("returnValue") != "success":
            return None
        nums = sorted([data[f"drwtNo{i}"] for i in range(1, 7)])
        return {
            "round": round_num,
            "nums": nums,
            "bonus": data["bnusNo"],
        }
    except Exception as e:
        print(f"  fetch 실패 ({round_num}회): {e}")
        return None

def load_existing_history(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"\{\s*round:\s*(\d+),\s*nums:\s*\[([^\]]+)\],\s*bonus:\s*(\d+)\s*\}"
    matches = re.findall(pattern, content)

    history = []
    for round_str, nums_str, bonus_str in matches:
        nums = [int(x.strip()) for x in nums_str.split(",")]
        history.append({
            "round": int(round_str),
            "nums": nums,
            "bonus": int(bonus_str),
        })

    history.sort(key=lambda x: x["round"])
    return history

def save_history(filepath, history):
    lines = ["window.FULL_DRAW_HISTORY = ["]
    for item in history:
        nums_str = ", ".join(str(n) for n in item["nums"])
        lines.append(f"  {{ round: {item['round']}, nums: [{nums_str}], bonus: {item['bonus']} }},")
    lines.append("];")
    lines.append("")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    print(f"실행 시각 (KST): {now.strftime('%Y-%m-%d %H:%M:%S')}")

    history = load_existing_history(JS_FILE)
    if not history:
        print("기존 파일이 비어 있음. 시작 회차부터 생성")
        latest_round = START_ROUND - 1
    else:
        latest_round = max(item["round"] for item in history)

    print(f"파일 내 최신 회차: {latest_round}")

    history_map = {item["round"]: item for item in history}

    # 최신 몇 회차는 다시 검증해서 수정
    recheck_from = max(START_ROUND, latest_round - RECHECK_COUNT + 1)
    for round_num in range(recheck_from, latest_round + 1):
        print(f"  {round_num}회차 재검증 중...")
        draw = fetch_round(round_num)
        if draw:
            if history_map.get(round_num) != draw:
                print(f"  🔄 {round_num}회차 수정: {history_map.get(round_num)} -> {draw}")
                history_map[round_num] = draw

    # 최신 다음 회차부터 추가
    check_round = latest_round + 1
    while True:
        print(f"  {check_round}회차 확인 중...")
        draw = fetch_round(check_round)
        if draw is None:
            print(f"  {check_round}회차 없음 — 종료")
            break
        print(f"  ✅ {check_round}회차 추가: {draw['nums']} 보너스 {draw['bonus']}")
        history_map[check_round] = draw
        check_round += 1

    final_history = sorted(history_map.values(), key=lambda x: x["round"])
    save_history(JS_FILE, final_history)

    print("완료: 파일 저장됨")

if __name__ == "__main__":
    main()
