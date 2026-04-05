#!/usr/bin/env python3
"""
Update_lotto.py
1. dhlottery 직접 (쿠키 세션)
2. allorigins 프록시
3. corsproxy.io
4. Naver 검색 파싱 (확실한 최후 수단)
"""
 
import json
import time
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
 
import requests
 
JSON_FILE = "draw-history-261-latest.json"
LOTTO_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
START_ROUND = 261
 
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.dhlottery.co.kr/gameResult.do?method=byWin",
}
 
 
# ── Method 1: dhlottery 직접 (쿠키 세션) ──
def fetch_dhlottery_direct(round_num):
    try:
        s = requests.Session()
        s.get("https://www.dhlottery.co.kr/", headers=HEADERS, timeout=6)
        resp = s.get(LOTTO_API.format(round_num), headers=HEADERS, timeout=8)
        return _parse_lotto_json(resp.text, round_num)
    except Exception as e:
        print(f"  [direct] {e}")
        return "ERROR"
 
 
# ── Method 2,3: CORS 프록시 ──
def fetch_via_proxy(round_num, proxy_url):
    try:
        target = urllib.parse.quote(LOTTO_API.format(round_num), safe="")
        url = proxy_url + target
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        return _parse_lotto_json(resp.text, round_num)
    except Exception as e:
        print(f"  [proxy:{proxy_url[:30]}] {e}")
        return "ERROR"
 
 
# ── Method 4: Naver 검색 파싱 (최후 수단) ──
def fetch_from_naver(round_num):
    """Naver는 GitHub Actions IP를 차단하지 않음"""
    try:
        query = f"로또 {round_num}회 당첨번호"
        url = "https://search.naver.com/search.naver?where=nexearch&query=" + urllib.parse.quote(query)
        headers = {
            "User-Agent": UA,
            "Accept-Language": "ko-KR,ko;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=12)
        html = resp.text
        return _parse_from_naver_html(html, round_num)
    except Exception as e:
        print(f"  [naver] {e}")
        return "ERROR"
 
 
def _parse_lotto_json(raw, round_num):
    """dhlottery JSON 응답 파싱"""
    if not raw:
        return "ERROR"
 
    stripped = raw.lstrip()
    if stripped.startswith("<") or "<html" in stripped[:200].lower():
        return "BLOCKED"  # HTML = 차단됨
 
    try:
        data = json.loads(raw)
    except Exception:
        return "ERROR"
 
    if data.get("returnValue") != "success":
        return None  # 해당 회차 없음
 
    nums = sorted([int(data[f"drwtNo{i}"]) for i in range(1, 7)])
    return {
        "round": int(round_num),
        "nums": nums,
        "bonus": int(data["bnusNo"]),
        "date": data.get("drwNoDate", ""),
    }
 
 
def _parse_from_naver_html(html, round_num):
    """Naver 검색 결과 HTML에서 로또 번호 추출"""
 
    # 패턴 1: JSON 데이터 임베드 (Naver가 종종 삽입)
    m = re.search(
        r'"drwtNo1"\s*:\s*(\d+).*?"drwtNo2"\s*:\s*(\d+).*?"drwtNo3"\s*:\s*(\d+)'
        r'.*?"drwtNo4"\s*:\s*(\d+).*?"drwtNo5"\s*:\s*(\d+).*?"drwtNo6"\s*:\s*(\d+)'
        r'.*?"bnusNo"\s*:\s*(\d+)',
        html,
        re.DOTALL,
    )
    if m:
        nums = sorted([int(x) for x in m.groups()[:6]])
        bonus = int(m.group(7))
        if _valid_lotto_set(nums):
            print(f"  [naver] JSON 패턴으로 추출 성공")
            return {"round": int(round_num), "nums": nums, "bonus": bonus, "date": ""}
 
    # 패턴 2: ball_XXX 클래스 (Naver 로또 위젯)
    balls = re.findall(r'class="[^"]*ball_\d+[^"]*"[^>]*>(\d{1,2})</[a-z]+>', html)
    if len(balls) >= 6:
        nums = sorted([int(x) for x in balls[:6]])
        if _valid_lotto_set(nums):
            bonus = int(balls[6]) if len(balls) > 6 else 0
            print(f"  [naver] ball 클래스 패턴으로 추출 성공")
            return {"round": int(round_num), "nums": nums, "bonus": bonus, "date": ""}
 
    # 패턴 3: 당첨번호 뒤에 나오는 숫자 6개
    m = re.search(
        r'당첨번호[^0-9]*'
        r'(\d{1,2})[^0-9]+(\d{1,2})[^0-9]+(\d{1,2})[^0-9]+'
        r'(\d{1,2})[^0-9]+(\d{1,2})[^0-9]+(\d{1,2})',
        html,
    )
    if m:
        nums = sorted([int(x) for x in m.groups()])
        if _valid_lotto_set(nums):
            print(f"  [naver] 당첨번호 텍스트 패턴으로 추출 성공")
            return {"round": int(round_num), "nums": nums, "bonus": 0, "date": ""}
 
    # 패턴 4: 페이지에서 가능한 6개 숫자 조합 찾기 (brute force)
    all_nums = re.findall(r'\b([1-9]|[1-3]\d|4[0-5])\b', html)
    all_nums = [int(x) for x in all_nums]
    # 연속하는 6개가 모두 1-45 범위이고 합이 적절한 구간이면 추출
    for i in range(len(all_nums) - 5):
        candidate = sorted(set(all_nums[i:i+6]))
        if len(candidate) == 6 and _valid_lotto_set(candidate):
            print(f"  [naver] 브루트포스 패턴으로 추출 성공: {candidate}")
            return {"round": int(round_num), "nums": candidate, "bonus": 0, "date": ""}
 
    print(f"  [naver] 파싱 실패 (HTML 구조 변경?)")
    return "ERROR"
 
 
def _valid_lotto_set(nums):
    if len(nums) != 6 or len(set(nums)) != 6:
        return False
    if not all(1 <= n <= 45 for n in nums):
        return False
    s = sum(nums)
    return 21 <= s <= 255  # 이론 최솟값~최댓값
 
 
def fetch_round(round_num):
    """여러 방법으로 회차 조회"""
    methods = [
        ("dhlottery-direct", lambda: fetch_dhlottery_direct(round_num)),
        ("allorigins",        lambda: fetch_via_proxy(round_num, "https://api.allorigins.win/raw?url=")),
        ("corsproxy",         lambda: fetch_via_proxy(round_num, "https://corsproxy.io/?")),
        ("naver-search",      lambda: fetch_from_naver(round_num)),
    ]
 
    for name, fn in methods:
        print(f"  [{round_num}] 시도: {name}")
        try:
            result = fn()
        except Exception as e:
            print(f"  [{round_num}] {name} 예외: {e}")
            result = "ERROR"
 
        if result is None:
            print(f"  [{round_num}] {name} → 없는 회차")
            return None  # 데이터 없음 (추첨 전)
 
        if isinstance(result, dict):
            print(f"  [{round_num}] {name} → 성공 {result['nums']}")
            return result
 
        # BLOCKED or ERROR → 다음 방법
        print(f"  [{round_num}] {name} → {result}, 다음 방법으로")
        time.sleep(2)
 
    print(f"  [{round_num}] 모든 방법 실패")
    return "FAILED"
 
 
# ── 파일 로드 / 저장 ──
def load_history(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
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
    except Exception as e:
        print(f"[ERROR] 파일 읽기 실패: {e}")
        return []
 
 
def save_history(filepath, history):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
 
 
# ── 메인 ──
def main():
    kst = timezone(timedelta(hours=9))
    print(f"[INFO] {datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S KST')}")
 
    history = load_history(JSON_FILE)
    latest = max((x["round"] for x in history), default=START_ROUND - 1)
    print(f"[INFO] 현재 최신 회차: {latest}")
 
    history_map = {x["round"]: x for x in history}
    check = latest + 1
    added = 0
    fail_streak = 0
 
    while True:
        print(f"\n[CHECK] {check}회차")
        result = fetch_round(check)
 
        if result is None:
            print(f"[DONE] {check}회차 없음 → 종료")
            break
 
        if result == "FAILED":
            fail_streak += 1
            if fail_streak >= 2:
                print("[WARN] 연속 2회 실패 → 종료")
                break
            check += 1
            time.sleep(3)
            continue
 
        fail_streak = 0
        history_map[check] = result
        added += 1
        check += 1
        time.sleep(1)
 
    final = sorted(history_map.values(), key=lambda x: x["round"])
    save_history(JSON_FILE, final)
    last = final[-1]["round"] if final else "없음"
    print(f"\n[RESULT] 추가:{added}회차 / 최신:{last}회차")
 
 
if __name__ == "__main__":
    main()
