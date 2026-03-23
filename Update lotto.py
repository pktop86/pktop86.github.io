#!/usr/bin/env python3
"""
update_lotto.py
매주 토요일 21:15 KST (12:15 UTC) GitHub Actions 실행
draw-history-261-latest.js 에 최신 회차 자동 추가
"""
 
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
 
JS_FILE = 'draw-history-261-latest.js'
LOTTO_API = 'https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}'
 
def fetch_round(round_num):
    url = LOTTO_API.format(round_num)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
        if data.get('returnValue') != 'success':
            return None
        nums = sorted([data[f'drwtNo{i}'] for i in range(1, 7)])
        return {
            'round': round_num,
            'nums': nums,
            'bonus': data['bnusNo']
        }
    except Exception as e:
        print(f'  fetch 실패 ({round_num}회): {e}')
        return None
 
def get_latest_round_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    matches = re.findall(r'round:\s*(\d+)', content)
    if not matches:
        return 0
    return max(int(m) for m in matches)
 
def append_round_to_file(filepath, draw):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
 
    nums_str = ', '.join(str(n) for n in draw['nums'])
    new_line = f"  {{ round: {draw['round']}, nums: [{nums_str}], bonus: {draw['bonus']} }},"
 
    # "];" 직전에 삽입
    insert_pos = content.rfind('];')
    if insert_pos == -1:
        print('  "];" 위치를 찾을 수 없음')
        return False
 
    # 마지막 항목의 쉼표 확인 (이미 있으면 그냥 추가)
    before = content[:insert_pos].rstrip()
    new_content = before + '\n' + new_line + '\n' + content[insert_pos:]
 
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True
 
def main():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    print(f'실행 시각 (KST): {now.strftime("%Y-%m-%d %H:%M:%S")}')
 
    latest_in_file = get_latest_round_in_file(JS_FILE)
    print(f'파일 내 최신 회차: {latest_in_file}')
 
    added = 0
    check_round = latest_in_file + 1
 
    while True:
        print(f'  {check_round}회차 확인 중...')
        draw = fetch_round(check_round)
        if draw is None:
            print(f'  {check_round}회차 없음 — 종료')
            break
        if append_round_to_file(JS_FILE, draw):
            print(f'  ✅ {check_round}회차 추가: {draw["nums"]} 보너스 {draw["bonus"]}')
            added += 1
            check_round += 1
        else:
            break
 
    print(f'\n완료: {added}개 회차 추가됨')
    return added
 
if __name__ == '__main__':
    main()