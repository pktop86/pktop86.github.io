#!/usr/bin/env python3
"""
Update_lotto.py
토요일 추첨(20:35 KST) 이후 여러 번 실행해
draw-history-261-latest.json 최신 회차 자동 추가 + 최근 회차 재검증
"""

import json
import urllib.request
from datetime import datetime, timezone, timedelta

JSON_FILE = "draw-history-261-latest.json"
LOTTO_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
START_ROUND = 261
RECHECK_COUNT = 5  # 최근 5회 재검증


def fetch_round(round_num: int):
    url = LOTTO_API.format(round_num)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))

        if data.get("returnValue") != "success":
            return None

        nums = sorted([int(data[f"drwtNo{i}"]) for i in range(1, 7)])

        return {
            "round": int(round_num),
            "nums": nums,
            "bonus": int(data["bnusNo"]),
            "date": data.get("drwNoDate", "")
        }

    except Exception as e:
        print(f"[ERROR] fetch 실패 ({round_num}회): {e}")
        return None


def load_existing_history(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("[WARN] 기존 JSON 구조가 리스트가 아님. 빈 데이터로 시작")
            return []

        history = []
        for item in data:
            if isinstance(item, dict) and "round" in item and "nums" in item and "bonus" in item:
                history.append({
                    "round": int(item["round"]),
                    "nums": sorted([int(x) for x in item["nums"]]),
                    "bonus": int(item["bonus"]),
                    "date": item.get("date", "")
                })

        history.sort(key=lambda x: x["round"])
        return history

    except FileNotFoundError:
        print("[INFO] 기존 JSON 파일이 없음. 새로 생성")
        return []

    except Exception as e:
        print(f"[ERROR] 기존 JSON 읽기 실패: {e}")
        return []


def save_history(filepath: str, history: list):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    print(f"[INFO] 실행 시각 (KST): {now.strftime('%Y-%m-%d %H:%M:%S')}")

    history = load_existing_history(JSON_FILE)

    if not history:
        latest_round = START_ROUND - 1
    else:
        latest_round = max(item["round"] for item in history)

    print(f"[INFO] 파일 내 최신 회차: {latest_round}")

    history_map = {item["round"]: item for item in history}

    recheck_from = max(START_ROUND, latest_round - RECHECK_COUNT + 1)
    for round_num in range(recheck_from, latest_round + 1):
        print(f"[INFO] {round_num}회차 재검증 중...")
        draw = fetch_round(round_num)
        if draw:
            old = history_map.get(round_num)
            if old != draw:
                print(f"[UPDATE] {round_num}회차 수정")
                history_map[round_num] = draw

    check_round = latest_round + 1
    added = 0
    while True:
        print(f"[INFO] {check_round}회차 확인 중...")
        draw = fetch_round(check_round)
        if draw is None:
            print(f"[INFO] {check_round}회차 없음 — 종료")
            break

        print(f"[ADD] {check_round}회차 추가: {draw['nums']} 보너스 {draw['bonus']}")
        history_map[check_round] = draw
        check_round += 1
        added += 1

    final_history = sorted(history_map.values(), key=lambda x: x["round"])
    save_history(JSON_FILE, final_history)

    print(f"[DONE] JSON 저장 완료 / 추가 회차 수: {added} / 최신 회차: {final_history[-1]['round']}")


if __name__ == "__main__":
    main()
