import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from pykrx import stock
import json
import os
import warnings
import argparse
import sys
warnings.filterwarnings('ignore')


class KISAPIClient:
    """한국투자증권 API 클라이언트"""

    def __init__(self, app_key, app_secret, account_no, mock=False, use_pykrx_for_historical=False):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.use_pykrx_for_historical = use_pykrx_for_historical

        if mock:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            print("🔧 모의투자 모드")
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
            print("💰 실전투자 모드")

        self.access_token = None

        if not app_key or not app_secret or not account_no:
            raise ValueError("APP_KEY, APP_SECRET, ACCOUNT_NO는 필수입니다.")

        print(f"APP_KEY: {app_key[:10]}..." if len(app_key) > 10 else f"APP_KEY: {app_key}")
        print(f"Base URL: {self.base_url}")

        if use_pykrx_for_historical:
            print("📊 과거 데이터 분석 모드 (pykrx 사용)")

        self._get_access_token()

        if not use_pykrx_for_historical:
            self._check_market_status()

    def _get_access_token(self):
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            res = requests.post(url, headers=headers, json=data)

            if res.status_code != 200:
                print(f"\n❌ 토큰 발급 실패 (HTTP {res.status_code})")
                print(f"응답: {res.text}")
                raise Exception(f"API 응답 오류: {res.status_code}")

            result = res.json()

            if 'access_token' not in result:
                print(f"\n❌ 토큰 발급 실패")
                print(f"응답: {json.dumps(result, indent=2, ensure_ascii=False)}")

                if 'msg1' in result:
                    print(f"오류 메시지: {result['msg1']}")

                raise Exception("access_token을 받지 못했습니다.")

            self.access_token = result['access_token']
            print(f"✓ Access Token 발급 성공")

        except requests.exceptions.RequestException as e:
            print(f"\n❌ 네트워크 오류: {e}")
            raise
        except Exception as e:
            print(f"\n❌ 토큰 발급 중 오류 발생: {e}")
            raise

    def _check_market_status(self):
        """시장 상태 확인"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()

        if weekday >= 5:
            print("\n⚠️  경고: 오늘은 주말입니다.")
            print("   마지막 거래일 데이터를 사용합니다.\n")
            return False

        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()

        if current_time < market_open:
            print(f"\n⚠️  경고: 현재 시각 {now.strftime('%H:%M')} - 장 시작 전입니다.")
            print("   전일 종가 데이터를 사용합니다.\n")
            return False
        elif current_time > market_close:
            print(f"\n⚠️  경고: 현재 시각 {now.strftime('%H:%M')} - 장 마감 후입니다.")
            print("   금일 종가 데이터를 사용합니다.\n")
            return False
        else:
            print(f"\n✓ 현재 시각 {now.strftime('%H:%M')} - 장 운영 중입니다.")
            print("  실시간 데이터를 사용합니다.\n")
            return True

    def get_last_trading_date(self):
        """마지막 거래일 확인"""
        try:
            today = datetime.now()
            for i in range(10):
                check_date = (today - timedelta(days=i)).strftime("%Y%m%d")
                try:
                    df = stock.get_index_ohlcv(check_date, check_date, "1001")
                    if not df.empty:
                        return check_date
                except:
                    continue
            return datetime.now().strftime("%Y%m%d")
        except:
            return datetime.now().strftime("%Y%m%d")

    def _get_headers(self, tr_id):
        """API 호출 헤더 생성"""
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }

    def get_kospi200_stocks(self, use_cache=True, cache_file="kospi_200_code.json"):
        """KOSPI 200 종목 코드 조회 (캐싱 지원)"""
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    print(f"캐시 파일에서 KOSPI 200 종목 {len(cached_data['stocks'])}개 로드 완료")
                    print(f"캐시 생성일: {cached_data['created_at']}")
                    return cached_data['stocks']
            except Exception as e:
                print(f"캐시 파일 읽기 실패: {e}")
                print("새로 종목 코드를 가져옵니다...")

        try:
            stock_codes = stock.get_index_portfolio_deposit_file("1028")

            stocks = []
            for code in stock_codes:
                name = stock.get_market_ticker_name(code)
                stocks.append({
                    'code': code,
                    'name': name
                })

            print(f"KOSPI 200 종목 {len(stocks)}개 로드 완료")

            if use_cache:
                try:
                    cache_data = {
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'stocks': stocks
                    }
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=2)
                    print(f"종목 코드를 '{cache_file}'에 저장했습니다.")
                except Exception as e:
                    print(f"캐시 파일 저장 실패: {e}")

            return stocks
        except Exception as e:
            print(f"KOSPI 200 종목 코드 조회 실패: {e}")
            return []

    def get_current_price(self, stock_code):
        """현재가 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code
        }
        headers = self._get_headers("FHKST01010100")
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def get_daily_price(self, stock_code, days=30):
        """일별 시세 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
            "fid_org_adj_prc": "0",
            "fid_period_div_code": "D"
        }
        headers = self._get_headers("FHKST01010400")
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def get_historical_data_pykrx(self, stock_code, start_date, end_date):
        """pykrx를 이용한 과거 데이터 조회"""
        try:
            df = stock.get_market_ohlcv(start_date, end_date, stock_code)
            if df.empty:
                return None
            return df
        except Exception as e:
            return None


class BNFStockScreener:
    """BNF 매매법 종목 선정 (Screener 3 버전)"""

    def __init__(self, api_client, target_date=None):
        self.api = api_client
        if target_date:
            self.last_trading_date = target_date
            print(f"📅 분석 대상일: {self.last_trading_date[:4]}-{self.last_trading_date[4:6]}-{self.last_trading_date[6:]}\n")
        else:
            self.last_trading_date = api_client.get_last_trading_date()
            print(f"📅 기준 거래일: {self.last_trading_date[:4]}-{self.last_trading_date[4:6]}-{self.last_trading_date[6:]}\n")

    def calculate_moving_average(self, prices, period=25):
        """이동평균 계산"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_ema(self, prices, period):
        """지수이동평균 (EMA) 계산"""
        if len(prices) < period:
            return None

        ema_values = []
        multiplier = 2 / (period + 1)

        # 첫 EMA는 SMA로 시작
        sma = sum(prices[:period]) / period
        ema_values.append(sma)

        # 이후 EMA 계산
        for i in range(period, len(prices)):
            ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)

        return ema_values[-1]

    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """MACD 계산
        Returns: (MACD Line, Signal Line, Histogram)
        """
        if len(prices) < slow:
            return None, None, None

        # EMA 계산을 위한 함수
        def calc_ema_series(data, period):
            ema_values = []
            multiplier = 2 / (period + 1)

            # 첫 EMA는 SMA로 시작
            sma = sum(data[:period]) / period
            ema_values.append(sma)

            # 이후 EMA 계산
            for i in range(period, len(data)):
                ema = (data[i] - ema_values[-1]) * multiplier + ema_values[-1]
                ema_values.append(ema)

            return ema_values

        # 12일 EMA와 26일 EMA 계산
        ema_fast = calc_ema_series(prices, fast)
        ema_slow = calc_ema_series(prices, slow)

        if not ema_fast or not ema_slow or len(ema_fast) < len(ema_slow):
            return None, None, None

        # MACD Line = 12 EMA - 26 EMA
        macd_line_values = [ema_fast[i + (fast - slow)] - ema_slow[i] for i in range(len(ema_slow))]

        if len(macd_line_values) < signal:
            return None, None, None

        # Signal Line = MACD Line의 9일 EMA
        signal_line_values = calc_ema_series(macd_line_values, signal)

        if not signal_line_values:
            return None, None, None

        # 현재 값들 (가장 최근)
        macd_line = macd_line_values[-1]
        signal_line = signal_line_values[-1]
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        if len(prices) < period + 1:
            return None

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, high_prices, low_prices, close_prices, period=14):
        """ATR (Average True Range) 계산"""
        if len(high_prices) < period + 1:
            return None

        true_ranges = []
        for i in range(1, len(high_prices)):
            tr1 = high_prices[i] - low_prices[i]
            tr2 = abs(high_prices[i] - close_prices[i-1])
            tr3 = abs(low_prices[i] - close_prices[i-1])
            true_ranges.append(max(tr1, tr2, tr3))

        if len(true_ranges) < period:
            return None

        atr = sum(true_ranges[-period:]) / period
        return atr

    def calculate_support_resistance(self, high_prices, low_prices, close_prices, period=20):
        """지지선과 저항선 계산"""
        if len(high_prices) < period:
            return None, None

        recent_highs = high_prices[-period:]
        recent_lows = low_prices[-period:]

        resistance = max(recent_highs)
        support = min(recent_lows)

        return support, resistance

    def calculate_trading_strategy(self, current_price, prices, high_prices, low_prices,
                                   ma25, atr, support, resistance):
        """손절가/익절가 전략 계산 (MA25 기준)"""
        strategy = {
            'entry_price': current_price,
            'stop_loss': {},
            'take_profit': [],
            'support_line': support,
            'resistance_line': resistance,
            'atr': atr,
            'ma25': ma25
        }

        # 손절가 계산: 매수가 대비 -3%
        stop_loss_price = current_price * 0.97
        stop_loss_pct = -3.0

        strategy['stop_loss'] = {
            'price': int(stop_loss_price),
            'pct': round(stop_loss_pct, 2),
            'reason': '매수가 대비 -3%'
        }

        # 1차 익절가: MA25 도달 시
        if ma25:
            tp1_price = ma25
            tp1_pct = ((tp1_price - current_price) / current_price) * 100

            strategy['take_profit'].append({
                'level': 1,
                'price': int(tp1_price),
                'pct': round(tp1_pct, 2),
                'reason': 'MA25 도달',
                'action': '50% 부분 익절'
            })

            # 2차 익절가: MA25에서 +5% 이격
            tp2_price = ma25 * 1.05
            tp2_pct = ((tp2_price - current_price) / current_price) * 100

            strategy['take_profit'].append({
                'level': 2,
                'price': int(tp2_price),
                'pct': round(tp2_pct, 2),
                'reason': 'MA25 +5% 이격',
                'action': '잔량 전량 익절'
            })

        # 손익비 계산
        if strategy['stop_loss'] and strategy['take_profit']:
            risk_amount = current_price - strategy['stop_loss']['price']
            reward_amount = strategy['take_profit'][0]['price'] - current_price
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            strategy['risk_reward_ratio'] = round(risk_reward_ratio, 2)

        return strategy

    def screen_stocks(self, stock_codes, criteria, max_stocks=None, save_progress=True, use_historical=False):
        """BNF 기준으로 종목 선정 (Screener 3 버전)"""
        results = []
        total = len(stock_codes)

        if max_stocks:
            stock_codes = stock_codes[:max_stocks]
            total = max_stocks

        print(f"\n총 {total}개 종목 분석 시작...")
        print(f"분석 기준: {self.last_trading_date[:4]}-{self.last_trading_date[4:6]}-{self.last_trading_date[6:]} 거래일 데이터")
        print("-" * 60)

        for idx, stock_info in enumerate(stock_codes, 1):
            try:
                if idx % 10 == 0:
                    print(f"진행중: {idx}/{total} ({idx/total*100:.1f}%)")

                if isinstance(stock_info, dict):
                    stock_code = stock_info['code']
                    stock_name = stock_info['name']
                else:
                    stock_code = stock_info
                    stock_name = None

                if use_historical:
                    time.sleep(0.1)

                    end_date = self.last_trading_date
                    start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=90)).strftime("%Y%m%d")

                    df = self.api.get_historical_data_pykrx(stock_code, start_date, end_date)
                    if df is None or df.empty or len(df) < 30:
                        continue

                    prices = df['종가'].tolist()
                    high_prices = df['고가'].tolist()
                    low_prices = df['저가'].tolist()
                    volumes = df['거래량'].tolist()

                    current_price = prices[-1]
                    prev_price = prices[-2] if len(prices) >= 2 else prices[-1]
                    volume = volumes[-1]

                    if not stock_name:
                        stock_name = stock.get_market_ticker_name(stock_code)

                else:
                    time.sleep(0.05)

                    current_data = self.api.get_current_price(stock_code)
                    if 'output' not in current_data:
                        continue

                    output = current_data['output']
                    current_price = float(output['stck_prpr'])
                    prev_price = float(output['stck_sdpr'])
                    volume = int(output['acml_vol'])

                    api_stock_name = output.get('hts_kor_isnm', '')
                    if not stock_name:
                        stock_name = api_stock_name

                    if current_price == 0 or volume == 0:
                        continue

                    time.sleep(0.05)
                    daily_data = self.api.get_daily_price(stock_code)
                    if 'output' not in daily_data:
                        continue

                    prices = [float(d['stck_clpr']) for d in daily_data['output']]
                    high_prices = [float(d['stck_hgpr']) for d in daily_data['output']]
                    low_prices = [float(d['stck_lwpr']) for d in daily_data['output']]
                    volumes = [int(d['acml_vol']) for d in daily_data['output']]

                    if len(prices) < 30:
                        continue

                # 기술적 지표 계산
                ma25 = self.calculate_moving_average(prices, 25)
                rsi = self.calculate_rsi(prices, 14)
                macd_line, signal_line, macd_hist = self.calculate_macd(prices)
                atr = self.calculate_atr(high_prices, low_prices, prices, 14)
                support, resistance = self.calculate_support_resistance(high_prices, low_prices, prices, 20)

                price_change_pct = ((current_price - prev_price) / prev_price) * 100

                avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else volumes[0]
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0

                # Screener 3 선정 조건 검사
                passed = True

                # 1) MA25 이격율이 -10% 이하일 것 (현재가가 MA25보다 10% 이상 낮을 것)
                if ma25:
                    price_above_ma25_pct = ((current_price - ma25) / ma25) * 100
                    if price_above_ma25_pct > criteria.get('ma25_deviation_max', -10):
                        passed = False
                else:
                    passed = False

                # 2) RSI 값이 과매도 상태 (RSI < 30)
                if rsi:
                    if rsi >= criteria.get('rsi_oversold', 30):
                        passed = False
                else:
                    passed = False

                # 3) MACD 값이 0보다 클 것
                if macd_line is not None:
                    if macd_line <= 0:
                        passed = False
                else:
                    passed = False

                if passed:
                    trading_strategy = self.calculate_trading_strategy(
                        current_price, prices, high_prices, low_prices,
                        ma25, atr, support, resistance
                    )

                    result = {
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'current_price': current_price,
                        'price_change_pct': round(price_change_pct, 2),
                        'volume': volume,
                        'volume_ratio': round(volume_ratio, 2),
                        'ma25': round(ma25, 2) if ma25 else None,
                        'price_above_ma25_pct': round(price_above_ma25_pct, 2) if ma25 else None,
                        'rsi': round(rsi, 2) if rsi else None,
                        'macd': round(macd_line, 2) if macd_line is not None else None,
                        'macd_signal': round(signal_line, 2) if signal_line is not None else None,
                        'macd_hist': round(macd_hist, 2) if macd_hist is not None else None,
                        'atr': round(atr, 2) if atr else None,
                        'trading_strategy': trading_strategy
                    }
                    results.append(result)
                    print(f"✓ 선정: {stock_name} ({stock_code}) - 이격율: {price_above_ma25_pct:.2f}%, RSI: {rsi:.2f}, MACD: {macd_line:.2f}")

            except Exception as e:
                continue

        print(f"\n분석 완료! 총 {len(results)}개 종목 선정됨")

        # MA25 이격율 낮은 순으로 정렬 (음수가 클수록 우선)
        results.sort(key=lambda x: x['price_above_ma25_pct'] if x['price_above_ma25_pct'] is not None else 0, reverse=False)

        if save_progress and results:
            self._save_results(results)

        return results

    def _save_results(self, results):
        """결과를 JSON 파일로 저장"""
        try:
            os.makedirs('data/json', exist_ok=True)
            os.makedirs('data/csv', exist_ok=True)

            json_filename = f"data/json/result_{self.last_trading_date}.json"

            output_data = {
                'screener_version': 3,
                'trading_date': self.last_trading_date,
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_count': len(results),
                'criteria': {
                    'description': 'MA25 이격율 -10% 이하, RSI 과매도, MACD > 0'
                },
                'selected_stocks': []
            }

            for result in results:
                stock_info = {
                    'code': result['stock_code'],
                    'name': result['stock_name'],
                    'price': result['current_price'],
                    'change_pct': result['price_change_pct'],
                    'volume': result['volume'],
                    'volume_ratio': result['volume_ratio'],
                    'ma25': result['ma25'],
                    'price_above_ma25_pct': result['price_above_ma25_pct'],
                    'rsi': result['rsi'],
                    'macd': result['macd'],
                    'macd_signal': result['macd_signal'],
                    'macd_hist': result['macd_hist'],
                    'atr': result['atr'],
                    'trading_strategy': result['trading_strategy']
                }
                output_data['selected_stocks'].append(stock_info)

            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"\nJSON 저장: {json_filename}")

            csv_filename = f"data/csv/result_{self.last_trading_date}.csv"
            df = pd.DataFrame(results)
            df.insert(0, 'trading_date', self.last_trading_date)
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"CSV 저장: {csv_filename}")

        except Exception as e:
            print(f"결과 저장 실패: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='BNF 매매법 종목 선정 프로그램 (Screener 3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  1. 실시간 분석:
     python bnf_stock_screener3.py --config config.json

  2. 과거 특정일 분석:
     python bnf_stock_screener3.py --config config.json --from 20250101

  3. 기간 분석:
     python bnf_stock_screener3.py --config config.json --from 20250101 --to 20250131

Screener 3 선정 기준:
  - MA25 이격율이 -10% 이하 (현재가가 MA25보다 10% 이상 낮을 것)
  - RSI 값이 과매도 상태 (기본값: RSI < 30)
  - MACD 값이 0보다 클 것

  이격율(%) = (현재주가 - MA25) ÷ MA25 × 100
        '''
    )

    parser.add_argument('--config', help='설정 파일 경로 (JSON)')
    parser.add_argument('-k', '--app-key', help='한국투자증권 APP KEY')
    parser.add_argument('-s', '--app-secret', help='한국투자증권 APP SECRET')
    parser.add_argument('-a', '--account', help='계좌번호')
    parser.add_argument('--mock', action='store_true', help='모의투자 모드')
    parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    parser.add_argument('--max-stocks', type=int, default=None, help='분석할 최대 종목 수')
    parser.add_argument('--no-cache', action='store_true', help='캐시 파일 사용 안함')
    parser.add_argument('--ma25-deviation-max', type=float, default=-10.0, help='MA25 이격율 최댓값 %% (기본값: -10%%, 즉 MA25보다 10%% 이상 낮아야 함)')
    parser.add_argument('--rsi-oversold', type=int, default=30, help='RSI 과매도 기준 (기본값: 30)')

    args = parser.parse_args()

    print("=" * 60)
    print("BNF 매매법 종목 선정 프로그램 (Screener 3)")
    print("=" * 60)

    # 날짜 범위 처리
    use_historical = False
    date_list = []

    if args.from_date:
        use_historical = True
        try:
            start = datetime.strptime(args.from_date, "%Y%m%d")
            end = datetime.strptime(args.to_date, "%Y%m%d") if args.to_date else start

            current = start
            while current <= end:
                date_list.append(current.strftime("%Y%m%d"))
                current += timedelta(days=1)

            print(f"\n📅 분석 기간: {args.from_date} ~ {end.strftime('%Y%m%d')}")
            print(f"   총 {len(date_list)}일 분석 예정\n")

        except ValueError:
            print("❌ 날짜 형식이 잘못되었습니다. YYYYMMDD 형식으로 입력해주세요.")
            sys.exit(1)

    # 설정 파일 또는 명령줄 인수 처리
    if args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)

            app_key = config.get('app_key')
            app_secret = config.get('app_secret')
            account = config.get('account')
            mock = config.get('mock', False)

            print(f"✓ 설정 파일 '{args.config}' 로드 완료\n")

        except FileNotFoundError:
            print(f"❌ 설정 파일 '{args.config}'을 찾을 수 없습니다.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"❌ 설정 파일 '{args.config}'의 JSON 형식이 잘못되었습니다.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 설정 파일 읽기 실패: {e}")
            sys.exit(1)
    else:
        app_key = args.app_key
        app_secret = args.app_secret
        account = args.account
        mock = args.mock

        if not app_key or not app_secret or not account:
            print("❌ APP_KEY, APP_SECRET, ACCOUNT는 필수입니다.")
            print("\n설정 파일 사용을 권장합니다:")
            print("  python bnf_stock_screener3.py --config config.json")
            sys.exit(1)

    # API 클라이언트 초기화
    try:
        print(f"\n입력받은 값:")
        print(f"  APP_KEY 길이: {len(app_key)}")
        print(f"  APP_SECRET 길이: {len(app_secret)}")
        print(f"  계좌번호: {account}")
        print(f"  모의투자: {mock}")
        print(f"  과거 데이터 분석: {use_historical}\n")

        api = KISAPIClient(app_key, app_secret, account, mock=mock, use_pykrx_for_historical=use_historical)
    except Exception as e:
        print(f"\n❌ API 초기화 실패: {e}")
        sys.exit(1)

    # 종목 코드 로딩
    print("=" * 60)
    print("KOSPI 200 종목 코드 로딩 중...")
    print("=" * 60)

    kospi200_stocks = api.get_kospi200_stocks(use_cache=not args.no_cache)
    print(f"총 {len(kospi200_stocks)}개 종목 로드 완료\n")

    # 선정 기준 설정 (Screener 3)
    criteria = {
        'ma25_deviation_max': args.ma25_deviation_max,
        'rsi_oversold': args.rsi_oversold
    }

    print("=" * 60)
    print("BNF 매매법 기준 (Screener 3):")
    print(f"  - MA25 이격율: {criteria['ma25_deviation_max']}% 이하")
    print(f"  - RSI: {criteria['rsi_oversold']} 미만 (과매도)")
    print(f"  - MACD: 0보다 큰 값")
    print("=" * 60)

    # 날짜별 분석
    if use_historical and date_list:
        all_results = {}

        for target_date in date_list:
            print(f"\n{'='*60}")
            print(f"분석 날짜: {target_date}")
            print(f"{'='*60}")

            screener = BNFStockScreener(api, target_date=target_date)

            selected_stocks = screener.screen_stocks(
                kospi200_stocks,
                criteria,
                max_stocks=args.max_stocks,
                save_progress=True,
                use_historical=True
            )

            all_results[target_date] = selected_stocks

            if selected_stocks:
                print(f"\n{target_date}: {len(selected_stocks)}개 종목 선정")
                for stock in selected_stocks[:5]:
                    print(f"  - {stock['stock_name']} ({stock['stock_code']}): 이격율 {stock['price_above_ma25_pct']:.2f}%, RSI {stock['rsi']:.2f}")

        # 전체 요약
        print("\n" + "=" * 60)
        print("전체 분석 결과 요약")
        print("=" * 60)
        for date, stocks in all_results.items():
            print(f"{date}: {len(stocks)}개 종목")

    else:
        # 실시간 분석
        screener = BNFStockScreener(api)

        selected_stocks = screener.screen_stocks(
            kospi200_stocks,
            criteria,
            max_stocks=args.max_stocks,
            save_progress=True,
            use_historical=False
        )

        print("\n" + "=" * 60)
        print(f"BNF 매매법 선정 종목 (Screener 3): {len(selected_stocks)}개")
        print("=" * 60 + "\n")

        if selected_stocks:
            df = pd.DataFrame(selected_stocks)

            print("[ TOP 20 종목 ]")
            print("\n종목 기본 정보:")
            basic_cols = ['stock_code', 'stock_name', 'current_price', 'price_above_ma25_pct', 'rsi', 'macd', 'volume_ratio']
            print(df[basic_cols].head(20).to_string(index=False))

            print("\n\n매매 전략 (손절/익절):")
            print("-" * 100)
            for idx, stock in enumerate(selected_stocks[:20], 1):
                strategy = stock['trading_strategy']
                print(f"\n{idx}. {stock['stock_name']} ({stock['stock_code']}) - 현재가: {int(stock['current_price']):,}원")
                print(f"   📊 이격율: {stock['price_above_ma25_pct']:.2f}% | RSI: {stock['rsi']:.2f} | MACD: {stock['macd']:.2f}")

                if strategy['stop_loss']:
                    sl = strategy['stop_loss']
                    print(f"   💔 손절가: {sl['price']:,}원 ({sl['pct']:+.2f}%) - {sl['reason']}")

                if strategy['take_profit']:
                    for tp in strategy['take_profit']:
                        print(f"   💰 {tp['level']}차 익절: {tp['price']:,}원 ({tp['pct']:+.2f}%) - {tp['reason']} [{tp['action']}]")

                if 'risk_reward_ratio' in strategy:
                    print(f"   📈 손익비: 1:{strategy['risk_reward_ratio']}")

            print("\n" + "=" * 60)
            print("통계 정보:")
            print(f"  평균 이격율: {df['price_above_ma25_pct'].mean():.2f}%")
            print(f"  최소 이격율: {df['price_above_ma25_pct'].min():.2f}%")
            print(f"  평균 RSI: {df['rsi'].mean():.2f}")
            print(f"  평균 MACD: {df['macd'].mean():.2f}")
            print(f"  평균 거래량 비율: {df['volume_ratio'].mean():.2f}배")

            risk_rewards = [s['trading_strategy'].get('risk_reward_ratio', 0) for s in selected_stocks if 'risk_reward_ratio' in s['trading_strategy']]
            if risk_rewards:
                print(f"  평균 손익비: 1:{sum(risk_rewards)/len(risk_rewards):.2f}")
            print("=" * 60)
        else:
            print("선정된 종목이 없습니다.")
            print("기준을 조정해보세요.")


if __name__ == "__main__":
    main()
