import csv

# CSV 파일 읽기
with open('data/json/kospi200/2025/result/momentum_trend_20240101_20241231.csv', 'r', encoding='utf-8-sig') as f:
    # 헤더 건너뛰기 (처음 5줄)
    for _ in range(5):
        next(f)
    
    reader = csv.DictReader(f)
    rows = list(reader)

print(f'\n{"="*60}')
print(f'백테스팅 상세 분석')
print(f'{"="*60}')

# 청산 사유별 분류
take_profit = [r for r in rows if r.get('백테스트_청산사유') == 'take_profit']
stop_loss = [r for r in rows if r.get('백테스트_청산사유') == 'stop_loss']
holding = [r for r in rows if r.get('백테스트_청산사유') == 'holding']

print(f'\n총 {len(rows)}개 종목')
print(f'익절: {len(take_profit)}개')
print(f'손절: {len(stop_loss)}개')
print(f'홀딩: {len(holding)}개')

# 익절 종목 상세
if take_profit:
    print(f'\n{"="*60}')
    print(f'익절 성공 종목 ({len(take_profit)}개)')
    print(f'{"="*60}')
    for r in take_profit[:10]:
        print(f'  {r["종목명"]:12s} | 익절률: {r["익절률(%)"]:>6s}% | 실제: {r["백테스트_수익률(%)"]:>6s}%')

# 손절가/익절가 비율 분석
print(f'\n{"="*60}')
print(f'손절가/익절가 설정 분석')
print(f'{"="*60}')

stop_loss_pcts = [abs(float(r['손절률(%)'])) for r in rows if r.get('손절률(%)')]
take_profit_pcts = [float(r['익절률(%)']) for r in rows if r.get('익절률(%)')]

avg_stop_loss = sum(stop_loss_pcts) / len(stop_loss_pcts) if stop_loss_pcts else 0
avg_take_profit = sum(take_profit_pcts) / len(take_profit_pcts) if take_profit_pcts else 0

print(f'평균 손절률: {avg_stop_loss:.2f}%')
print(f'평균 익절률: {avg_take_profit:.2f}%')
print(f'손익비: 1 : {avg_take_profit/avg_stop_loss:.2f}')

# 손절 종목 분석
if stop_loss:
    losses = [float(r['백테스트_수익률(%)']) for r in stop_loss]
    print(f'\n손절 종목 평균 손실: {sum(losses)/len(losses):.2f}%')

# 홀딩 종목 분석
if holding:
    holdings = [float(r['백테스트_수익률(%)']) for r in holding]
    print(f'홀딩 종목 평균 수익: {sum(holdings)/len(holdings):.2f}%')
    
    # 홀딩 종목 중 수익/손실 분포
    profit_holding = [h for h in holdings if h > 0]
    loss_holding = [h for h in holdings if h < 0]
    print(f'  - 수익 중: {len(profit_holding)}개 (평균 +{sum(profit_holding)/len(profit_holding):.2f}%)')
    print(f'  - 손실 중: {len(loss_holding)}개 (평균 {sum(loss_holding)/len(loss_holding):.2f}%)')

# 홀딩 종목이 손절가에 얼마나 가까운지
print(f'\n{"="*60}')
print(f'홀딩 종목의 위험도 분석')
print(f'{"="*60}')

near_stop_loss = 0
for r in holding:
    profit = float(r['백테스트_수익률(%)'])
    stop_pct = float(r['손절률(%)'])
    
    # 손절가의 50% 이내에 있으면 위험
    if profit < stop_pct * 0.5:
        near_stop_loss += 1

print(f'손절 위험 종목 (손절가 50% 이내): {near_stop_loss}개 / {len(holding)}개')

