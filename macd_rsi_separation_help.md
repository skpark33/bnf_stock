# MACD, RSI, 이격도 골든 크로스 종목 선별 프로그램 사용 가이드

`macd_rsi_separation.py`는 KOSPI 200 종목 데이터를 분석하여 MACD, RSI, 장단기 이격도 골든 크로스가 모두 발생한 종목을 찾아내는 프로그램입니다.

---

## 📋 목차

- [개요](#개요)
- [선별 기준](#선별-기준)
- [사용법](#사용법)
- [출력 파일 구조](#출력-파일-구조)
- [사용 예시](#사용-예시)
- [데이터 활용](#데이터-활용)
- [문제 해결](#문제-해결)

---

## 개요

### 프로그램 목적
여러 기술적 지표의 골든 크로스가 순차적으로 발생한 강한 매수 신호 종목을 찾아냅니다.

### 주요 특징
- ✅ 3단계 필터링을 통한 엄격한 종목 선별
- ✅ 골든 크로스 발생 날짜 및 지표 값 제공
- ✅ 진입가, 손절가, 익절가 자동 계산
- ✅ 백테스팅으로 실제 수익률 검증 가능
- ✅ JSON 형식으로 결과 저장

---

## 선별 기준

### 🔍 3단계 필터링 프로세스

```
KOSPI 200 전체 종목 (약 200개)
    ↓
[1단계] MACD 골든 크로스 발생
    ↓
[2단계] MACD 이전 10일 이내 RSI 골든 크로스 발생
    ↓
[3단계] 최근 20일 이내 5일선이 20일선 상향 돌파
    ↓
최종 선택 종목
```

### 📊 기술적 지표 상세

#### 1단계: MACD 골든 크로스
- **MACD Line**: 12일 EMA - 26일 EMA
- **Signal Line**: MACD의 9일 EMA
- **골든 크로스**: MACD Line이 Signal Line을 아래에서 위로 돌파

**의미**: 단기 모멘텀이 강해지기 시작

#### 2단계: RSI 골든 크로스 (MACD 이전 10일 이내)
- **RSI**: 14일 RSI
- **RSI Signal**: RSI의 9일 EMA
- **골든 크로스**: RSI가 RSI Signal을 아래에서 위로 돌파
- **조건**: MACD 골든 크로스 발생 10일 전까지 RSI 골든 크로스가 선행되어야 함

**의미**: MACD 골든 크로스 전에 이미 과매도 구간에서 반등 신호 발생

#### 3단계: 장단기 이격도 골든 크로스 (MACD 이전 10일 이내)
- **MA5**: 5일 이동평균선
- **MA20**: 20일 이동평균선
- **골든 크로스**: MA5가 MA20을 아래에서 위로 돌파
- **조건**: MACD 골든 크로스 발생 10일 전까지 MA 골든 크로스가 선행되어야 함

**의미**: MACD 골든 크로스 전에 이미 단기 추세가 중기 추세를 상향 돌파하여 상승 추세 전환 신호가 있었음

---

## 사용법

### 기본 사용법

```bash
python macd_rsi_separation.py --config config.json [--from YYYYMMDD] [--to YYYYMMDD] [--backtest]
```

### 명령줄 옵션

| 옵션 | 필수 | 설명 | 기본값 |
|------|------|------|--------|
| `--config` | ✅ | 설정 파일 경로 | - |
| `--from` | ❌ | 분석 시작일 (YYYYMMDD) | 어제 |
| `--to` | ❌ | 분석 종료일 (YYYYMMDD) | 어제 |
| `--backtest` | ❌ | 백테스팅 모드 (--from, --to 필수) | - |
| `--low_period` | ❌ | 전저점 계산 기간 (일) | 12 |
| `--silent` | ❌ | 간략 출력 모드 (최종 결과만 표시) | - |

### 사전 요구사항

#### 1. 데이터 수집
먼저 `get_data.py`로 데이터를 수집해야 합니다:

```bash
# 최근 3개월 데이터 수집
python get_data.py --config config.json --from 20241115 --to 20250114
```

> ⚠️ **중요**: 기술적 지표 계산을 위해 분석 기간보다 최소 60일 이상의 데이터가 필요합니다.

#### 2. 설정 파일 (`config.json`)
```json
{
  "app_key": "YOUR_APP_KEY",
  "app_secret": "YOUR_APP_SECRET",
  "account": "YOUR_ACCOUNT_NUMBER",
  "mock": false
}
```

---

## 출력 파일 구조

### 📁 파일 위치
```
data/json/kospi200/[연도]/result/macd_rsi_separation_[from]_[to].json
```

> 💡 연도는 종료 날짜(--to) 기준으로 자동 결정됩니다.

예시:
```
data/json/kospi200/2025/result/macd_rsi_separation_20250101_20250131.json
data/json/kospi200/2024/result/macd_rsi_separation_20241201_20241231.json
```

### JSON 구조

```json
{
  "analysis_period": {
    "start_date": "20250101",
    "end_date": "20250131"
  },
  "generated_at": "2025-01-15 16:30:00",
  "total_selected": 3,
  "selected_stocks": [
    {
      "code": "005930",
      "name": "삼성전자",
      "macd_golden_cross_date": "20250115",
      "macd_golden_cross_index": 45,
      "macd_value": 1250.5,
      "macd_signal": 1240.2,
      "rsi_golden_cross_date": "20250110",
      "rsi_golden_cross_index": 40,
      "rsi_value": 42.3,
      "rsi_signal": 41.8,
      "ma_golden_cross_date": "20250120",
      "ma_golden_cross_index": 50,
      "ma5_value": 70500,
      "ma20_value": 70000,
      "entry_price": 70000,
      "current_price": 71000,
      "profit_rate": 1.43,
      "current_separation_rate": 1.43,
      "stop_loss": 67000,
      "stop_loss_pct": -4.29,
      "take_profit": 76000,
      "take_profit_pct": 8.57,
      "risk_reward_ratio": 2.0,
      "support_low": 67000,
      "backtest": {
        "buy_date": "20250116",
        "buy_price": 70500,
        "sell_date": "20250125",
        "sell_price": 76000,
        "sell_reason": "익절",
        "profit_rate": 7.80,
        "days_held": 7
      }
    }
  ]
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `analysis_period` | object | 분석 기간 |
| `generated_at` | string | 분석 실행 시각 |
| `total_selected` | number | 선택된 종목 수 |
| `selected_stocks` | array | 선택된 종목 목록 |

#### 종목 필드 (`selected_stocks[]`)

| 필드 | 타입 | 설명 |
|------|------|------|
| `code` | string | 종목 코드 |
| `name` | string | 종목명 |
| `macd_golden_cross_date` | string | MACD 골든 크로스 발생일 |
| `macd_value` | number | MACD 값 |
| `macd_signal` | number | MACD Signal 값 |
| `rsi_golden_cross_date` | string | RSI 골든 크로스 발생일 |
| `rsi_value` | number | RSI 값 |
| `rsi_signal` | number | RSI Signal 값 |
| `ma_golden_cross_date` | string | 이격도 골든 크로스 발생일 |
| `ma5_value` | number | 5일 이동평균 |
| `ma20_value` | number | 20일 이동평균 |
| `entry_price` | number | 진입가 (MACD 골든 크로스 발생일 종가) |
| `current_price` | number | 현재가 (분석 종료일 종가) |
| `profit_rate` | number | 수익률 (진입가 대비 현재가, %) |
| `current_separation_rate` | number | 현재 이격도 (%) |
| `stop_loss` | number | 손절 추천가 (원, 진입가 기준) |
| `stop_loss_pct` | number | 손절률 (%, 진입가 기준) |
| `take_profit` | number | 익절 추천가 (원, 진입가 기준) |
| `take_profit_pct` | number | 익절률 (%, 진입가 기준) |
| `risk_reward_ratio` | number | 손익비 (고정 2.0) |
| `support_low` | number | MACD 발생일 기준 이전 N일 최저가 (원, N=--low_period) |
| `backtest` | object | 백테스팅 결과 (--backtest 옵션 사용 시에만 포함) |

#### 백테스팅 필드 (`backtest`, --backtest 옵션 시에만)

| 필드 | 타입 | 설명 |
|------|------|------|
| `buy_date` | string | 매수일 (MACD 골든 크로스 다음날) |
| `buy_price` | number | 매수가 (매수일 시가) |
| `sell_date` | string | 매도일 (손절/익절 도달일 또는 종료일) |
| `sell_price` | number | 매도가 (손절가/익절가 또는 종료일 종가) |
| `sell_reason` | string | 매도 사유 ("익절", "손절", "홀딩") |
| `profit_rate` | number | 실제 수익률 (매수가 대비 매도가, %) |
| `days_held` | number | 보유 일수 |

---

## 사용 예시

### 1️⃣ 어제 (마지막 거래일) 분석 (기본)

```bash
python macd_rsi_separation.py --config config.json
```

> 💡 `--from`, `--to` 옵션을 생략하면 어제(마지막 거래일)에 MACD 골든 크로스가 발생한 종목만 검색합니다.

**실행 결과:**
```
============================================================
MACD, RSI, 이격도 골든 크로스 종목 선별 프로그램
============================================================
✓ 설정 파일 'config.json' 로드 완료

분석 기간: 20250114 ~ 20250114
데이터 로드 기간: 20241115 ~ 20250114 (기술적 지표 계산용)
MACD 검색 범위: 20250114 (1일)

✓ 로드된 거래일: 60일
  첫 거래일: 20241115
  마지막 거래일: 20250114
  종목 수: 200개

============================================================
1단계: MACD 골든 크로스 종목 검색
============================================================
진행중: 50/200 (25.0%)
진행중: 100/200 (50.0%)
진행중: 150/200 (75.0%)
진행중: 200/200 (100.0%)

✓ MACD 골든 크로스 발견: 15개 종목
  - 삼성전자 (005930): 20250113
  - SK하이닉스 (000660): 20250112
  ... 외 13개 종목

============================================================
2단계: RSI 골든 크로스 종목 검색 (MACD 이전 10일 이내)
============================================================

✓ RSI 골든 크로스 발견: 8개 종목
  - 삼성전자 (005930): RSI GC 20250108, MACD GC 20250113
  - SK하이닉스 (000660): RSI GC 20250107, MACD GC 20250112
  ... 외 6개 종목

============================================================
3단계: 장단기 이격도 골든 크로스 종목 검색 (MACD 이전 10일 이내)
============================================================

✓ 장단기 이격도 골든 크로스 발견: 3개 종목
  - 삼성전자 (005930): MA GC 20250110, 진입가 70,000원 → 현재가 71,000원 (+1.4%), 손절 67,000원 (-4.3%), 익절 76,000원 (+8.6%)
  - SK하이닉스 (000660): MA GC 20250109, 진입가 150,000원 → 현재가 152,000원 (+1.3%), 손절 146,000원 (-2.7%), 익절 158,000원 (+5.3%)
  - LG전자 (066570): MA GC 20250108, 진입가 94,000원 → 현재가 95,000원 (+1.1%), 손절 90,000원 (-4.3%), 익절 102,000원 (+8.5%)

================================================================================
최종 선택 종목: 3개
================================================================================

[골든 크로스 발생 시점]
종목명        코드      MACD GC    RSI GC     MA GC      이격도
--------------------------------------------------------------------
삼성전자      005930   20250113   20250108   20250110      2.15%
SK하이닉스    000660   20250112   20250107   20250109      3.42%
LG전자        066570   20250111   20250106   20250108      1.87%

[매매 전략 (손절/익절)]
종목명            진입가      현재가   수익률      손절가   손절률      익절가   익절률   손익비
---------------------------------------------------------------------------------------------------------
삼성전자        70,000원    71,000원    1.43%    67,000원   -4.29%    76,000원    8.57%  1:2
SK하이닉스     150,000원   152,000원    1.33%   146,000원   -2.67%   158,000원    5.33%  1:2
LG전자          94,000원    95,000원    1.06%    90,000원   -4.26%   102,000원    8.51%  1:2

[통계 정보]
  - 평균 이격도: 2.48%
  - 평균 진입가: 104,667원
  - 평균 현재가: 106,000원
  - 평균 수익률: +1.27%
  - 평균 손절률: -3.74%
  - 평균 익절률: 7.47%

[종목별 상세 정보]

1. 삼성전자 (005930)
   진입가: 70,000원 (MACD GC일) | 현재가: 71,000원 | 수익률: +1.43%
   이격도: +2.15%
   골든 크로스: MA(20250110) → RSI(20250108) → MACD(20250113)
   💔 손절가: 67,000원 (-4.29%) - MACD 발생일 기준 이전 20일 저점
   💰 익절가: 76,000원 (+8.57%) - 손절폭의 2배
   📊 손익비: 1:2

2. SK하이닉스 (000660)
   진입가: 150,000원 (MACD GC일) | 현재가: 152,000원 | 수익률: +1.33%
   이격도: +3.42%
   골든 크로스: MA(20250109) → RSI(20250107) → MACD(20250112)
   💔 손절가: 146,000원 (-2.67%) - MACD 발생일 기준 이전 20일 저점
   💰 익절가: 158,000원 (+5.33%) - 손절폭의 2배
   📊 손익비: 1:2

3. LG전자 (066570)
   진입가: 94,000원 (MACD GC일) | 현재가: 95,000원 | 수익률: +1.06%
   이격도: +1.87%
   골든 크로스: MA(20250108) → RSI(20250106) → MACD(20250111)
   💔 손절가: 90,000원 (-4.26%) - MACD 발생일 기준 이전 20일 저점
   💰 익절가: 102,000원 (+8.51%) - 손절폭의 2배
   📊 손익비: 1:2

============================================================
✓ 결과 저장 완료: data/json/kospi200/2025/result/macd_rsi_separation_20250108_20250115.json
============================================================

✅ 분석 완료!
```

---

### 2️⃣ 특정 기간 분석

```bash
python macd_rsi_separation.py --config config.json --from 20250101 --to 20250131
```

**주의**: 분석 기간보다 최소 60일 이전의 데이터가 필요합니다.

---

### 3️⃣ 백테스팅 (실제 수익률 검증)

```bash
python macd_rsi_separation.py --config config.json --from 20250101 --to 20250131 --backtest
```

> 💡 백테스팅 모드에서는 MACD 골든 크로스 다음날 시가에 매수하고, 손절가/익절가 도달 시 매도하는 시뮬레이션을 실행합니다.

**실행 결과:**
```
================================================================================
백테스팅 실행 중...
================================================================================

✅ 삼성전자 (005930): 20250114(70,500원) → 20250122(76,000원) [익절] +7.80%
❌ SK하이닉스 (000660): 20250113(150,000원) → 20250118(146,000원) [손절] -2.67%
⏳ LG전자 (066570): 20250112(94,000원) → 20250131(95,000원) [홀딩] +1.06%

================================================================================
백테스팅 통계
================================================================================
총 종목: 3개
익절: 1개 (33.3%)
손절: 1개 (33.3%)
홀딩: 1개 (33.3%)
평균 수익률: +2.06%
승률: 33.3%

[백테스팅 결과]
종목명           매수일      매수가      매도일      매도가   결과   수익률  보유일
------------------------------------------------------------------------------------------
삼성전자      20250114    70,500원  20250122    76,000원  ✅익절    +7.80%     6일
SK하이닉스    20250113   150,000원  20250118   146,000원  ❌손절    -2.67%     3일
LG전자        20250112    94,000원  20250131    95,000원  ⏳홀딩    +1.06%    13일
```

**백테스팅 결과 해석:**
- **익절**: 익절가에 도달하여 목표 수익 달성
- **손절**: 손절가에 도달하여 손실 최소화
- **홀딩**: 분석 기간 동안 손절/익절가 미도달, 현재 보유 중

---

### 4️⃣ 전저점 기간 변경

```bash
# 10일 이내 전저점 사용
python macd_rsi_separation.py --config config.json --from 20250101 --to 20250131 --low_period 10

# 30일 이내 전저점 사용
python macd_rsi_separation.py --config config.json --from 20250101 --to 20250131 --low_period 30
```

> 💡 `--low_period`는 손절가 계산 시 MACD 골든 크로스 시점으로부터 과거 몇 일의 저점을 사용할지 지정합니다. 기본값은 12일입니다.

---

### 5️⃣ 간략 출력 모드

```bash
# 최종 종목별 상세 정보만 표시
python macd_rsi_separation.py --config config.json --from 20250101 --to 20250131 --silent

# 백테스팅 + 간략 모드 (종목별 상세 정보 → 백테스팅 통계만)
python macd_rsi_separation.py --config config.json --from 20250101 --to 20250131 --backtest --silent
```

> 💡 `--silent` 옵션 사용 시 중간 단계 출력 없이 최종 결과만 표시됩니다. 백테스팅 모드에서는 종목별 상세 정보를 먼저 표시한 후 백테스팅 통계를 표시합니다.

---

### 6️⃣ 데이터가 없을 때

```bash
python macd_rsi_separation.py --config config.json --from 20250101 --to 20250131
```

**실행 결과:**
```
============================================================
MACD, RSI, 이격도 골든 크로스 종목 선별 프로그램
============================================================
✓ 설정 파일 'config.json' 로드 완료

분석 기간: 20250101 ~ 20250131
데이터 로드 기간: 20241102 ~ 20250131 (기술적 지표 계산용)

❌ 데이터 폴더가 없습니다: data/json/kospi200
   먼저 get_data.py를 실행하여 데이터를 수집하세요:
   python get_data.py --config config.json --from 20241102 --to 20250131
```

---

## 데이터 활용

### Python으로 결과 읽기

```python
import json

# 결과 파일 읽기
with open('data/json/kospi200/2025/result/macd_rsi_separation_20250101_20250131.json', 'r', encoding='utf-8') as f:
    result = json.load(f)

print(f"분석 기간: {result['analysis_period']['start_date']} ~ {result['analysis_period']['end_date']}")
print(f"선택된 종목: {result['total_selected']}개\n")

# 종목별 상세 정보
for stock in result['selected_stocks']:
    print(f"[{stock['name']}] {stock['code']}")
    print(f"  - MACD 골든 크로스: {stock['macd_golden_cross_date']}")
    print(f"  - RSI 골든 크로스: {stock['rsi_golden_cross_date']}")
    print(f"  - MA 골든 크로스: {stock['ma_golden_cross_date']}")
    print(f"  - 진입가: {stock['entry_price']:,}원 (MACD GC일)")
    print(f"  - 현재가: {stock['current_price']:,}원 | 수익률: {stock['profit_rate']:+.2f}%")
    print(f"  - 이격도: {stock['current_separation_rate']}%")
    print(f"  - 손절가: {stock['stop_loss']:,}원 ({stock['stop_loss_pct']:+.2f}%)")
    print(f"  - 익절가: {stock['take_profit']:,}원 ({stock['take_profit_pct']:+.2f}%)")
    print(f"  - 손익비: 1:{stock['risk_reward_ratio']:.0f}")
    
    # 백테스팅 결과 (있는 경우)
    if 'backtest' in stock:
        bt = stock['backtest']
        print(f"  - 백테스트: {bt['buy_date']}({bt['buy_price']:,}원) → "
              f"{bt['sell_date']}({bt['sell_price']:,}원) "
              f"[{bt['sell_reason']}] {bt['profit_rate']:+.2f}% ({bt['days_held']}일)")
    print()
```

### Pandas로 분석

```python
import json
import pandas as pd

# 결과 파일 읽기
with open('data/json/kospi200/2025/result/macd_rsi_separation_20250101_20250131.json', 'r', encoding='utf-8') as f:
    result = json.load(f)

# DataFrame 생성
df = pd.DataFrame(result['selected_stocks'])

# 기본 통계
print("=== 선택 종목 통계 ===")
print(f"종목 수: {len(df)}개")
print(f"평균 진입가: {df['entry_price'].mean():,.0f}원")
print(f"평균 현재가: {df['current_price'].mean():,.0f}원")
print(f"평균 수익률: {df['profit_rate'].mean():+.2f}%")
print(f"평균 이격도: {df['current_separation_rate'].mean():.2f}%")
print(f"평균 손절률: {df['stop_loss_pct'].mean():.2f}%")
print(f"평균 익절률: {df['take_profit_pct'].mean():.2f}%")

# 손익비 분석
print("\n=== 매매 전략 분석 ===")
print(f"평균 손절폭: {(df['entry_price'] - df['stop_loss']).mean():,.0f}원")
print(f"평균 익절폭: {(df['take_profit'] - df['entry_price']).mean():,.0f}원")

# 수익률 순으로 정렬
df_sorted = df.sort_values('profit_rate', ascending=False)
print("\n=== 수익률 상위 종목 ===")
print(df_sorted[['name', 'code', 'entry_price', 'current_price', 'profit_rate', 
                 'stop_loss', 'take_profit']].head(10))

# 손절률이 낮은(안전한) 종목
df_safe = df.sort_values('stop_loss_pct', ascending=False)
print("\n=== 손절률이 낮은(안전한) 종목 ===")
print(df_safe[['name', 'code', 'entry_price', 'stop_loss_pct', 'take_profit_pct']].head(10))

# 날짜 분석
print("\n=== 골든 크로스 발생 날짜 분포 ===")
print(f"MACD 골든 크로스 날짜:")
print(df['macd_golden_cross_date'].value_counts())

# 백테스팅 결과 분석 (backtest 필드가 있는 경우)
if 'backtest' in df.columns:
    # backtest 필드를 펼쳐서 별도 컬럼으로 만들기
    backtest_df = pd.json_normalize(df['backtest'])
    df_with_backtest = pd.concat([df.drop('backtest', axis=1), backtest_df], axis=1)
    
    print("\n=== 백테스팅 통계 ===")
    print(f"총 종목: {len(df_with_backtest)}개")
    print(f"익절: {(df_with_backtest['sell_reason'] == '익절').sum()}개")
    print(f"손절: {(df_with_backtest['sell_reason'] == '손절').sum()}개")
    print(f"홀딩: {(df_with_backtest['sell_reason'] == '홀딩').sum()}개")
    print(f"평균 실제 수익률: {df_with_backtest['profit_rate'].mean():+.2f}%")
    print(f"평균 보유일수: {df_with_backtest['days_held'].mean():.1f}일")
    
    print("\n=== 백테스팅 실제 수익률 상위 종목 ===")
    print(df_with_backtest[['name', 'code', 'buy_date', 'buy_price', 'sell_date', 
                             'sell_price', 'sell_reason', 'profit_rate', 'days_held']]
          .sort_values('profit_rate', ascending=False).head(10))
```

### 여러 기간 결과 비교

```python
import json
import os

def load_all_results():
    """모든 분석 결과 파일 로드"""
    base_dir = 'data/json/kospi200'
    all_results = []
    
    if not os.path.exists(base_dir):
        return []
    
    # 모든 연도 폴더 검색
    for year in sorted(os.listdir(base_dir)):
        year_path = os.path.join(base_dir, year)
        if not os.path.isdir(year_path):
            continue
        
        result_dir = os.path.join(year_path, 'result')
        if not os.path.exists(result_dir):
            continue
        
        for filename in sorted(os.listdir(result_dir)):
            if filename.startswith('macd_rsi_separation_') and filename.endswith('.json'):
                filepath = os.path.join(result_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_results.append({
                        'filename': filename,
                        'year': year,
                        'period': data['analysis_period'],
                        'total': data['total_selected'],
                        'stocks': [s['code'] for s in data['selected_stocks']]
                    })
    
    return all_results

# 모든 결과 로드
results = load_all_results()

# 기간별 선택 종목 수
print("=== 기간별 선택 종목 수 ===")
for r in results:
    print(f"{r['period']['start_date']} ~ {r['period']['end_date']}: {r['total']}개")

# 자주 선택되는 종목 찾기
from collections import Counter

all_codes = []
for r in results:
    all_codes.extend(r['stocks'])

most_common = Counter(all_codes).most_common(10)
print("\n=== 가장 자주 선택된 종목 ===")
for code, count in most_common:
    print(f"{code}: {count}회")
```

---

## 문제 해결

### ❌ "데이터 폴더가 없습니다" 오류

**문제:**
```
❌ 데이터 폴더가 없습니다: data/json/kospi200
   먼저 get_data.py를 실행하여 데이터를 수집하세요:
   python get_data.py --config config.json --from 20241102 --to 20250131
```

**해결 방법:**
먼저 `get_data.py`로 데이터를 수집하세요:
```bash
python get_data.py --config config.json --from 20241102 --to 20250131
```

---

### ❌ 선택된 종목이 없음

**상황:**
```
⚠️  MACD 골든 크로스 종목이 없어 분석을 종료합니다.
```
또는
```
⚠️  RSI 골든 크로스 종목이 없어 분석을 종료합니다.
```
또는
```
⚠️  장단기 이격도 골든 크로스 종목이 없습니다.
```

**의미:**
- 해당 기간에 조건을 만족하는 종목이 없습니다.
- 매우 엄격한 필터링이므로 정상적인 상황입니다.

**해결 방법:**
- 분석 기간을 늘려보세요 (예: 1주일 → 1개월)
- 다른 기간을 분석해보세요

---

### ⚠️ 데이터 부족

**문제:**
기술적 지표 계산을 위한 데이터가 부족합니다.

**필요한 최소 데이터:**
- MACD 계산: 최소 35일 (26일 EMA + 9일 시그널)
- RSI 계산: 최소 15일 (14일 RSI + 1일)
- MA 계산: 최소 20일

**권장 데이터:**
- 분석 기간 + 최소 60일 이전 데이터

**해결 방법:**
더 긴 기간의 데이터를 수집하세요:
```bash
python get_data.py --config config.json --from 20241001 --to 20250131
```

---

### 💡 성능 최적화

**대용량 데이터 처리 시:**

1. **메모리 사용량 줄이기**
   - 한 번에 처리하는 기간을 줄임
   - 월별로 나누어 분석

2. **처리 속도 향상**
   - 진행 상황 표시를 끄려면 코드 수정 필요
   - 병렬 처리는 향후 업데이트 예정

---

## 골든 크로스란?

### 정의
빠른 선(단기 지표)이 느린 선(장기 지표)을 **아래에서 위로 돌파**하는 것

### 시각적 예시
```
        빠른선
           /
          /
         /    ← 골든 크로스 발생
        /
-------/------- 느린선
      /
     /
    /
```

### 의미
- **상승 전환 신호**: 단기 추세가 강해지고 있음
- **매수 신호**: 가격 상승 가능성 증가
- **추세 전환**: 하락 → 상승 또는 횡보 → 상승

### 반대 개념: 데드 크로스
빠른 선이 느린 선을 **위에서 아래로 돌파** (하락 신호)

---

## 프로그램 로직 흐름

```
1. 데이터 로드
   ↓
2. 모든 종목 목록 추출 (KOSPI 200)
   ↓
3. 각 종목별로:
   │
   ├─ [1단계] MACD 계산
   │  └─ MACD 골든 크로스 확인
   │     └─ 발견 시 후보 목록 추가 (MACD GC 시점 저장)
   │
   ├─ [2단계] 1단계 통과 종목만:
   │  └─ RSI 계산
   │     └─ MACD GC 이전 10일 내 RSI 골든 크로스 확인
   │        └─ 발견 시 후보 목록 추가
   │
   └─ [3단계] 2단계 통과 종목만:
      └─ 5일선, 20일선 계산
         └─ MACD GC 이전 10일 내 이격도 골든 크로스 확인
            └─ 발견 시 최종 목록 추가
            └─ 손절가/익절가 계산
   ↓
4. 최종 선택 종목 출력 및 저장

* 중요: 골든 크로스 순서
  MA(5x20) GC → RSI GC → MACD GC
  (모두 10일 이내에 순차적으로 발생)
```

---

## 관련 파일

- `get_data.py` - 데이터 수집 프로그램 (사전 실행 필요)
- `get_data_help.md` - 데이터 수집 프로그램 가이드
- `config.json` - API 설정 파일
- `data/json/kospi200/[연도]/kospi200_data.json` - 입력 데이터 (연도별)
- `data/json/kospi200/[연도]/result/macd_rsi_separation_*.json` - 출력 결과 (연도별)

---

## FAQ

### Q1. 왜 3단계 필터링을 하나요?
**A:** 단일 지표보다 여러 지표가 동시에 매수 신호를 보낼 때 더 강한 신호로 판단할 수 있습니다. 각 단계를 통과할수록 더 확실한 상승 추세 전환 가능성이 높아집니다.

### Q2. 골든 크로스 순서가 왜 중요한가요?
**A:** 이 프로그램은 **MA(5x20) → RSI → MACD** 순서로 골든 크로스가 순차적으로 발생하는 종목을 찾습니다.

**골든 크로스 순서와 의미:**
1. **MA(5x20) 골든 크로스** (가장 먼저)
   - 단기 추세가 중기 추세를 상향 돌파
   - 초기 상승 신호
   
2. **RSI 골든 크로스** (10일 이내)
   - 과매도 구간에서 반등 신호
   - 매수 세력 유입 시작
   
3. **MACD 골든 크로스** (10일 이내)
   - 본격적인 상승 모멘텀 시작
   - 가장 강력한 매수 신호

**이렇게 순차적으로 발생하면**: 바닥에서 서서히 상승 동력을 쌓아온 종목이므로, 상승 추세가 더 강하고 지속 가능성이 높습니다.

### Q3. 진입가란 무엇인가요?
**A:** 진입가는 **MACD 골든 크로스가 발생한 날의 종가**입니다. 이 프로그램은 MACD 골든 크로스를 매수 신호로 보고, 그날 종가에 매수했다고 가정합니다.

**예시:**
- MACD 골든 크로스 발생일: 2025-01-13
- 그날의 종가: 70,000원
- 진입가: 70,000원

### Q4. 손절가는 어떻게 계산되나요?
**A:** 손절가는 **진입가(MACD 발생일) 기준 이전 N일간의 최저가(이전 저점)**로 설정됩니다. 기본값 N=20이며, `--low_period` 옵션으로 변경 가능합니다.

**예시 (--low_period 20):**
- 진입가: 10,000원 (MACD GC일)
- MACD 발생일 기준 이전 20일 최저가: 9,500원
- 손절가: 9,500원 (-5%)

### Q5. 익절가는 어떻게 계산되나요?
**A:** 익절가는 **손절폭의 2배**로 설정됩니다. 이는 손익비 1:2를 유지하여 리스크 대비 수익을 확보하는 전략입니다. 모든 계산은 **진입가 기준**입니다.

**계산 방법:**
1. 손절폭 = 진입가 - 손절가
2. 익절가 = 진입가 + (손절폭 × 2)

**예시:**
- 진입가: 10,000원
- 손절가: 9,500원
- 손절폭: 500원
- 익절가: 10,000 + (500 × 2) = 11,000원 (+10%)

### Q6. 손익비 1:2가 무엇인가요?
**A:** 손익비는 위험(Risk) 대비 보상(Reward)의 비율입니다.

- **손실 가능액**: 500원 (진입가 10,000 → 손절가 9,500)
- **이익 가능액**: 1,000원 (진입가 10,000 → 익절가 11,000)
- **손익비**: 1:2 (500:1,000)

**의미**: 손실보다 이익이 2배 크므로, 승률이 33% 이상만 되어도 장기적으로 수익이 발생합니다.

### Q7. 현재가와 진입가의 차이는?
**A:** 
- **진입가**: MACD 골든 크로스 발생일의 종가 (매수 시점)
- **현재가**: 분석 종료일의 종가 (분석 기준일)
- **수익률**: (현재가 - 진입가) / 진입가 × 100

**예시:**
```
MACD GC 발생: 2025-01-13, 종가 70,000원 (진입가)
분석 종료일: 2025-01-15, 종가 71,000원 (현재가)
수익률: +1.43%
```

**활용:** 이미 진입한 종목의 현재 수익 상태를 파악할 수 있습니다.

### Q8. 선택된 종목을 그대로 매수해도 되나요?
**A:** 아닙니다. 이 프로그램은 참고용 선별 도구일 뿐입니다. 실제 투자는:
- 기업 재무제표 분석
- 시장 상황 파악
- 뉴스 및 이슈 확인
- 개인 리스크 허용도
- 분할 매수 전략
등을 종합적으로 고려해야 합니다.

### Q9. 손절가/익절가를 반드시 지켜야 하나요?
**A:** 권장사항이지만 절대적인 것은 아닙니다:

**손절가 준수를 권장하는 이유:**
- 큰 손실 방지
- 감정적 거래 방지
- 자본 보존

**익절가는 유연하게:**
- 추세가 강하면 일부만 익절하고 나머지 보유
- 분할 익절 전략 활용
- 상황에 따라 조정 가능

### Q10. 얼마나 자주 실행해야 하나요?
**A:** 
- **일일 분석**: 매일 장 마감 후 (15:30 이후)
- **주간 분석**: 매주 금요일
- **필요시**: 특정 기간 분석

### Q11. 과거 데이터로 백테스팅할 수 있나요?
**A:** 네. `--from`, `--to` 옵션으로 과거 기간을 지정하면 해당 시점의 골든 크로스를 찾을 수 있습니다.

**예시:**
```bash
# 2024년 12월 분석
python macd_rsi_separation.py --config config.json --from 20241201 --to 20241231
```

### Q12. 왜 손절폭의 2배가 익절가인가요? 3배는 안 되나요?
**A:** 2배는 일반적으로 권장되는 손익비입니다:

- **1:1** - 너무 보수적, 수수료 고려 시 불리
- **1:2** - 균형 잡힌 비율, 승률 33%만 되어도 수익
- **1:3** - 욕심, 익절 기회를 놓칠 수 있음

더 높은 손익비를 원하면 코드를 수정하거나, 익절을 단계적으로 하는 것을 권장합니다:
- 1차 익절: 손절폭의 1배에서 50% 익절
- 2차 익절: 손절폭의 2배에서 나머지 익절

### Q13. 백테스팅은 무엇인가요?
**A:** 과거 데이터를 기반으로 매매 전략의 실제 성과를 검증하는 기능입니다.

**백테스팅 동작 방식:**
1. MACD 골든 크로스 다음날 시가에 매수
2. 매일 저가가 손절가 이하로 떨어지면 손절가에 매도
3. 매일 고가가 익절가 이상으로 오르면 익절가에 매도
4. 분석 기간 종료까지 둘 다 도달하지 않으면 "홀딩" (현재가로 수익률 계산)

**예시:**
```
MACD GC: 2025-01-13 (진입가 70,000원)
매수: 2025-01-14 시가 70,500원
손절가: 67,000원 / 익절가: 76,000원

2025-01-15: 저가 68,000원, 고가 72,000원 → 유지
2025-01-16: 저가 70,000원, 고가 73,000원 → 유지
2025-01-17: 저가 72,000원, 고가 76,500원 → 익절가 도달! 76,000원에 매도
실제 수익률: (76,000 - 70,500) / 70,500 = +7.80%
```

### Q14. 백테스팅 결과를 어떻게 해석하나요?
**A:** 백테스팅 통계를 통해 전략의 유효성을 판단합니다.

**핵심 지표:**
- **승률**: 익절 비율. 30% 이상이면 양호
- **평균 수익률**: 전체 거래의 평균 수익. 양수면 수익 전략
- **평균 보유일수**: 빠른 회전율(5일 이하)이 좋음

**좋은 백테스팅 결과 예:**
```
승률: 40%
평균 수익률: +3.5%
평균 보유일수: 6일
```

**나쁜 백테스팅 결과 예:**
```
승률: 20%
평균 수익률: -1.2%
평균 보유일수: 15일
```

### Q15. 백테스팅에서 "홀딩"의 의미는?
**A:** 분석 기간 동안 손절가/익절가 어디에도 도달하지 못한 종목입니다.

**의미:**
- **양수 수익**: 상승 추세지만 익절가까지는 도달하지 못함 (보유 추천)
- **음수 수익**: 하락 추세지만 손절가까지는 도달하지 않음 (주의 필요)

**홀딩 비율이 높은 경우:**
- 손절가/익절가 폭이 너무 넓을 수 있음
- 분석 기간이 너무 짧을 수 있음
- 변동성이 낮은 종목일 수 있음

---

**마지막 업데이트:** 2025-01-15  
**버전:** 2.3 (--low_period 기본값 12로 변경)

