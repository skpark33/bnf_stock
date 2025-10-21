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
    
    def __init__(self, app_key, app_secret, account_no, mock=False):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        
        # URL 설정: 모의투자와 실전투자 URL이 다름
        if mock:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            print("🔧 모의투자 모드")
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
            print("💰 실전투자 모드")
        
        self.access_token = None
        
        # 입력값 검증
        if not app_key or not app_secret or not account_no:
            raise ValueError("APP_KEY, APP_SECRET, ACCOUNT_NO는 필수입니다.")
        
        print(f"APP_KEY: {app_key[:10]}..." if len(app_key) > 10 else f"APP_KEY: {app_key}")
        print(f"Base URL: {self.base_url}")
        
        self._get_access_token()
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
            
            # 응답 상태 코드 확인
            if res.status_code != 200:
                print(f"\n❌ 토큰 발급 실패 (HTTP {res.status_code})")
                print(f"응답: {res.text}")
                raise Exception(f"API 응답 오류: {res.status_code}")
            
            result = res.json()
            
            # 응답에 access_token이 있는지 확인
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
        weekday = now.weekday()  # 0=월요일, 6=일요일
        
        # 주말 체크
        if weekday >= 5:  # 토요일(5), 일요일(6)
            print("\n⚠️  경고: 오늘은 주말입니다.")
            print("   마지막 거래일 데이터를 사용합니다.\n")
            return False
        
        # 장 운영시간 체크 (9:00 ~ 15:30)
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
            # pykrx로 최근 거래일 확인
            today = datetime.now()
            for i in range(10):  # 최대 10일 전까지 확인
                check_date = (today - timedelta(days=i)).strftime("%Y%m%d")
                try:
                    # KOSPI 지수로 거래일 확인
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
    
    def get_kospi_stocks(self):
        """KOSPI 전체 종목 코드 조회 (pykrx 사용)"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            stock_codes = stock.get_market_ticker_list(date=today, market="KOSPI")
            
            # 종목명도 함께 가져오기
            stocks = []
            for code in stock_codes:
                name = stock.get_market_ticker_name(code)
                stocks.append({
                    'code': code,
                    'name': name
                })
            
            print(f"KOSPI 종목 {len(stocks)}개 로드 완료")
            return stocks
        except Exception as e:
            print(f"종목 코드 조회 실패: {e}")
            return []
    
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
    
    def get_kosdaq_stocks(self):
        """KOSDAQ 전체 종목 코드 조회 (pykrx 사용)"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            stock_codes = stock.get_market_ticker_list(date=today, market="KOSDAQ")
            
            stocks = []
            for code in stock_codes:
                name = stock.get_market_ticker_name(code)
                stocks.append({
                    'code': code,
                    'name': name
                })
            
            print(f"KOSDAQ 종목 {len(stocks)}개 로드 완료")
            return stocks
        except Exception as e:
            print(f"종목 코드 조회 실패: {e}")
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


class BNFStockScreener:
    """BNF 매매법 종목 선정"""
    
    def __init__(self, api_client):
        self.api = api_client
        self.last_trading_date = api_client.get_last_trading_date()
        print(f"📅 기준 거래일: {self.last_trading_date[:4]}-{self.last_trading_date[4:6]}-{self.last_trading_date[6:]}\n")
    
    def calculate_moving_average(self, prices, period=25):
        """이동평균 계산"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
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
        """손절가/익절가 전략 계산 (ATR + 기술적 분석 복합)"""
        strategy = {
            'entry_price': current_price,
            'stop_loss': {},
            'take_profit': [],
            'support_line': support,
            'resistance_line': resistance,
            'atr': atr
        }
        
        # 손절가 계산
        atr_stop = current_price - (atr * 2) if atr else None
        support_stop = support * 0.98 if support else None
        ma_stop = ma25 * 0.97 if ma25 else None
        fixed_stop = current_price * 0.95
        
        stop_candidates = [
            ('ATR 기반 (ATR × 2)', atr_stop),
            ('기술적 지지선', support_stop),
            ('MA25 기반', ma_stop),
            ('고정 -5%', fixed_stop)
        ]
        
        valid_stops = [(name, price) for name, price in stop_candidates if price]
        if valid_stops:
            stop_loss_name, stop_loss_price = max(valid_stops, key=lambda x: x[1])
            stop_loss_pct = ((stop_loss_price - current_price) / current_price) * 100
            
            strategy['stop_loss'] = {
                'price': int(stop_loss_price),
                'pct': round(stop_loss_pct, 2),
                'reason': stop_loss_name,
                'alternatives': [
                    {'method': name, 'price': int(price), 'pct': round(((price - current_price) / current_price) * 100, 2)}
                    for name, price in valid_stops if price != stop_loss_price
                ]
            }
        
        # 익절가 계산
        if atr:
            tp1_atr = current_price + (atr * 3)
            tp2_atr = current_price + (atr * 5)
        else:
            tp1_atr = None
            tp2_atr = None
        
        tp_resistance = resistance * 0.99 if resistance and resistance > current_price else None
        
        risk = abs(current_price - strategy['stop_loss']['price']) if strategy['stop_loss'] else current_price * 0.05
        tp1_ratio = current_price + (risk * 2)
        tp2_ratio = current_price + (risk * 3)
        
        tp1_candidates = [
            ('ATR × 3', tp1_atr),
            ('손익비 2:1', tp1_ratio),
            ('고정 +5%', current_price * 1.05)
        ]
        valid_tp1 = [(name, price) for name, price in tp1_candidates if price]
        if valid_tp1:
            tp1_name, tp1_price = min(valid_tp1, key=lambda x: x[1])
            strategy['take_profit'].append({
                'level': 1,
                'price': int(tp1_price),
                'pct': round(((tp1_price - current_price) / current_price) * 100, 2),
                'reason': tp1_name,
                'action': '50% 부분 익절'
            })
        
        tp2_candidates = [
            ('ATR × 5', tp2_atr),
            ('저항선', tp_resistance),
            ('손익비 3:1', tp2_ratio),
            ('고정 +10%', current_price * 1.10)
        ]
        valid_tp2 = [(name, price) for name, price in tp2_candidates if price]
        if valid_tp2:
            tp2_name, tp2_price = min(valid_tp2, key=lambda x: x[1])
            strategy['take_profit'].append({
                'level': 2,
                'price': int(tp2_price),
                'pct': round(((tp2_price - current_price) / current_price) * 100, 2),
                'reason': tp2_name,
                'action': '잔량 전량 익절'
            })
        
        if strategy['stop_loss'] and strategy['take_profit']:
            risk_amount = current_price - strategy['stop_loss']['price']
            reward_amount = strategy['take_profit'][0]['price'] - current_price
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            strategy['risk_reward_ratio'] = round(risk_reward_ratio, 2)
        
        return strategy
    
    def screen_stocks(self, stock_codes, criteria, max_stocks=None, save_progress=True):
        """BNF 기준으로 종목 선정"""
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
                
                # stock_info가 딕셔너리인 경우와 문자열인 경우 모두 처리
                if isinstance(stock_info, dict):
                    stock_code = stock_info['code']
                    stock_name = stock_info['name']
                else:
                    stock_code = stock_info
                    stock_name = None
                
                time.sleep(0.05)
                
                current_data = self.api.get_current_price(stock_code)
                if 'output' not in current_data:
                    continue
                
                output = current_data['output']
                current_price = float(output['stck_prpr'])
                prev_price = float(output['stck_sdpr'])
                volume = int(output['acml_vol'])
                
                # API에서 종목명 가져오기 (우선순위: 캐시된 이름 > API 이름)
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
                
                if len(prices) < 26:
                    continue
                
                ma25 = self.calculate_moving_average(prices, 25)
                rsi = self.calculate_rsi(prices, 14)
                atr = self.calculate_atr(high_prices, low_prices, prices, 14)
                support, resistance = self.calculate_support_resistance(high_prices, low_prices, prices, 20)
                
                price_change_pct = ((current_price - prev_price) / prev_price) * 100
                
                avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else volumes[0]
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                
                passed = True
                
                if 'price_increase_pct' in criteria:
                    if price_change_pct < criteria['price_increase_pct']:
                        passed = False
                
                if 'volume_increase_ratio' in criteria:
                    if volume_ratio < criteria['volume_increase_ratio']:
                        passed = False
                
                if rsi and 'rsi_min' in criteria:
                    if rsi < criteria['rsi_min']:
                        passed = False
                
                if rsi and 'rsi_max' in criteria:
                    if rsi > criteria['rsi_max']:
                        passed = False
                
                if ma25 and criteria.get('above_ma25', False):
                    if current_price < ma25:
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
                        'rsi': round(rsi, 2) if rsi else None,
                        'atr': round(atr, 2) if atr else None,
                        'trading_strategy': trading_strategy
                    }
                    results.append(result)
                    print(f"✓ 선정: {stock_name} ({stock_code}) - 상승률: {price_change_pct:.2f}% | 손절: {trading_strategy['stop_loss'].get('price', 'N/A')} | 익절: {trading_strategy['take_profit'][0]['price'] if trading_strategy['take_profit'] else 'N/A'}")
                    
            except Exception as e:
                print(f"Error processing {stock_code if 'stock_code' in locals() else 'unknown'}: {e}")
                continue
        
        print(f"\n분석 완료! 총 {len(results)}개 종목 선정됨")
        
        results.sort(key=lambda x: x['price_change_pct'], reverse=True)
        
        if save_progress and results:
            self._save_results(results)
        
        return results
    
    def _save_results(self, results):
        """결과를 JSON 파일로 저장"""
        try:
            filename = f"result_{self.last_trading_date}.json"
            
            output_data = {
                'trading_date': self.last_trading_date,
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_count': len(results),
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
                    'rsi': result['rsi'],
                    'atr': result['atr'],
                    'trading_strategy': result['trading_strategy']
                }
                output_data['selected_stocks'].append(stock_info)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n결과 저장: {filename}")
            
            csv_filename = f"result_{self.last_trading_date}.csv"
            df = pd.DataFrame(results)
            df.insert(0, 'trading_date', self.last_trading_date)
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"CSV 저장: {csv_filename}")
            
        except Exception as e:
            print(f"결과 저장 실패: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='BNF 매매법 종목 선정 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  1. 설정 파일 사용 (권장):
     python bnf_stock_screener.py --config config.json
  
  2. 명령줄 직접 입력:
     python bnf_stock_screener.py -k YOUR_KEY -s YOUR_SECRET -a YOUR_ACCOUNT
     python bnf_stock_screener.py -k YOUR_KEY -s YOUR_SECRET -a YOUR_ACCOUNT --mock
        '''
    )
    
    parser.add_argument('--config', help='설정 파일 경로 (JSON)')
    parser.add_argument('-k', '--app-key', help='한국투자증권 APP KEY')
    parser.add_argument('-s', '--app-secret', help='한국투자증권 APP SECRET')
    parser.add_argument('-a', '--account', help='계좌번호')
    parser.add_argument('--mock', action='store_true', help='모의투자 모드 사용')
    parser.add_argument('--max-stocks', type=int, default=None, help='분석할 최대 종목 수')
    parser.add_argument('--no-cache', action='store_true', help='캐시 파일 사용 안함')
    parser.add_argument('--price-increase', type=float, default=3.0, help='최소 상승률 %%')
    parser.add_argument('--volume-ratio', type=float, default=2.0, help='최소 거래량 비율')
    parser.add_argument('--rsi-min', type=int, default=50, help='최소 RSI')
    parser.add_argument('--rsi-max', type=int, default=70, help='최대 RSI')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BNF 매매법 종목 선정 프로그램")
    print("=" * 60)
    
    if args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            app_key = config.get('app_key')
            app_secret = config.get('app_secret')
            account = config.get('account')
            mock = config.get('mock', False)
            
            if 'price_increase' in config:
                args.price_increase = config['price_increase']
            if 'volume_ratio' in config:
                args.volume_ratio = config['volume_ratio']
            if 'rsi_min' in config:
                args.rsi_min = config['rsi_min']
            if 'rsi_max' in config:
                args.rsi_max = config['rsi_max']
            
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
            print("  python bnf_stock_screener.py --config config.json")
            sys.exit(1)
    
    try:
        print(f"\n입력받은 값:")
        print(f"  APP_KEY 길이: {len(app_key)}")
        print(f"  APP_SECRET 길이: {len(app_secret)}")
        print(f"  계좌번호: {account}")
        print(f"  모의투자: {mock}\n")
        
        api = KISAPIClient(app_key, app_secret, account, mock=mock)
    except Exception as e:
        print(f"\n❌ API 초기화 실패: {e}")
        print("\n다음을 확인해주세요:")
        print("  1. APP_KEY와 APP_SECRET이 올바른지")
        print("  2. 실전투자 키로 모의투자 모드를 사용하거나 그 반대는 아닌지")
        print("  3. 특수문자가 있다면 따옴표로 감쌌는지")
        print("  4. 한국투자증권 API 포털에서 키가 활성화되어 있는지")
        print("\n설정 파일 사용을 권장합니다:")
        print("  python bnf_stock_screener.py --config config.json")
        sys.exit(1)
    
    screener = BNFStockScreener(api)
    
    print("=" * 60)
    print("KOSPI 200 종목 코드 로딩 중...")
    print("=" * 60)
    
    kospi200_stocks = api.get_kospi200_stocks(use_cache=not args.no_cache)
    
    # 수정: 딕셔너리 전체를 전달 (코드만 추출하지 않음)
    print(f"총 {len(kospi200_stocks)}개 종목 로드 완료\n")
    
    criteria = {
        'price_increase_pct': args.price_increase,
        'volume_increase_ratio': args.volume_ratio,
        'rsi_min': args.rsi_min,
        'rsi_max': args.rsi_max,
        'above_ma25': True
    }
    
    print("=" * 60)
    print("BNF 매매법 기준:")
    print(f"  - 상승률: {criteria['price_increase_pct']}% 이상")
    print(f"  - 거래량: 평균의 {criteria['volume_increase_ratio']}배 이상")
    print(f"  - RSI: {criteria['rsi_min']} ~ {criteria['rsi_max']}")
    print(f"  - 25일 이평선 위")
    print("=" * 60)
    
    selected_stocks = screener.screen_stocks(
        kospi200_stocks,  # 수정: 딕셔너리 리스트 전체 전달
        criteria,
        max_stocks=args.max_stocks,
        save_progress=True
    )
    
    print("\n" + "=" * 60)
    print(f"BNF 매매법 선정 종목: {len(selected_stocks)}개")
    print("=" * 60 + "\n")
    
    if selected_stocks:
        df = pd.DataFrame(selected_stocks)
        
        print("[ TOP 20 종목 ]")
        print("\n종목 기본 정보:")
        basic_cols = ['stock_code', 'stock_name', 'current_price', 'price_change_pct', 'volume_ratio', 'rsi']
        print(df[basic_cols].head(20).to_string(index=False))
        
        print("\n\n매매 전략 (손절/익절):")
        print("-" * 100)
        for idx, stock in enumerate(selected_stocks[:20], 1):
            strategy = stock['trading_strategy']
            print(f"\n{idx}. {stock['stock_name']} ({stock['stock_code']}) - 현재가: {int(stock['current_price']):,}원")
            
            if strategy['stop_loss']:
                sl = strategy['stop_loss']
                print(f"   💔 손절가: {sl['price']:,}원 ({sl['pct']:+.2f}%) - {sl['reason']}")
            
            if strategy['take_profit']:
                for tp in strategy['take_profit']:
                    print(f"   💰 {tp['level']}차 익절: {tp['price']:,}원 ({tp['pct']:+.2f}%) - {tp['reason']} [{tp['action']}]")
            
            if 'risk_reward_ratio' in strategy:
                print(f"   📊 손익비: 1:{strategy['risk_reward_ratio']}")
        
        print("\n" + "=" * 60)
        print("통계 정보:")
        print(f"  평균 상승률: {df['price_change_pct'].mean():.2f}%")
        print(f"  최대 상승률: {df['price_change_pct'].max():.2f}%")
        print(f"  평균 거래량 비율: {df['volume_ratio'].mean():.2f}배")
        print(f"  평균 RSI: {df['rsi'].mean():.2f}")
        
        risk_rewards = [s['trading_strategy'].get('risk_reward_ratio', 0) for s in selected_stocks if 'risk_reward_ratio' in s['trading_strategy']]
        if risk_rewards:
            print(f"  평균 손익비: 1:{sum(risk_rewards)/len(risk_rewards):.2f}")
        print("=" * 60)
    else:
        print("선정된 종목이 없습니다.")
        print("기준을 조정해보세요.")
