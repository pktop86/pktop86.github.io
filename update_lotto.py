#!/usr/bin/env python3
import requests, json, re, sys, time
from bs4 import BeautifulSoup
 
def fetch_lotto_naver(drwNo):
    url = f"https://search.naver.com/search.naver?query={drwNo}회+로또"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
 
        win_ball = soup.select_one('.win_ball')
        if not win_ball:
            print(f"  win_ball 없음")
            return None
 
        # 텍스트에서 숫자만 추출
        numbers = [int(n) for n in win_ball.text.split() if n.isdigit()]
        print(f"  win_ball 숫자: {numbers}")
 
        if len(numbers) < 7:
            print(f"  숫자 부족: {len(numbers)}개")
            return None
 
        # 검증: 실제 로또 번호 범위(1~45) 확인
        valid = [n for n in numbers if 1 <= n <= 45]
        if len(valid) < 7:
            print(f"  유효 번호 부족: {valid}")
            return None
 
        nums = valid[:6]
        bonus = valid[6]
 
        # 추가 검증: 번호가 실제로 해당 회차 번호인지
        # 네이버에서 해당 회차 텍스트가 실제로 있는지 확인
        page_text = soup.get_text()
        if str(drwNo) + '회' not in page_text and str(drwNo) + ' 회' not in page_text:
            print(f"  [경고] {drwNo}회 텍스트 없음 - 잘못된 결과일 수 있음")
            # 그래도 데이터가 있으면 반환 (단 로그 남김)
 
        print(f"  ✅ {drwNo}회차 성공: {nums} 보너스:{bonus}")
        return {'round': drwNo, 'nums': nums, 'bonus': bonus, 'date': ''}
 
    except Exception as e:
        print(f"  [오류] {type(e).__name__}: {e}")
        return None
 
def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
 
    m = re.search(r'let latestRound\s*=\s*(\d+)', content)
    current = int(m.group(1))
    target = current + 1
    print(f"현재 latestRound: {current}, {target}회차 조회 시도...")
 
    # 단일 회차만 조회 (루프 없음 - 제미나이 권고)
    d = fetch_lotto_naver(target)
 
    if not d:
        print("최신 회차입니다. 업데이트할 내용 없음.")
        return
 
    # SEED_HISTORY 업데이트
    sh_match = re.search(r'const SEED_HISTORY = \[(.*?)\];', content, re.DOTALL)
    existing = []
    for m2 in re.finditer(r'\{round:(\d+),nums:\[([^\]]+)\],bonus:(\d+)\}', sh_match.group(1)):
        existing.append({'round':int(m2.group(1)),'nums':list(map(int,m2.group(2).split(','))),'bonus':int(m2.group(3))})
    existing.append({'round':d['round'],'nums':d['nums'],'bonus':d['bonus']})
    existing = sorted(existing, key=lambda x: x['round'])[-5:]
    lines = [f"  {{round:{e['round']},nums:[{','.join(map(str,e['nums']))}],bonus:{e['bonus']}}}" for e in existing]
    new_sh = 'const SEED_HISTORY = [\n' + ',\n'.join(lines) + ',\n];'
 
    content = re.sub(r'const SEED_HISTORY = \[.*?\];', new_sh, content, flags=re.DOTALL)
    content = re.sub(r'let latestRound\s*=\s*\d+', f'let latestRound = {d["round"]}', content)
    content = re.sub(r'let latestWinNums\s*=\s*\[[^\]]*\]', f'let latestWinNums = {json.dumps(d["nums"])}', content)
    content = re.sub(r'let latestBonusNum\s*=\s*\d+', f'let latestBonusNum = {d["bonus"]}', content)
 
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ 완료! latestRound:{d['round']} nums:{d['nums']} bonus:{d['bonus']}")
 
if __name__ == '__main__':
    main()
