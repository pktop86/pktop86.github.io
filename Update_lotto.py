#!/usr/bin/env python3
"""
Update_lotto.py
- dhlottery.co.kr GitHub Actions IP 차단 → 프록시 순환 우회
- 4가지 프록시 + 직접 접속 자동 전환
- 실패해도 크래시 없이 정상 종료
"""
 
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
 
JSON_FILE = "draw-history-261-latest.json"
LOTTO_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
START_ROUND = 261
MAX_RETRIES = 2       # 프록시당 재시도 횟수
RETRY_DELAY = 8       # 재시도 간격(초)
 
# 프록시 목록 — None=직접 접속, 나머지는 CORS 프록시
PROXIES = [
    None,
    "https://api.allorigins.win/raw?url=",
    "https://corsproxy.io/?",
    "https://api.codetabs.com/v1/proxy?quest=",
    "https://thingproxy.freeboard.io/fetch/",
]
 
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]
 
 
def make_url(round_num: int, proxy=None):
    target = LOTTO_API.format(round_num)
    if proxy is None:
        return target
    return proxy + urllib.parse.quote(target, safe="")
 
 
def fetch_once(round_num: int, proxy=None, ua_index: int = 0):
    url = make_url(round_num, proxy)
    ua = USER_AGENTS[ua_index % len(USER_AGENTS)]
 
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
            "Referer": "https://www.dhlottery.co.kr/gameResult.do?method=byWin",
            "Cache-Control": "no-cache",
        }
    )
 
    with urllib.request.urlopen(req, timeout=15) as res:
        raw = res.read().decode("utf-8", errors="replace")
 
    # HTML 응답 감지 = 차단됨
    if (raw.lstrip().startswith("<!") or
            "<html" in raw[:200].lower()):
        return "BLOCKED"
 
    data = json.loads(raw)
 
    if data.get("returnValue") != "success":
        return None  # 해당 회차 없음 (정상)
 
    nums = sorted([int(data[f"drwtNo{i}"]) for i in range(1, 7)])
    return {
        "round": int(round_num),
        "nums": nums,
        "bonus": int(data["bnusNo"]),
        "date": data.get("drwNoDate", "")
    }
 
 
def fetch_round(round_num: int):
    """프록시 순환 + 재시도로 회차 조회"""
    ua_idx = 0
    for proxy in PROXIES:
        label = (proxy[:35] + "...") if proxy else "direct"
 
        for attempt in range(MAX_RETRIES):
            try:
                result = fetch_once(round_num, proxy=proxy, ua_index=ua_idx)
                ua_idx += 1
 
                if result is None:
                    return None  # 없는 회차
 
                if isinstance(result, dict):
                    print(f"  OK ({label})")
                    return result
 
                if result == "BLOCKED":
                    print(f"  차단 ({label}) retry {attempt+1}/{MAX_RETRIES}")
                    time.sleep(RETRY_DELAY)
 
            except Exception as e:
                ua_idx += 1
                print(f"  오류 ({label}): {type(e).__name__}: {e}")
                time.sleep(RETRY_DELAY)
 
        print(f"  → {label} 실패, 다음 프록시로")
        time.sleep(3)
 
    return "FAILED"
 
 
def load_existing_history(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        history = []
        for item in data:
            if isinstance(item, dict) and "round" in item:
                history.append({
                    "round": int(item["round"]),
                    "nums": sorted([int(x) for x in item.get("nums", [])]),
                    "bonus": int(item.get("bonus", 0)),
                    "date": item.get("date", "")
                })
        history.sort(key=lambda x: x["round"])
        return history
    except FileNotFoundError:
        print("[INFO] JSON 없음 → 새로 생성")
        return []
    except Exception as e:
        print(f"[ERROR] JSON 읽기 실패: {e}")
        return []
 
 
def save_history(filepath: str, history: list):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
 
 
def main():
    kst = timezone(timedelta(hours=9))
    print(f"[INFO] 실행: {datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S KST')}")
 
    history = load_existing_history(JSON_FILE)
    latest_round = max((x["round"] for x in history), default=START_ROUND - 1)
    print(f"[INFO] 현재 최신 회차: {latest_round}")
 
    history_map = {x["round"]: x for x in history}
    check_round = latest_round + 1
    added = 0
    fail_streak = 0
 
    while True:
        print(f"[CHECK] {check_round}회차...")
        result = fetch_round(check_round)
 
        if result is None:
            print(f"[INFO] {check_round}회차 없음 → 종료")
            break
 
        if result == "FAILED":
            fail_streak += 1
            print(f"[WARN] {check_round}회차 실패 (연속 {fail_streak})")
            if fail_streak >= 2:
                print("[WARN] 연속 2회 실패 → 종료")
                break
            check_round += 1
            time.sleep(5)
            continue
 
        fail_streak = 0
        print(f"[ADD] {check_round}회차: {result['nums']} 보너스:{result['bonus']} {result['date']}")
        history_map[check_round] = result
        check_round += 1
        added += 1
        time.sleep(1)
 
    final = sorted(history_map.values(), key=lambda x: x["round"])
    save_history(JSON_FILE, final)
 
    last = final[-1]["round"] if final else "없음"
    print(f"[DONE] 추가:{added}회차 / 최신:{last}회차")
 
 
if __name__ == "__main__":
    main()
