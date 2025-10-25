# BNF Stock Trading System

BNF 매매법을 기반으로 한 주식 종목 선정 및 백테스팅 시스템입니다.

## 목차

- [프로그램 개요](#프로그램-개요)
- [설치](#설치)
- [설정 파일](#설정-파일)
- [bnf_stock_screener3.py](#bnf_stock_screener3py)
- [bnf_stock_back_test.py](#bnf_stock_back_testpy)
- [워크플로우](#워크플로우)

## 프로그램 개요

### bnf_stock_screener3.py
KOSPI 200 종목 중에서 BNF 매매법 기준에 맞는 종목을 선정하는 프로그램입니다.

**선정 기준:**
- MA25 이격율이 -10% 이하 (현재가가 25일 이동평균선보다 10% 이상 낮을 것)
- RSI 과매도 매수 신호 (이전 RSI < 30이고 현재 RSI가 상승 전환)
- MACD가 0보다 클 것

**이격율 계산 공식:**
```
이격율(%) = (현재주가 - MA25) ÷ MA25 × 100
```

**RSI 매수 신호:**
- 이전 RSI < 30 (과매도 상태)
- 현재 RSI > 이전 RSI (상승 전환)
- 즉, 과매도 구간에서 반등 시작하는 시점

**손절/익절 전략:**
- 손절가: 매수가 대비 -3%
- 1차 익절가: MA25 도달 시 (50% 부분 익절)
- 2차 익절가: MA25에서 +5% 이격 시 (잔량 전량 익절)

### bnf_stock_back_test.py
종목 선정 결과를 바탕으로 백테스팅을 수행하는 프로그램입니다.

**백테스팅 기능:**
- 손절/익절 전략 시뮬레이션
- 수익률 계산
- 거래 통계 분석
- 결과 CSV 저장

## 설치

### 필수 패키지 설치

```bash
pip install pykrx pandas requests
```

### 디렉토리 구조

```
bnf_stock/
├── bnf_stock_screener3.py    # 종목 선정 프로그램
├── bnf_stock_back_test.py    # 백테스팅 프로그램
├── config.json               # 설정 파일
├── kospi_200_code.json       # KOSPI 200 종목 코드 캐시
└── data/
    ├── json/                 # 선정 결과 JSON 파일
    └── csv/                  # 백테스팅 결과 CSV 파일
```

## 설정 파일

`config.json` 파일을 생성하여 한국투자증권 API 인증 정보를 저장합니다.

```json
{
  "app_key": "YOUR_APP_KEY",
  "app_secret": "YOUR_APP_SECRET",
  "account": "YOUR_ACCOUNT_NUMBER",
  "mock": false
}
```

**설정 항목:**
- `app_key`: 한국투자증권 앱 키
- `app_secret`: 한국투자증권 앱 시크릿
- `account`: 계좌번호
- `mock`: 모의투자 모드 사용 여부 (true/false)

## bnf_stock_screener3.py

### 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--config` | 설정 파일 경로 (JSON) | - |
| `-k, --app-key` | 한국투자증권 APP KEY | - |
| `-s, --app-secret` | 한국투자증권 APP SECRET | - |
| `-a, --account` | 계좌번호 | - |
| `--mock` | 모의투자 모드 사용 | false |
| `--from` | 시작일 (YYYYMMDD) | - |
| `--to` | 종료일 (YYYYMMDD) | - |
| `--max-stocks` | 분석할 최대 종목 수 | 전체 |
| `--no-cache` | 캐시 파일 사용 안함 | false |
| `--ma25-deviation-max` | MA25 이격율 최댓값 (%) | -10.0 |
| `--rsi-oversold` | RSI 과매도 기준 | 30 |

### 사용 예시

#### 1. 실시간 종목 선정 (설정 파일 사용)

```bash
python bnf_stock_screener3.py --config config.json
```

#### 2. 과거 특정일 분석

```bash
python bnf_stock_screener3.py --config config.json --from 20250115
```

#### 3. 기간 분석

```bash
# 2025년 1월 전체 분석
python bnf_stock_screener3.py --config config.json --from 20250801 --to 20250831
```

#### 4. 이격율 조건 조정

```bash
# 이격율 -15% 이하로 더 엄격하게
python bnf_stock_screener3.py --config config.json --ma25-deviation-max -15

# 이격율 -5% 이하로 완화
python bnf_stock_screener3.py --config config.json --ma25-deviation-max -5
```

#### 5. RSI 조건 조정

```bash
# RSI 25 미만 (더 강한 과매도)
python bnf_stock_screener3.py --config config.json --rsi-oversold 25

# RSI 35 미만 (완화)
python bnf_stock_screener3.py --config config.json --rsi-oversold 35
```

#### 6. 명령줄에서 직접 인증 정보 입력

```bash
python bnf_stock_screener3.py \
  -k YOUR_APP_KEY \
  -s YOUR_APP_SECRET \
  -a YOUR_ACCOUNT \
  --mock
```

#### 7. 일부 종목만 테스트

```bash
# 처음 50개 종목만 분석
python bnf_stock_screener3.py --config config.json --max-stocks 50
```

### 출력 파일

#### JSON 파일
`data/json/result_YYYYMMDD.json`

```json
{
  "screener_version": 3,
  "trading_date": "20250115",
  "generated_at": "2025-01-15 15:30:00",
  "total_count": 5,
  "criteria": {
    "description": "MA25 이격율 -10% 이하, RSI 과매도, MACD > 0"
  },
  "selected_stocks": [
    {
      "code": "005930",
      "name": "삼성전자",
      "price": 75000,
      "change_pct": 2.5,
      "volume": 15000000,
      "volume_ratio": 1.8,
      "ma25": 85000,
      "price_above_ma25_pct": -11.76,
      "rsi": 28.5,
      "macd": 0.5,
      "trading_strategy": { ... }
    }
  ]
}
```

#### CSV 파일
`data/csv/result_YYYYMMDD.csv`

엑셀에서 열어서 확인 가능한 형식으로 저장됩니다.

## bnf_stock_back_test.py

### 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--config` | 설정 파일 경로 (JSON) | - |
| `--from` | 백테스팅 시작일 (YYYYMMDD) | **필수** |
| `--to` | 백테스팅 종료일 (YYYYMMDD) | **필수** |
| `--tp1-ratio` | 1차 익절 비율 (%) | 50.0 |
| `--tp2-ratio` | 2차 익절 비율 (%) | 50.0 |

### 사용 예시

#### 1. 기본 백테스팅

```bash
python bnf_stock_back_test.py --from 20250101 --to 20250131
```

#### 2. 익절 비율 조정

```bash
# 1차 익절 20%, 2차 익절 80%
python bnf_stock_back_test.py --from 20250101 --to 20250131 --tp1-ratio 20 --tp2-ratio 80

# 1차 익절 30%, 2차 익절 70%
python bnf_stock_back_test.py --from 20250101 --to 20250131 --tp1-ratio 30 --tp2-ratio 70
```

#### 3. 설정 파일과 함께 사용

```bash
python bnf_stock_back_test.py --config config.json --from 20250101 --to 20250131
```

### 백테스팅 로직

1. **진입**: 선정된 종목의 익일 시가에 매수
2. **손절**: 종가가 손절가(매수가 대비 -3%) 이하로 떨어지면 전량 손절
3. **1차 익절**: 종가가 MA25 도달 시 설정 비율만큼 익절 (기본 50%)
4. **2차 익절**: 종가가 MA25 +5% 이격 도달 시 잔량 전량 익절 (기본 50%)
5. **홀딩 기간**: 최대 30일간 보유

**손절/익절 조건 상세:**
- 손절가 = 매수가 × 0.97 (매수가 대비 -3%)
- 1차 익절가 = MA25 (25일 이동평균선)
- 2차 익절가 = MA25 × 1.05 (MA25에서 +5%)

### 출력 파일

#### CSV 파일
`data/csv/backtest_result_YYYYMMDD_YYYYMMDD.csv`

백테스팅 결과가 CSV 파일로 저장되며, 각 거래의 상세 정보를 포함합니다:

| 컬럼 | 설명 |
|------|------|
| trading_date | 종목 선정일 |
| stock_code | 종목 코드 |
| stock_name | 종목명 |
| entry_date | 진입일 (매수일) |
| entry_price | 진입가 (매수가) |
| exit_date | 청산일 (매도일) |
| exit_price | 청산가 (매도가) |
| exit_reason | 청산 사유 (손절/1차익절/2차익절/기간만료) |
| return_pct | 수익률 (%) |
| holding_days | 보유 일수 |

### 백테스팅 결과 예시

```
================================================================
백테스팅 결과 요약
================================================================

총 거래 수: 150
승률: 62.0%
평균 수익률: 3.45%
최대 수익: 15.2%
최대 손실: -5.0%

청산 사유별 통계:
  1차 익절: 45건 (30.0%)
  2차 익절: 48건 (32.0%)
  손절: 42건 (28.0%)
  기간 만료: 15건 (10.0%)

================================================================
```

## 워크플로우

### 1. 종목 선정 및 백테스팅 전체 프로세스

```bash
# Step 1: 과거 기간 동안 종목 선정
python bnf_stock_screener3.py --config config.json --from 20240101 --to 20241231

# Step 2: 백테스팅 수행
python bnf_stock_back_test.py --from 20240101 --to 20241231

# Step 3: 결과 확인
# data/csv/backtest_result_20240101_20241231.csv 파일 확인
```

### 2. 조건을 변경하며 최적화

```bash
# 이격율 -15%로 더 엄격한 조건
python bnf_stock_screener3.py \
  --config config.json \
  --from 20240101 --to 20241231 \
  --ma25-deviation-max -15

python bnf_stock_back_test.py --from 20240101 --to 20241231

# 이격율 -5%로 완화된 조건
python bnf_stock_screener3.py \
  --config config.json \
  --from 20240101 --to 20241231 \
  --ma25-deviation-max -5

python bnf_stock_back_test.py --from 20240101 --to 20241231
```

### 3. 실전 투자 준비

```bash
# 오늘 종목 선정
python bnf_stock_screener3.py --config config.json

# 결과 확인
cat data/json/result_$(date +%Y%m%d).json
```

## 주의사항

1. **API 호출 제한**: 한국투자증권 API는 호출 횟수 제한이 있으므로, 과도한 요청을 피해야 합니다.

2. **거래일 확인**: 주말이나 공휴일에는 데이터가 없으므로, 거래일만 분석됩니다.

3. **백테스팅 한계**:
   - 과거 데이터 기반이므로 미래 수익을 보장하지 않습니다
   - 슬리피지(체결 가격 차이)는 고려되지 않습니다
   - 수수료는 계산에 포함되지 않습니다

4. **실전 투자 시**:
   - 충분한 백테스팅을 통해 전략을 검증하세요
   - 리스크 관리를 철저히 하세요
   - 손절가는 반드시 지키세요

## 라이선스

이 프로젝트는 개인 투자 참고용으로 제작되었습니다. 투자 결과에 대한 책임은 본인에게 있습니다.

## 문의

이슈나 개선사항이 있으면 GitHub Issues를 통해 제보해주세요.
