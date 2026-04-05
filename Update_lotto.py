#!/usr/bin/env python3
"""
Update_lotto.py
토요일 추첨(20:35 KST) 이후 실행해
draw-history-261-latest.json 최신 회차 자동 추가
"""
 
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta
 
JSON_FILE = "draw-history-261-latest.json"
LOTTO_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
START_ROUND = 261
MAX_RETRIES = 4      # 최대 재시도 횟수
RETRY_DELAY = 15     # 재시도 간격 (초)
 
# User-Agent 목록 - 번갈아 사용해 차단 우회
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]
 
 
def fetch_round(round_num: int, ua_index: int = 0):
    """단일 회차 조회 (UA 순환)"""
    url = LOTTO_API.format(round_num)
    ua = USER_AGENTS[ua_index % len(USER_AGENTS)]
 
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": ua,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
                "Referer": "https://www.dhlottery.co.kr/gameResult.do?method=byWin",
                "Connection": "keep-alive",
            }
        )
 
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read().decode("utf-8", errors="replace")
 
        # HTML 응답 감지 (서버 차단)
        stripped = raw.lstrip()
        if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html") or "<html" in raw[:200].lower():
            print(f"  [BLOCKED] {round_num}회차 — HTML 응답 (UA: {ua[:40]}...)")
            return "HTML_BLOCKED"
 
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
 
    except json.JSONDecodeError as e:
        print(f"  [ERROR] {round_num}회차 JSON 파싱 실패: {e}")
        return "PARSE_ERROR"
 
    except urllib.error.HTTPError as e:
        print(f"  [ERROR] {round_num}회차 HTTP 오류: {e.code} {e.reason}")
        return "FETCH_ERROR"
 
    except Exception as e:
        print(f"  [ERROR] {round_num}회차 fetch 실패: {type(e).__name__}: {e}")
        return "FETCH_ERROR"
 
 
def fetch_round_with_retry(round_num: int):
    """재시도 + UA 순환으로 회차 조회"""
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            wait = RETRY_DELAY * attempt
            print(f"  [RETRY] {attempt}번째 재시도 ({wait}초 대기)...")
            time.sleep(wait)
 
        result = fetch_round(round_num, ua_index=attempt)
 
        if result is None:
            return None  # 해당 회차 없음 - 재시도 불필요
 
        if isinstance(result, dict):
            return result  # 성공
 
        # 오류 (HTML_BLOCKED, FETCH_ERROR, PARSE_ERROR)
        print(f"  [WARN] {round_num}회차 시도 {attempt + 1}/{MAX_RETRIES} 실패: {result}")
 
    print(f"  [FAIL] {round_num}회차 — {MAX_RETRIES}번 모두 실패. 건너뜀")
    return "FAILED"
 
 
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
        print("[INFO] 기존 JSON 파일 없음. 새로 생성")
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
 
    # ── 새 회차 추가 ──
    check_round = latest_round + 1
    added = 0
    consecutive_failures = 0
 
    while True:
        print(f"[INFO] {check_round}회차 확인 중...")
        result = fetch_round_with_retry(check_round)
 
        if result is None:
            # 해당 회차 데이터 없음 = 아직 추첨 안 됐거나 없는 회차
            print(f"[INFO] {check_round}회차 없음 — 종료")
            break
 
        if result == "FAILED":
            # 재시도 모두 실패 = 서버 문제, 이 회차 건너뜀
            consecutive_failures += 1
            print(f"[WARN] {check_round}회차 건너뜀 (연속 실패: {consecutive_failures})")
 
            if consecutive_failures >= 2:
                print("[WARN] 연속 2회 실패 — 루프 종료")
                break
 
            check_round += 1
            continue
 
        # 성공
        consecutive_failures = 0
        print(f"[ADD] {check_round}회차 추가: {result['nums']} 보너스 {result['bonus']} 날짜: {result['date']}")
        history_map[check_round] = result
        check_round += 1
        added += 1
 
        # 연속 회차 조회 시 짧은 딜레이 (서버 부하 방지)
        time.sleep(1)
 
    # ── 저장 ──
    final_history = sorted(history_map.values(), key=lambda x: x["round"])
    save_history(JSON_FILE, final_history)
 
    last_round = final_history[-1]["round"] if final_history else "없음"
    print(f"[DONE] 저장 완료 / 추가: {added}회차 / 최신: {last_round}회차")
 
    if added == 0:
        print("[INFO] 추가된 회차 없음 (이미 최신 또는 API 미업데이트)")
 
 
if __name__ == "__main__":
    main()
