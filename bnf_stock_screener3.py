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

    def __init__(self, app_key, app_secret, account_no, mock=False, use_pykrx_for_historical=False, skip_api_init=False):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.use_pykrx_for_historical = use_pykrx_for_historical
        self.skip_api_init = skip_api_init

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

        if skip_api_init:
            print("🚫 API 토큰 요청 생략 (캐시 데이터 사용)")
            return

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
        Returns: (MACD Line, Signal Line, Histogram, MACD Series, Signal Series)
        """
        if len(prices) < slow + signal:
            return None, None, None, None, None

        price_series = pd.Series(prices)
        macd_series = price_series.ewm(span=fast, adjust=False).mean() - price_series.ewm(span=slow, adjust=False).mean()
        signal_series = macd_series.ewm(span=signal, adjust=False).mean()
        histogram_series = macd_series - signal_series

        macd_line = macd_series.iloc[-1]
        signal_line = signal_series.iloc[-1]
        histogram = histogram_series.iloc[-1]

        return macd_line, signal_line, histogram, macd_series.tolist(), signal_series.tolist()

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

    def calculate_rsi_series(self, prices, period=14):
        """RSI 시계열 계산 (최근 여러 일의 RSI 반환)"""
        if len(prices) < period + 1:
            return None

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        rsi_values = []

        # 첫 RSI 계산 (SMA 방식)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        rsi_values.append(rsi)

        # 이후 RSI 계산 (EMA 방식)
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)

        return rsi_values

    def calculate_rsi_signal_series(self, rsi_values, signal_period=9):
        """RSI 시그널(EMA) 시계열 계산"""
        if not rsi_values or len(rsi_values) < signal_period:
            return None

        signal_series = [None] * (signal_period - 1)
        initial_sma = sum(rsi_values[:signal_period]) / signal_period
        signal_series.append(initial_sma)

        multiplier = 2 / (signal_period + 1)
        ema = initial_sma

        for value in rsi_values[signal_period:]:
            ema = (value - ema) * multiplier + ema
            signal_series.append(ema)

        return signal_series

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

    def screen_stocks(self, stock_codes, criteria, max_stocks=None, save_progress=True, use_historical=False, historical_data=None):
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

                prev_volume = None
                if use_historical:
                    if historical_data is not None and stock_code in historical_data:
                        data_entry = historical_data[stock_code]
                        prices = data_entry['prices']
                        high_prices = data_entry['high_prices']
                        low_prices = data_entry['low_prices']
                        volumes = data_entry['volumes']
                        stock_name = data_entry.get('name', stock_name) or stock.get_market_ticker_name(stock_code)
                    else:
                        time.sleep(0.1)

                        end_date = self.last_trading_date
                        start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=90)).strftime("%Y%m%d")

                        df = self.api.get_historical_data_pykrx(stock_code, start_date, end_date)
                        if df is None or df.empty or len(df) < 30:
                            continue

                        prices = [float(p) for p in df['종가'].tolist()]
                        high_prices = [float(p) for p in df['고가'].tolist()]
                        low_prices = [float(p) for p in df['저가'].tolist()]
                        volumes = [int(v) for v in df['거래량'].tolist()]

                        if historical_data is not None:
                            historical_data[stock_code] = {
                                'prices': prices,
                                'high_prices': high_prices,
                                'low_prices': low_prices,
                                'volumes': volumes,
                                'name': stock_name or stock.get_market_ticker_name(stock_code)
                            }

                    current_price = prices[-1]
                    prev_price = prices[-2] if len(prices) >= 2 else prices[-1]
                    volume = volumes[-1]
                    if len(volumes) >= 2:
                        prev_volume = volumes[-2]

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

                    if len(volumes) >= 2:
                        prev_volume = volumes[-2]

                # 기술적 지표 계산
                ma25 = self.calculate_moving_average(prices, 25)
                rsi = self.calculate_rsi(prices, 14) if criteria.get('enable_rsi', True) else None
                rsi_series = self.calculate_rsi_series(prices, 14) if criteria.get('enable_rsi', True) else None
                rsi_signal_series = self.calculate_rsi_signal_series(rsi_series, signal_period=9) if (criteria.get('enable_rsi', True) and rsi_series) else None
                macd_line, signal_line, macd_hist, macd_series, macd_signal_series = self.calculate_macd(prices)
                atr = self.calculate_atr(high_prices, low_prices, prices, 14)
                support, resistance = self.calculate_support_resistance(high_prices, low_prices, prices, 20)

                price_change_pct = ((current_price - prev_price) / prev_price) * 100

                avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else volumes[0]
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                volume_increase_pct_val = None
                if prev_volume and prev_volume > 0:
                    volume_increase_pct_val = (volume / prev_volume) * 100

                # Screener 3 선정 조건 검사
                passed = True
                prev_rsi = None
                curr_rsi = None
                prev_rsi_signal = None
                curr_rsi_signal = None
                prev_macd = None
                curr_macd = None
                prev_macd_signal = None
                curr_macd_signal = None

                # 1) MA25 이격율 조건
                if criteria.get('enable_ma25', True):
                    if ma25:
                        price_above_ma25_pct = ((current_price - ma25) / ma25) * 100
                        if price_above_ma25_pct > criteria.get('ma25_deviation_max', -10):
                            passed = False
                    else:
                        passed = False
                else:
                    price_above_ma25_pct = ((current_price - ma25) / ma25) * 100 if ma25 else None

                # 2) RSI 과매도 상태에서 매수 신호 (RSI 상승 전환)
                if criteria.get('enable_rsi', True):
                    if rsi_series and len(rsi_series) >= 2 and rsi_signal_series and len(rsi_signal_series) >= 2:
                        prev_rsi = rsi_series[-2]
                        curr_rsi = rsi_series[-1]
                        prev_rsi_signal = rsi_signal_series[-2]
                        curr_rsi_signal = rsi_signal_series[-1]

                        if prev_rsi_signal is None or curr_rsi_signal is None:
                            passed = False
                        else:
                            prev_diff = prev_rsi - prev_rsi_signal
                            curr_diff = curr_rsi - curr_rsi_signal
                            rsi_max_threshold = criteria.get('rsi_oversold', 30)

                            if not (prev_rsi <= rsi_max_threshold and curr_rsi > prev_rsi and prev_diff <= 0 and curr_diff > 0):
                                passed = False
                                print(
                                    f"RSI 조건 실패 -> prev_rsi: {prev_rsi:.2f}, curr_rsi: {curr_rsi:.2f}, "
                                    f"prev_signal: {prev_rsi_signal:.2f}, curr_signal: {curr_rsi_signal:.2f}, "
                                    f"threshold: {rsi_max_threshold}, prev_diff: {prev_diff:.2f}, curr_diff: {curr_diff:.2f}"
                                )
                    else:
                        passed = False

                # 3) MACD(12,26)가 MACD(9) 시그널을 상향 돌파할 것 (옵션 사용 시)
                if criteria.get('enable_macd', True):
                    if macd_series and macd_signal_series and len(macd_series) >= 2 and len(macd_signal_series) >= 2:
                        prev_macd = macd_series[-2]
                        curr_macd = macd_series[-1]
                        prev_macd_signal = macd_signal_series[-2]
                        curr_macd_signal = macd_signal_series[-1]

                        prev_macd_diff = prev_macd - prev_macd_signal
                        curr_macd_diff = curr_macd - curr_macd_signal

                        if not (prev_macd_diff <= 0 and curr_macd_diff > 0):
                            passed = False
                    else:
                        passed = False

                # 4) 거래량 조건 (옵션 사용 시)
                volume_increase_threshold = criteria.get('volume_increase_pct')
                if volume_increase_threshold is not None:
                    if volume_increase_pct_val is None:
                        passed = False
                    else:
                        if volume_increase_pct_val < volume_increase_threshold:
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
                        'prev_volume': prev_volume,
                        'volume_increase_pct': round(volume_increase_pct_val, 2) if volume_increase_pct_val is not None else None,
                        'ma25': round(ma25, 2) if ma25 else None,
                        'price_above_ma25_pct': round(price_above_ma25_pct, 2) if price_above_ma25_pct is not None else None,
                        'rsi': round(rsi, 2) if rsi else None,
                        'prev_rsi': round(prev_rsi, 2) if prev_rsi is not None else None,
                        'curr_rsi': round(curr_rsi, 2) if curr_rsi is not None else None,
                        'prev_rsi_signal': round(prev_rsi_signal, 2) if prev_rsi_signal is not None else None,
                        'curr_rsi_signal': round(curr_rsi_signal, 2) if curr_rsi_signal is not None else None,
                        'macd': round(macd_line, 2) if macd_line is not None else None,
                        'macd_signal': round(signal_line, 2) if signal_line is not None else None,
                        'prev_macd': round(prev_macd, 2) if prev_macd is not None else None,
                        'curr_macd': round(curr_macd, 2) if curr_macd is not None else None,
                        'prev_macd_signal': round(prev_macd_signal, 2) if prev_macd_signal is not None else None,
                        'curr_macd_signal': round(curr_macd_signal, 2) if curr_macd_signal is not None else None,
                        'macd_hist': round(macd_hist, 2) if macd_hist is not None else None,
                        'atr': round(atr, 2) if atr else None,
                        'trading_strategy': trading_strategy
                    }
                    results.append(result)
                    rsi_change = (curr_rsi - prev_rsi) if (curr_rsi is not None and prev_rsi is not None) else 0
                    volume_log = ""
                    if volume_increase_pct_val is not None:
                        volume_log = f", 거래량: {volume_increase_pct_val:.1f}%"
                    signal_log = ""
                    if criteria.get('enable_rsi', True) and prev_rsi_signal is not None and curr_rsi_signal is not None:
                        signal_log = f", RSI 시그널: {prev_rsi_signal:.2f}→{curr_rsi_signal:.2f}"
                macd_log = ""
                if criteria.get('enable_macd', True):
                    if prev_macd is not None and curr_macd is not None and prev_macd_signal is not None and curr_macd_signal is not None:
                        macd_log = f", MACD: {prev_macd:.2f}→{curr_macd:.2f} / 시그널: {prev_macd_signal:.2f}→{curr_macd_signal:.2f}"
                    elif macd_line is not None:
                        macd_log = f", MACD: {macd_line:.2f}"
                rsi_log = ""
                if criteria.get('enable_rsi', True) and prev_rsi is not None and curr_rsi is not None:
                    rsi_log = f", RSI: {prev_rsi:.2f}→{curr_rsi:.2f} (+{rsi_change:.2f})"
                ma25_text = ""
                if price_above_ma25_pct is not None:
                    ma25_text = f"이격율: {price_above_ma25_pct:.2f}%"
                else:
                    ma25_text = "이격율: N/A"
                print(f"✓ 선정: {stock_name} ({stock_code}) - {ma25_text}{rsi_log}{signal_log}{macd_log}{volume_log}")

            except Exception as e:
                continue

        print(f"\n분석 완료! 총 {len(results)}개 종목 선정됨")

        # MA25 이격율 낮은 순으로 정렬 (음수가 클수록 우선)
        results.sort(key=lambda x: x['price_above_ma25_pct'] if x['price_above_ma25_pct'] is not None else 0, reverse=False)

        if save_progress and results:
            self._save_results(results)

        return results

    @staticmethod
    def load_api_cache(cache_path):
        """저장된 API 데이터를 로드"""
        if not os.path.exists(cache_path):
            return {}
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 캐시 로드 실패: {e}. 새로 데이터를 수집합니다.")
            return {}

    @staticmethod
    def save_api_cache(cache_path, cache_data):
        """API 데이터를 캐시에 저장"""
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
            print(f"✓ API 데이터 캐시 저장: {cache_path}")
        except Exception as e:
            print(f"⚠️ API 데이터 캐시 저장 실패: {e}")

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
                    'description': 'MA25 이격율 -10% 이하, RSI 30 이하 상향 돌파, MACD(12,26) 상향 돌파'
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
                    'prev_rsi': result['prev_rsi'],
                    'curr_rsi': result['curr_rsi'],
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
  - RSI 과매도 매수 신호 (이전 RSI < 30이고 현재 RSI > 이전 RSI)
  - MACD 값이 0보다 클 것

  이격율(%) = (현재주가 - MA25) ÷ MA25 × 100
  RSI 매수 신호: 과매도 구간에서 상승 전환
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
    parser.add_argument('--ma25', type=float, default=-10.0, help='MA25 이격율 최댓값 %% (기본값: -10%%, 즉 MA25보다 10%% 이상 낮아야 함)')
    parser.add_argument('--rsi-oversold', type=float, default=30.0, help='RSI 최대값 (기본값: 30)')
    parser.add_argument('--volume', type=float, help='전일 대비 거래량 증가율 임계값 (예: 150 = 150%%, 200 = 200%%)')
    parser.add_argument('--refresh', action='store_true', help='저장된 API 데이터를 무시하고 새로 수집')
    parser.add_argument('--no-macd', action='store_true', help='MACD 조건을 사용하지 않음')
    parser.add_argument('--no-rsi', action='store_true', help='RSI 조건을 사용하지 않음')
    parser.add_argument('--no-ma25', action='store_true', help='MA25 이격율 조건을 사용하지 않음')
    parser.add_argument('--del-olddata', action='store_true', help='data/json 및 data/csv 기존 파일 삭제 후 시작')

    args = parser.parse_args()

    print("=" * 60)
    print("BNF 매매법 종목 선정 프로그램 (Screener 3)")
    print("=" * 60)

    # 날짜 범위 처리
    use_historical = False
    date_list = []
    cache_filename = None

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

            cache_from = args.from_date
            cache_to = args.to_date if args.to_date else args.from_date
            cache_filename = f"data/api_data_{cache_from}_{cache_to}.json"

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
    skip_api_init = False
    if use_historical and cache_filename and not args.refresh and not args.no_cache:
        if os.path.exists(cache_filename) and os.path.exists('kospi_200_code.json'):
            skip_api_init = True

    if args.del_olddata:
        for folder, pattern in [('data/json', '*.json'), ('data/csv', '*.csv')]:
            folder_path = os.path.join(folder)
            if os.path.exists(folder_path):
                for file_name in os.listdir(folder_path):
                    if file_name.endswith(('.json', '.csv')):
                        file_path = os.path.join(folder_path, file_name)
                        try:
                            os.remove(file_path)
                            print(f"🧹 삭제: {file_path}")
                        except Exception as e:
                            print(f"⚠️ 삭제 실패: {file_path} -> {e}")

    try:
        print(f"\n입력받은 값:")
        print(f"  APP_KEY 길이: {len(app_key)}")
        print(f"  APP_SECRET 길이: {len(app_secret)}")
        print(f"  계좌번호: {account}")
        print(f"  모의투자: {mock}")
        print(f"  과거 데이터 분석: {use_historical}\n")

        api = KISAPIClient(
            app_key,
            app_secret,
            account,
            mock=mock,
            use_pykrx_for_historical=use_historical,
            skip_api_init=skip_api_init
        )
    except Exception as e:
        print(f"\n❌ API 초기화 실패: {e}")
        sys.exit(1)

    # 종목 코드 로딩
    print("=" * 60)
    print("KOSPI 200 종목 코드 로딩 중...")
    print("=" * 60)

    if skip_api_init and os.path.exists('kospi_200_code.json'):
        try:
            with open('kospi_200_code.json', 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            kospi200_stocks = cache_data.get('stocks', [])
            print(f"캐시에서 KOSPI 200 종목 {len(kospi200_stocks)}개 로드 완료")
        except Exception as e:
            print(f"⚠️ KOSPI 200 캐시 로드 실패: {e}. API에서 다시 가져옵니다.")
            kospi200_stocks = api.get_kospi200_stocks(use_cache=not args.no_cache)
    else:
        kospi200_stocks = api.get_kospi200_stocks(use_cache=not args.no_cache)
    print(f"총 {len(kospi200_stocks)}개 종목 로드 완료\n")

    # 선정 기준 설정 (Screener 3)
    criteria = {
        'ma25_deviation_max': args.ma25,
        'rsi_oversold': args.rsi_oversold,
        'volume_increase_pct': args.volume,
        'enable_macd': not args.no_macd,
        'enable_rsi': not args.no_rsi,
        'enable_ma25': not args.no_ma25
    }

    print("=" * 60)
    print("BNF 매매법 기준 (Screener 3):")
    if criteria['enable_ma25']:
        print(f"  - MA25 이격율: {criteria['ma25_deviation_max']}% 이하")
    if criteria['enable_rsi']:
        print(f"  - RSI: {criteria['rsi_oversold']} 이하 & RSI14가 RSI9(시그널)을 상향 돌파")
    if criteria['enable_macd']:
        print(f"  - MACD: MACD(12,26)이 MACD(9) 시그널을 상향 돌파")
    if criteria['volume_increase_pct'] is not None:
        print(f"  - 거래량: 전일 대비 {criteria['volume_increase_pct']}% 이상")
    print("=" * 60)

    # 날짜별 분석
    if use_historical and date_list:
        all_results = {}

        api_cache = {}
        cache_keys = []
        if args.to_date:
            cache_keys = [args.from_date, args.to_date]
        else:
            cache_keys = [args.from_date, args.from_date]

        cache_filename = f"data/api_data_{cache_keys[0]}_{cache_keys[1]}.json"

        if not args.refresh:
            api_cache = BNFStockScreener.load_api_cache(cache_filename)
            if api_cache:
                print(f"✓ 캐시 파일 '{cache_filename}'에서 데이터 로드 완료")

        os.makedirs('data', exist_ok=True)

        for target_date in date_list:
            print(f"\n{'='*60}")
            print(f"분석 날짜: {target_date}")
            print(f"{'='*60}")

            date_cache = api_cache.get(target_date)
            if date_cache is None:
                date_cache = {}
                api_cache[target_date] = date_cache

            screener = BNFStockScreener(api, target_date=target_date)

            selected_stocks = screener.screen_stocks(
                kospi200_stocks,
                criteria,
                max_stocks=args.max_stocks,
                save_progress=True,
                use_historical=True,
                historical_data=date_cache
            )

            all_results[target_date] = selected_stocks

            if selected_stocks:
                print(f"\n{target_date}: {len(selected_stocks)}개 종목 선정")
                for stock in selected_stocks[:5]:
                    prev_rsi = stock.get('prev_rsi')
                    curr_rsi = stock.get('curr_rsi')
                    rsi_text = ""
                    if criteria.get('enable_rsi', True) and prev_rsi is not None and curr_rsi is not None:
                        rsi_change = curr_rsi - prev_rsi
                        rsi_text = f", RSI {prev_rsi:.2f}→{curr_rsi:.2f} (+{rsi_change:.2f})"
                    print(f"  - {stock['stock_name']} ({stock['stock_code']}): 이격율 {stock['price_above_ma25_pct']:.2f}%{rsi_text}")

        if api_cache:
            BNFStockScreener.save_api_cache(cache_filename, api_cache)

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
            basic_cols = ['stock_code', 'stock_name', 'current_price', 'price_above_ma25_pct', 'prev_rsi', 'curr_rsi', 'macd', 'volume_ratio']
            print(df[basic_cols].head(20).to_string(index=False))

            print("\n\n매매 전략 (손절/익절):")
            print("-" * 100)
            for idx, stock in enumerate(selected_stocks[:20], 1):
                strategy = stock['trading_strategy']
                prev_rsi = stock.get('prev_rsi')
                curr_rsi = stock.get('curr_rsi')
                rsi_change = (curr_rsi - prev_rsi) if (prev_rsi is not None and curr_rsi is not None) else None
                print(f"\n{idx}. {stock['stock_name']} ({stock['stock_code']}) - 현재가: {int(stock['current_price']):,}원")
                rsi_info = ""
                if criteria.get('enable_rsi', True) and prev_rsi is not None and curr_rsi is not None and rsi_change is not None:
                    rsi_info = f" | RSI: {prev_rsi:.2f}→{curr_rsi:.2f} (+{rsi_change:.2f})"
                macd_value = stock.get('macd')
                macd_text = f"{macd_value:.2f}" if macd_value is not None else "N/A"
                ma25_pct = stock.get('price_above_ma25_pct')
                ma25_text = f"{ma25_pct:.2f}%" if ma25_pct is not None else "N/A"
                print(f"   📊 이격율: {ma25_text}{rsi_info} | MACD: {macd_text}")

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
            print(f"  평균 RSI (이전→현재): {df['prev_rsi'].mean():.2f} → {df['curr_rsi'].mean():.2f}")
            print(f"  평균 RSI 변화: +{(df['curr_rsi'].mean() - df['prev_rsi'].mean()):.2f}")
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
