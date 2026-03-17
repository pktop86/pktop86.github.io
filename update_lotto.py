#!/usr/bin/env python3
import requests
import json
import re
import sys
from pathlib import Path

LOTTO_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
INDEX_FILE = "index.html"


def fetch_lotto_api(drw_no: int):
    url = LOTTO_API.format(drw_no)
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()

        if not data or data.get("returnValue") != "success":
            print(f"  {drw_no}회차 데이터 없음")
            return None

        nums = [data.get(f"drwtNo{i}") for i in range(1, 7)]
        bonus = data.get("bnusNo")
        date = data.get("drwNoDate", "")

        if any(n is None for n in nums) or bonus is None:
            print(f"  {drw_no}회차 번호 파싱 실패")
            return None

        nums = [int(n) for n in nums]
        bonus = int(bonus)

        if len(nums) != 6 or not all(1 <= n <= 45 for n in nums) or not (1 <= bonus <= 45):
            print(f"  {drw_no}회차 번호 검증 실패: nums={nums}, bonus={bonus}")
            return None

        print(f"  ✅ {drw_no}회차 성공: {nums} 보너스:{bonus}")
        return {
            "round": drw_no,
            "nums": nums,
            "bonus": bonus,
            "date": date
        }

    except Exception as e:
        print(f"  [오류] {type(e).__name__}: {e}")
        return None


def read_index_file():
    path = Path(INDEX_FILE)
    if not path.exists():
        raise FileNotFoundError(f"{INDEX_FILE} 파일이 없습니다.")
    return path.read_text(encoding="utf-8")


def write_index_file(content: str):
    Path(INDEX_FILE).write_text(content, encoding="utf-8")


def parse_latest_round(content: str) -> int:
    m = re.search(r'let\s+latestRound\s*=\s*(\d+)', content)
    if not m:
        raise RuntimeError("index.html 안에서 'let latestRound = 숫자' 패턴을 찾지 못했습니다.")
    return int(m.group(1))


def parse_seed_history(content: str):
    sh_match = re.search(r'const\s+SEED_HISTORY\s*=\s*\[(.*?)\];', content, re.DOTALL)
    if not sh_match:
        raise RuntimeError("index.html 안에서 SEED_HISTORY 배열을 찾지 못했습니다.")

    block = sh_match.group(1)
    existing = []

    for m in re.finditer(
        r'\{round\s*:\s*(\d+)\s*,\s*nums\s*:\s*\[([^\]]+)\]\s*,\s*bonus\s*:\s*(\d+)\s*\}',
        block
    ):
        round_no = int(m.group(1))
        nums = [int(x.strip()) for x in m.group(2).split(",") if x.strip()]
        bonus = int(m.group(3))
        existing.append({
            "round": round_no,
            "nums": nums,
            "bonus": bonus
        })

    return existing


def build_seed_history_block(items):
    lines = []
    for e in items:
        nums_text = ",".join(map(str, e["nums"]))
        lines.append(f"  {{round:{e['round']},nums:[{nums_text}],bonus:{e['bonus']}}}")
    return "const SEED_HISTORY = [\n" + ",\n".join(lines) + "\n];"


def update_index_content(content: str, lotto_data: dict) -> str:
    existing = parse_seed_history(content)

    # 중복 회차 제거 후 새 회차 추가
    existing = [x for x in existing if x["round"] != lotto_data["round"]]
    existing.append({
        "round": lotto_data["round"],
        "nums": lotto_data["nums"],
        "bonus": lotto_data["bonus"]
    })

    # 회차순 정렬 후 최근 5개만 유지
    existing = sorted(existing, key=lambda x: x["round"])[-5:]

    new_sh = build_seed_history_block(existing)

    content = re.sub(
        r'const\s+SEED_HISTORY\s*=\s*\[.*?\];',
        new_sh,
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'let\s+latestRound\s*=\s*\d+',
        f'let latestRound = {lotto_data["round"]}',
        content
    )

    content = re.sub(
        r'let\s+latestWinNums\s*=\s*\[[^\]]*\]',
        f'let latestWinNums = {json.dumps(lotto_data["nums"], ensure_ascii=False)}',
        content
    )

    content = re.sub(
        r'let\s+latestBonusNum\s*=\s*\d+',
        f'let latestBonusNum = {lotto_data["bonus"]}',
        content
    )

    return content


def main():
    print("=== update_lotto.py 시작 ===")

    try:
        content = read_index_file()
        current = parse_latest_round(content)
    except Exception as e:
        print(f"❌ index.html 파싱 실패: {e}")
        sys.exit(1)

    target = current + 1
    print(f"현재 latestRound: {current}, 다음 회차 {target} 조회 시도...")

    lotto_data = fetch_lotto_api(target)

    if not lotto_data:
        print("최신 회차입니다. 업데이트할 내용 없음.")
        return

    try:
        new_content = update_index_content(content, lotto_data)
        write_index_file(new_content)
    except Exception as e:
        print(f"❌ index.html 업데이트 실패: {e}")
        sys.exit(1)

    print(f"\n✅ 완료! latestRound:{lotto_data['round']} nums:{lotto_data['nums']} bonus:{lotto_data['bonus']}")


if __name__ == '__main__':
    main()
