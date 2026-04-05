#!/usr/bin/env python3
"""
Update_lotto.py — Naver 검색 전용 (회차 검증 포함)
"""
 
import json, re, time, urllib.parse
from datetime import datetime, timezone, timedelta
import requests
 
JSON_FILE = "draw-history-261-latest.json"
START_ROUND = 261
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
 
 
def fetch_round(round_num):
    query = f"로또 {round_num}회 당첨번호"
    url = "https://search.naver.com/search.naver?query=" + urllib.parse.quote(query)
    try:
        resp = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR"}, timeout=12)
        html = resp.text
    except Exception as e:
        print(f"  [{round_num}] 요청 실패: {e}")
        return "ERROR"
 
    # ★ 핵심: HTML에 해당 회차 번호가 실제로 있는지 먼저 확인
    round_str = str(round_num)
    if round_str + "회" not in html and round_str + "회차" not in html:
        print(f"  [{round_num}] HTML에 {round_num}회 없음 → 추첨 전으로 판단")
        return None  # 아직 추첨 안 된 회차
 
    # 패턴 1: JSON 임베드 (drwtNo 필드)
    m = re.search(
        r'"drwtNo1"\s*:\s*(\d+).*?"drwtNo2"\s*:\s*(\d+).*?"drwtNo3"\s*:\s*(\d+)'
        r'.*?"drwtNo4"\s*:\s*(\d+).*?"drwtNo5"\s*:\s*(\d+).*?"drwtNo6"\s*:\s*(\d+)'
        r'.*?"bnusNo"\s*:\s*(\d+)',
        html, re.DOTALL,
    )
    if m:
        nums = sorted([int(x) for x in m.groups()[:6]])
        bonus = int(m.group(7))
        if valid(nums):
            print(f"  [{round_num}] 패턴1 성공: {nums} 보너스:{bonus}")
            return make(round_num, nums, bonus)
 
    # 패턴 2: ball 클래스
    balls = re.findall(r'class="[^"]*ball[_\s][^"]*"[^>]*>\s*(\d{1,2})\s*<', html)
    if len(balls) >= 6:
        nums = sorted([int(x) for x in balls[:6]])
        bonus = int(balls[6]) if len(balls) > 6 else 0
        if valid(nums):
            print(f"  [{round_num}] 패턴2 성공: {nums} 보너스:{bonus}")
            return make(round_num, nums, bonus)
 
    # 패턴 3: 당첨번호 뒤 6개 숫자
    m = re.search(
        r'당첨번호[^0-9]*(\d{1,2})[^0-9]+(\d{1,2})[^0-9]+(\d{1,2})'
        r'[^0-9]+(\d{1,2})[^0-9]+(\d{1,2})[^0-9]+(\d{1,2})',
        html,
    )
    if m:
        nums = sorted([int(x) for x in m.groups()])
        if valid(nums):
            print(f"  [{round_num}] 패턴3 성공: {nums}")
            return make(round_num, nums, 0)
 
    print(f"  [{round_num}] 파싱 실패")
    return "ERROR"
 
 
def valid(nums):
    return (len(nums) == 6 and len(set(nums)) == 6
            and all(1 <= n <= 45 for n in nums)
            and 21 <= sum(nums) <= 255)
 
 
def make(round_num, nums, bonus):
    return {"round": int(round_num), "nums": nums, "bonus": bonus, "date": ""}
 
 
def load_history():
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        history = []
        for item in data:
            if isinstance(item, dict) and "round" in item:
                history.append({
                    "round": int(item["round"]),
                    "nums": sorted([int(x) for x in item.get("nums", [])]),
                    "bonus": int(item.get("bonus", 0)),
                    "date": item.get("date", ""),
                })
        history.sort(key=lambda x: x["round"])
        return history
    except FileNotFoundError:
        return []
 
 
def save_history(history):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
 
 
def main():
    kst = timezone(timedelta(hours=9))
    print(f"[INFO] {datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S KST')}")
 
    history = load_history()
    latest = max((x["round"] for x in history), default=START_ROUND - 1)
    print(f"[INFO] 현재 최신 회차: {latest}")
 
    history_map = {x["round"]: x for x in history}
    check, added, fails = latest + 1, 0, 0
 
    while True:
        print(f"[CHECK] {check}회차")
        result = fetch_round(check)
 
        if result is None:
            print(f"[DONE] 종료")
            break
        if result == "ERROR":
            fails += 1
            if fails >= 2:
                print("[WARN] 2회 연속 실패 → 종료")
                break
            check += 1
            time.sleep(3)
            continue
 
        fails = 0
        prev = history_map.get(check - 1)

        # 직전 회차와 번호+보너스가 같으면 오탐으로 판단하고 종료
        if prev and prev.get("nums") == result.get("nums") and prev.get("bonus") == result.get("bonus"):
            print(f"[WARN] {check}회차 결과가 직전 회차와 동일 → 오탐 가능성 높음, 저장 중단")
            break
 
        history_map[check] = result
        added += 1
        check += 1
        time.sleep(1)
 
    final = sorted(history_map.values(), key=lambda x: x["round"])
    save_history(final)
    last = final[-1]["round"] if final else "없음"
    print(f"[RESULT] 추가:{added}회차 / 최신:{last}회차")
 
 
if __name__ == "__main__":
    main()
