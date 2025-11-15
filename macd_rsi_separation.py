import json
import os
import sys
import argparse
import csv
from datetime import datetime, timedelta
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


class TechnicalIndicators:
    """기술적 지표 계산 클래스"""
    
    @staticmethod
    def calculate_ema(prices, period):
        """EMA (Exponential Moving Average) 계산"""
        if len(prices) < period:
            return [None] * len(prices)
        
        ema_values = []
        multiplier = 2 / (period + 1)
        
        # 첫 EMA는 SMA로 시작
        sma = sum(prices[:period]) / period
        ema_values.append(sma)
        
        # 이후 EMA 계산
        for i in range(period, len(prices)):
            ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)
        
        # 앞부분을 None으로 채움
        return [None] * (period - 1) + ema_values
    
    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        """MACD 계산 (MACD Line, Signal Line 반환)"""
        if len(prices) < slow + signal:
            return [None] * len(prices), [None] * len(prices)
        
        # MACD Line 계산
        fast_ema = TechnicalIndicators.calculate_ema(prices, fast)
        slow_ema = TechnicalIndicators.calculate_ema(prices, slow)
        
        macd_line = []
        for i in range(len(prices)):
            if fast_ema[i] is not None and slow_ema[i] is not None:
                macd_line.append(fast_ema[i] - slow_ema[i])
            else:
                macd_line.append(None)
        
        # Signal Line 계산 (MACD의 EMA)
        valid_macd = [m for m in macd_line if m is not None]
        if len(valid_macd) < signal:
            return macd_line, [None] * len(prices)
        
        signal_ema = TechnicalIndicators.calculate_ema(valid_macd, signal)
        
        # None 부분 채우기
        none_count = len([m for m in macd_line if m is None])
        signal_line = [None] * none_count + signal_ema
        
        return macd_line, signal_line
    
    @staticmethod
    def calculate_rsi(prices, period=14):
        """RSI 계산"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        rsi_values = [None]  # 첫 번째는 None
        
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
    
    @staticmethod
    def calculate_ma(prices, period):
        """이동평균 계산"""
        if len(prices) < period:
            return [None] * len(prices)
        
        ma_values = []
        for i in range(len(prices)):
            if i < period - 1:
                ma_values.append(None)
            else:
                ma = sum(prices[i-period+1:i+1]) / period
                ma_values.append(ma)
        
        return ma_values


class DataLoader:
    """데이터 로드 클래스"""
    
    @staticmethod
    def load_kospi200_data(start_date, end_date):
        """지정된 기간의 KOSPI 200 데이터 로드"""
        base_dir = 'data/json/kospi200'
        
        if not os.path.exists(base_dir):
            print(f"❌ 데이터 폴더가 없습니다: {base_dir}")
            print(f"   먼저 get_data.py를 실행하여 데이터를 수집하세요:")
            print(f"   python get_data.py --config config.json --from {start_date} --to {end_date}")
            return None
        
        # 필요한 연도 목록
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        years = list(range(start_year, end_year + 1))
        
        # 각 연도별 데이터 로드
        all_days = []
        for year in years:
            year_file = os.path.join(base_dir, str(year), 'kospi200_data.json')
            if os.path.exists(year_file):
                with open(year_file, 'r', encoding='utf-8') as f:
                    year_data = json.load(f)
                    all_days.extend(year_data['data'])
            else:
                print(f"⚠️  {year}년 데이터 파일이 없습니다: {year_file}")
        
        if not all_days:
            print(f"❌ 데이터가 없습니다.")
            print(f"   먼저 get_data.py를 실행하여 데이터를 수집하세요:")
            print(f"   python get_data.py --config config.json --from {start_date} --to {end_date}")
            return None
        
        # 날짜 범위 필터링
        filtered_days = [d for d in all_days if start_date <= d['date'] <= end_date]
        
        if not filtered_days:
            print(f"❌ {start_date} ~ {end_date} 기간의 데이터가 없습니다.")
            print(f"   먼저 get_data.py를 실행하여 데이터를 수집하세요:")
            print(f"   python get_data.py --config config.json --from {start_date} --to {end_date}")
            return None
        
        # 거래일만 필터링
        trading_days = [d for d in filtered_days if not d['is_holiday']]
        
        if not trading_days:
            print(f"❌ 기간 내 거래일이 없습니다.")
            return None
        
        return sorted(trading_days, key=lambda x: x['date'])
    
    @staticmethod
    def get_stock_timeseries(trading_days, stock_code):
        """특정 종목의 시계열 데이터 추출"""
        timeseries = []
        
        for day in trading_days:
            stock = next((s for s in day['stocks'] if s['code'] == stock_code), None)
            if stock:
                timeseries.append({
                    'date': day['date'],
                    'open': stock['open'],
                    'high': stock['high'],
                    'low': stock['low'],
                    'close': stock['close'],
                    'volume': stock['volume']
                })
        
        return timeseries


class StockScreener:
    """종목 선별 클래스"""
    
    def __init__(self, trading_days, silent=False):
        self.trading_days = trading_days
        self.all_stocks = self._get_all_stock_codes()
        self.silent = silent
    
    def _get_all_stock_codes(self):
        """모든 종목 코드 추출"""
        if not self.trading_days:
            return []
        
        # 가장 최근 거래일의 종목 목록
        latest_day = self.trading_days[-1]
        stocks = [{'code': s['code'], 'name': s['name']} for s in latest_day['stocks']]
        return stocks
    
    def find_macd_golden_cross(self, start_date=None, end_date=None):
        """MACD 골든 크로스 발생 종목 찾기"""
        if not self.silent:
            print(f"\n{'='*60}")
            print(f"1단계: MACD 골든 크로스 종목 검색")
            print(f"{'='*60}")
        
        macd_stocks = []
        total = len(self.all_stocks)
        
        for idx, stock_info in enumerate(self.all_stocks, 1):
            if not self.silent and idx % 50 == 0:
                print(f"진행중: {idx}/{total} ({idx/total*100:.1f}%)")
            
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            
            # 종목 시계열 데이터 추출
            timeseries = DataLoader.get_stock_timeseries(self.trading_days, stock_code)
            
            if len(timeseries) < 50:  # 최소 50일 데이터 필요
                continue
            
            closes = [t['close'] for t in timeseries]
            
            # MACD 계산
            macd_line, signal_line = TechnicalIndicators.calculate_macd(closes)
            
            # 골든 크로스 찾기
            golden_cross_info = self._find_golden_cross(
                macd_line, signal_line, timeseries, start_date, end_date
            )
            
            if golden_cross_info:
                macd_stocks.append({
                    'code': stock_code,
                    'name': stock_name,
                    'macd_golden_cross_date': golden_cross_info['date'],
                    'macd_golden_cross_index': golden_cross_info['index'],
                    'macd_value': golden_cross_info['value1'],
                    'macd_signal': golden_cross_info['value2']
                })
        
        if not self.silent:
            print(f"\n✓ MACD 골든 크로스 발견: {len(macd_stocks)}개 종목")
            for stock in macd_stocks[:10]:
                print(f"  - {stock['name']} ({stock['code']}): {stock['macd_golden_cross_date']}")
            
            if len(macd_stocks) > 10:
                print(f"  ... 외 {len(macd_stocks) - 10}개 종목")
        
        return macd_stocks
    
    def find_rsi_golden_cross(self, candidate_stocks, lookback_days=10):
        """RSI 골든 크로스 발생 종목 찾기 (MACD 골든 크로스 이전 10일 이내)"""
        if not self.silent:
            print(f"\n{'='*60}")
            print(f"2단계: RSI 골든 크로스 종목 검색 (MACD 이전 {lookback_days}일 이내)")
            print(f"{'='*60}")
        
        rsi_stocks = []
        
        for stock_info in candidate_stocks:
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            macd_gc_index = stock_info['macd_golden_cross_index']
            
            # 종목 시계열 데이터 추출
            timeseries = DataLoader.get_stock_timeseries(self.trading_days, stock_code)
            
            if len(timeseries) < 30:
                continue
            
            closes = [t['close'] for t in timeseries]
            
            # RSI 계산
            rsi_line = TechnicalIndicators.calculate_rsi(closes, 14)
            rsi_signal = TechnicalIndicators.calculate_ema([r for r in rsi_line if r is not None], 9)
            
            # RSI 시그널 앞부분을 None으로 맞춤
            none_count = len([r for r in rsi_line if r is None])
            rsi_signal_aligned = [None] * none_count + rsi_signal
            
            # MACD 골든 크로스 이전 lookback_days 이내에서 RSI 골든 크로스 찾기
            start_index = max(0, macd_gc_index - lookback_days)
            end_index = macd_gc_index
            
            rsi_gc_info = self._find_golden_cross_in_range(
                rsi_line, rsi_signal_aligned, timeseries, start_index, end_index
            )
            
            if rsi_gc_info:
                rsi_stocks.append({
                    **stock_info,
                    'rsi_golden_cross_date': rsi_gc_info['date'],
                    'rsi_golden_cross_index': rsi_gc_info['index'],
                    'rsi_value': rsi_gc_info['value1'],
                    'rsi_signal': rsi_gc_info['value2']
                })
        
        if not self.silent:
            print(f"\n✓ RSI 골든 크로스 발견: {len(rsi_stocks)}개 종목")
            for stock in rsi_stocks[:10]:
                print(f"  - {stock['name']} ({stock['code']}): RSI GC {stock['rsi_golden_cross_date']}, MACD GC {stock['macd_golden_cross_date']}")
            
            if len(rsi_stocks) > 10:
                print(f"  ... 외 {len(rsi_stocks) - 10}개 종목")
        
        return rsi_stocks
    
    def find_ma_separation_golden_cross(self, candidate_stocks, lookback_days=10, low_period=12):
        """장단기 이격도 골든 크로스 발생 종목 찾기 (MACD 이전 10일 이내)"""
        if not self.silent:
            print(f"\n{'='*60}")
            print(f"3단계: 장단기 이격도 골든 크로스 종목 검색 (MACD 이전 {lookback_days}일 이내)")
            print(f"{'='*60}")
        
        separation_stocks = []
        
        for stock_info in candidate_stocks:
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            macd_gc_index = stock_info['macd_golden_cross_index']
            
            # 종목 시계열 데이터 추출
            timeseries = DataLoader.get_stock_timeseries(self.trading_days, stock_code)
            
            if len(timeseries) < 25:
                continue
            
            closes = [t['close'] for t in timeseries]
            lows = [t['low'] for t in timeseries]
            highs = [t['high'] for t in timeseries]
            
            # 5일선, 20일선 계산
            ma5 = TechnicalIndicators.calculate_ma(closes, 5)
            ma20 = TechnicalIndicators.calculate_ma(closes, 20)
            
            # MACD 골든 크로스 이전 lookback_days 이내에서 골든 크로스 찾기
            start_index = max(0, macd_gc_index - lookback_days)
            end_index = macd_gc_index
            
            ma_gc_info = self._find_golden_cross_in_range(
                ma5, ma20, timeseries, start_index, end_index
            )
            
            if ma_gc_info:
                # 진입가: MACD 골든 크로스 발생일의 종가
                entry_price = closes[macd_gc_index]
                
                # 현재가 및 이격도 계산
                current_close = closes[-1]
                current_ma20 = ma20[-1] if ma20[-1] is not None else current_close
                separation_rate = ((current_close - current_ma20) / current_ma20) * 100 if current_ma20 != 0 else 0
                
                # 수익률 계산 (진입가 대비 현재가)
                profit_rate = ((current_close - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                
                # 손절가/익절가 계산 (진입가 기준)
                # 손절가: MACD 발생일 기준 이전 low_period일간 최저가 (이전 저점)
                lookback_start = max(0, macd_gc_index - low_period)
                lookback_end = macd_gc_index + 1
                support_low = min(lows[lookback_start:lookback_end])
                
                # 손절폭 (진입가 기준)
                stop_loss_amount = entry_price - support_low
                
                # 손절가, 익절가 계산 (진입가 기준)
                stop_loss = int(support_low)
                stop_loss_pct = ((support_low - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                
                # 익절가: 손절폭의 2배 (진입가 기준)
                take_profit = int(entry_price + (stop_loss_amount * 2))
                take_profit_pct = ((take_profit - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                
                # 손익비 (Risk:Reward = 1:2)
                risk_reward_ratio = 2.0
                
                separation_stocks.append({
                    **stock_info,
                    'ma_golden_cross_date': ma_gc_info['date'],
                    'ma_golden_cross_index': ma_gc_info['index'],
                    'ma5_value': ma_gc_info['value1'],
                    'ma20_value': ma_gc_info['value2'],
                    'entry_price': int(entry_price),
                    'current_price': int(current_close),
                    'profit_rate': round(profit_rate, 2),
                    'current_separation_rate': round(separation_rate, 2),
                    'stop_loss': stop_loss,
                    'stop_loss_pct': round(stop_loss_pct, 2),
                    'take_profit': take_profit,
                    'take_profit_pct': round(take_profit_pct, 2),
                    'risk_reward_ratio': risk_reward_ratio,
                    'support_low': int(support_low)
                })
        
        if not self.silent:
            print(f"\n✓ 장단기 이격도 골든 크로스 발견: {len(separation_stocks)}개 종목")
            for stock in separation_stocks[:10]:
                print(f"  - {stock['name']} ({stock['code']}): MA GC {stock['ma_golden_cross_date']}, "
                      f"진입가 {stock['entry_price']:,}원 → 현재가 {stock['current_price']:,}원 ({stock['profit_rate']:+.1f}%), "
                      f"손절 {stock['stop_loss']:,}원 ({stock['stop_loss_pct']:+.1f}%), "
                      f"익절 {stock['take_profit']:,}원 ({stock['take_profit_pct']:+.1f}%)")
            
            if len(separation_stocks) > 10:
                print(f"  ... 외 {len(separation_stocks) - 10}개 종목")
        
        return separation_stocks
    
    def _find_golden_cross(self, line1, line2, timeseries, start_date=None, end_date=None):
        """골든 크로스 찾기 (전체 또는 지정 기간)"""
        start_index = 1  # 0이 아닌 1부터 (골든크로스는 이전 값과 비교 필요)
        end_index = len(timeseries)
        
        if start_date:
            # start_date에 해당하는 인덱스 찾기
            for i, t in enumerate(timeseries):
                if t['date'] >= start_date:
                    start_index = max(1, i)  # 최소 1
                    break
        
        if end_date:
            # end_date에 해당하는 인덱스 찾기
            for i, t in enumerate(timeseries):
                if t['date'] > end_date:
                    end_index = i
                    break
        
        return self._find_golden_cross_in_range(line1, line2, timeseries, start_index, end_index)
    
    def _find_golden_cross_in_range(self, line1, line2, timeseries, start_index, end_index):
        """지정된 범위에서 골든 크로스 찾기 (역순: 최신 신호 우선)"""
        for i in range(end_index - 1, start_index, -1):
            if (line1[i] is not None and line2[i] is not None and
                line1[i-1] is not None and line2[i-1] is not None):
                
                # 골든 크로스: line1이 line2를 아래에서 위로 돌파
                if line1[i-1] <= line2[i-1] and line1[i] > line2[i]:
                    return {
                        'date': timeseries[i]['date'],
                        'index': i,
                        'value1': round(line1[i], 2),
                        'value2': round(line2[i], 2)
                    }
        
        return None


def save_results(results, start_date, end_date):
    """결과를 CSV 파일로 저장"""
    year = end_date[:4]
    output_dir = f'data/json/kospi200/{year}/result'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'macd_rsi_separation_{start_date}_{end_date}.csv')
    
    # 신호일 기준으로 정렬 (MACD 골든크로스 날짜)
    sorted_results = sorted(results, key=lambda x: x['macd_golden_cross_date'])
    
    if not sorted_results:
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['전략', 'MACD + RSI + 이격도 골든크로스'])
            writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
            writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(['선택종목수', '0'])
        print(f"\n{'='*60}")
        print(f"✓ 결과 저장 완료: {output_file}")
        print(f"{'='*60}")
        return
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['전략', 'MACD + RSI + 이격도 골든크로스'])
        writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
        writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(['선택종목수', str(len(sorted_results))])
        writer.writerow([])
        
        if 'backtest' in sorted_results[0]:
            headers = [
                'MACD신호일', '종목코드', '종목명', 'RSI신호일', '이격도신호일',
                '진입가', '현재가', '수익률(%)',
                'MACD', 'Signal', 'RSI', 'RSI_Signal', 'MA5', 'MA20',
                '손절가', '손절률(%)', '익절가', '익절률(%)', '지지선',
                '백테스트_진입일', '백테스트_진입가', '백테스트_청산일', '백테스트_청산가',
                '백테스트_청산사유', '백테스트_수익률(%)'
            ]
        else:
            headers = [
                'MACD신호일', '종목코드', '종목명', 'RSI신호일', '이격도신호일',
                '진입가', '현재가', '수익률(%)',
                'MACD', 'Signal', 'RSI', 'RSI_Signal', 'MA5', 'MA20',
                '손절가', '손절률(%)', '익절가', '익절률(%)', '지지선'
            ]
        
        writer.writerow(headers)
        
        for stock in sorted_results:
            row = [
                stock['macd_golden_cross_date'],
                stock['code'],
                stock['name'],
                stock['rsi_golden_cross_date'],
                stock['ma_separation_golden_cross_date'],
                stock['entry_price'],
                stock['current_price'],
                stock['profit_rate'],
                stock['macd_value'],
                stock['macd_signal'],
                stock['rsi_value'],
                stock['rsi_signal'],
                stock['ma5'],
                stock['ma20'],
                stock['stop_loss'],
                stock['stop_loss_pct'],
                stock['take_profit'],
                stock['take_profit_pct'],
                stock['support_low']
            ]
            
            if 'backtest' in stock:
                bt = stock['backtest']
                row.extend([
                    bt['entry_date'],
                    bt['entry_price'],
                    bt['exit_date'],
                    bt['exit_price'],
                    bt['exit_reason'],
                    bt['profit_rate']
                ])
            
            writer.writerow(row)
    
    print(f"\n{'='*60}")
    print(f"✓ 결과 저장 완료: {output_file}")
    print(f"{'='*60}")


def backtest_stocks(results, trading_days, end_date, silent=False):
    """백테스팅: 익일 시가 매수 후 손절/익절 도달 여부 확인"""
    if not silent:
        print(f"\n{'='*80}")
        print(f"백테스팅 실행 중...")
        print(f"{'='*80}\n")
    
    backtested_results = []
    
    for stock in results:
        stock_code = stock['code']
        stock_name = stock['name']
        macd_date = stock['macd_golden_cross_date']
        entry_price = stock['entry_price']
        stop_loss = stock['stop_loss']
        take_profit = stock['take_profit']
        
        # 해당 종목의 시계열 데이터 추출
        stock_data = []
        for day in trading_days:
            if day['is_holiday']:
                continue
            stock_info = next((s for s in day['stocks'] if s['code'] == stock_code), None)
            if stock_info:
                stock_data.append({
                    'date': day['date'],
                    'open': stock_info['open'],
                    'high': stock_info['high'],
                    'low': stock_info['low'],
                    'close': stock_info['close']
                })
        
        # MACD 골든 크로스 발생일 찾기
        macd_index = next((i for i, d in enumerate(stock_data) if d['date'] == macd_date), None)
        
        if macd_index is None or macd_index >= len(stock_data) - 1:
            # 다음 날이 없으면 백테스팅 불가
            continue
        
        # 익일 시가로 매수
        buy_index = macd_index + 1
        buy_price = stock_data[buy_index]['open']
        buy_date = stock_data[buy_index]['date']
        
        # 손절가/익절가 도달 여부 확인 (익일부터 체크)
        sell_date = None
        sell_price = None
        sell_reason = None
        
        for i in range(buy_index, len(stock_data)):
            day_data = stock_data[i]
            
            # 당일 저가가 손절가 이하로 떨어졌는지 확인
            if day_data['low'] <= stop_loss:
                sell_date = day_data['date']
                sell_price = stop_loss
                sell_reason = '손절'
                break
            
            # 당일 고가가 익절가 이상으로 올랐는지 확인
            if day_data['high'] >= take_profit:
                sell_date = day_data['date']
                sell_price = take_profit
                sell_reason = '익절'
                break
        
        # 매도하지 않았다면 홀딩
        if sell_date is None:
            current_price = stock_data[-1]['close']
            sell_date = stock_data[-1]['date']
            sell_price = current_price
            sell_reason = '홀딩'
        
        # 수익률 계산
        profit_rate = ((sell_price - buy_price) / buy_price) * 100 if buy_price != 0 else 0
        
        backtested_results.append({
            **stock,
            'backtest': {
                'buy_date': buy_date,
                'buy_price': int(buy_price),
                'sell_date': sell_date,
                'sell_price': int(sell_price),
                'sell_reason': sell_reason,
                'profit_rate': round(profit_rate, 2),
                'days_held': len([d for d in stock_data[buy_index:] if d['date'] <= sell_date])
            }
        })
        
        if not silent:
            status_icon = '✅' if sell_reason == '익절' else '❌' if sell_reason == '손절' else '⏳'
            print(f"{status_icon} {stock_name} ({stock_code}): {buy_date}({buy_price:,}원) → {sell_date}({sell_price:,}원) "
                  f"[{sell_reason}] {profit_rate:+.2f}%")
    
    return backtested_results


def print_final_summary(results, silent=False):
    """최종 결과 요약 출력"""
    if not silent:
        print(f"\n{'='*80}")
        print(f"최종 선택 종목: {len(results)}개")
        print(f"{'='*80}")
    
    if not results:
        print("선택된 종목이 없습니다.")
        return
    
    if not silent:
        # 골든 크로스 정보 테이블
        print(f"\n[골든 크로스 발생 시점]")
        print(f"{'종목명':<12} {'코드':<8} {'MACD GC':<10} {'RSI GC':<10} {'MA GC':<10} {'이격도':<8}")
        print("-" * 68)
        
        for stock in results:
            name = stock['name'][:10] + '..' if len(stock['name']) > 12 else stock['name']
            print(f"{name:<12} {stock['code']:<8} "
                  f"{stock['macd_golden_cross_date']:<10} "
                  f"{stock['rsi_golden_cross_date']:<10} "
                  f"{stock['ma_golden_cross_date']:<10} "
                  f"{stock['current_separation_rate']:>6.2f}%")
        
        # 매매 전략 테이블
        print(f"\n[매매 전략 (손절/익절)]")
        print(f"{'종목명':<12} {'진입가':>10} {'현재가':>10} {'수익률':>8} {'손절가':>10} {'손절률':>8} {'익절가':>10} {'익절률':>8} {'손익비':<8}")
        print("-" * 105)
        
        for stock in results:
            name = stock['name'][:10] + '..' if len(stock['name']) > 12 else stock['name']
            print(f"{name:<12} "
                  f"{stock['entry_price']:>10,}원 "
                  f"{stock['current_price']:>10,}원 "
                  f"{stock['profit_rate']:>7.2f}% "
                  f"{stock['stop_loss']:>10,}원 "
                  f"{stock['stop_loss_pct']:>7.2f}% "
                  f"{stock['take_profit']:>10,}원 "
                  f"{stock['take_profit_pct']:>7.2f}% "
                  f"1:{stock['risk_reward_ratio']:.0f}")
        
        # 백테스팅 결과 테이블 (있는 경우)
        if results and 'backtest' in results[0]:
            print(f"\n[백테스팅 결과]")
            print(f"{'종목명':<12} {'매수일':>10} {'매수가':>10} {'매도일':>10} {'매도가':>10} {'결과':>8} {'수익률':>8} {'보유일':>6}")
            print("-" * 90)
            
            for stock in results:
                name = stock['name'][:10] + '..' if len(stock['name']) > 12 else stock['name']
                bt = stock['backtest']
                result_icon = '✅익절' if bt['sell_reason'] == '익절' else '❌손절' if bt['sell_reason'] == '손절' else '⏳홀딩'
                print(f"{name:<12} "
                      f"{bt['buy_date']:>10} "
                      f"{bt['buy_price']:>10,}원 "
                      f"{bt['sell_date']:>10} "
                      f"{bt['sell_price']:>10,}원 "
                      f"{result_icon:>8} "
                      f"{bt['profit_rate']:>7.2f}% "
                      f"{bt['days_held']:>5}일")
        
        # 통계 정보
        print(f"\n[통계 정보]")
        print(f"  - 평균 이격도: {sum(s['current_separation_rate'] for s in results) / len(results):.2f}%")
        print(f"  - 평균 진입가: {sum(s['entry_price'] for s in results) / len(results):,.0f}원")
        print(f"  - 평균 현재가: {sum(s['current_price'] for s in results) / len(results):,.0f}원")
        print(f"  - 평균 수익률: {sum(s['profit_rate'] for s in results) / len(results):+.2f}%")
        print(f"  - 평균 손절률: {sum(s['stop_loss_pct'] for s in results) / len(results):.2f}%")
        print(f"  - 평균 익절률: {sum(s['take_profit_pct'] for s in results) / len(results):.2f}%")
    
    # 개별 종목 상세 정보
    print(f"\n[종목별 상세 정보]")
    for idx, stock in enumerate(results, 1):
        print(f"\n{idx}. {stock['name']} ({stock['code']})")
        print(f"   진입가: {stock['entry_price']:,}원 (MACD GC일) | 현재가: {stock['current_price']:,}원 | 수익률: {stock['profit_rate']:+.2f}%")
        print(f"   이격도: {stock['current_separation_rate']:+.2f}%")
        print(f"   골든 크로스: MA({stock['ma_golden_cross_date']}) → "
              f"RSI({stock['rsi_golden_cross_date']}) → "
              f"MACD({stock['macd_golden_cross_date']})")
        print(f"   💔 손절가: {stock['stop_loss']:,}원 ({stock['stop_loss_pct']:+.2f}%) - MACD 발생일 기준 이전 저점")
        print(f"   💰 익절가: {stock['take_profit']:,}원 ({stock['take_profit_pct']:+.2f}%) - 손절폭의 2배")
        print(f"   📊 손익비: 1:{stock['risk_reward_ratio']:.0f}")
        
        # 백테스팅 정보 (있는 경우)
        if 'backtest' in stock:
            bt = stock['backtest']
            result_text = f"{'✅ 익절' if bt['sell_reason'] == '익절' else '❌ 손절' if bt['sell_reason'] == '손절' else '⏳ 홀딩'}"
            print(f"   🔍 백테스트: {bt['buy_date']}({bt['buy_price']:,}원) → {bt['sell_date']}({bt['sell_price']:,}원) "
                  f"| {result_text} | {bt['profit_rate']:+.2f}% | {bt['days_held']}일 보유")


def main():
    parser = argparse.ArgumentParser(
        description='MACD, RSI, 이격도 골든 크로스 종목 선별 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  1. 특정 기간 분석:
     python macd_rsi_separation.py --from 20250101 --to 20250131

  2. 어제 (마지막 거래일) 분석 (기본):
     python macd_rsi_separation.py

  3. 백테스팅 (특정 기간 + 실제 수익률 계산):
     python macd_rsi_separation.py --from 20250101 --to 20250131 --backtest

  4. 전저점 기간 지정 (10일):
     python macd_rsi_separation.py --from 20250101 --to 20250131 --low_period 10

선별 기준:
  1. MACD 골든 크로스 발생 종목
  2. MACD 골든 크로스 이전 10일 이내 RSI 골든 크로스 발생
  3. MACD 골든 크로스 이전 10일 이내 5일선이 20일선을 상향 돌파

백테스팅:
  - MACD GC 다음날 시가에 매수
  - 손절가 또는 익절가 도달 시 매도
  - 미도달 시 현재가 기준 홀딩 수익률 계산

골든 크로스: 빠른 선이 느린 선을 아래에서 위로 돌파
순서: MA(5x20) 골든 크로스 → RSI 골든 크로스 → MACD 골든 크로스 (10일 이내)
        '''
    )
    
    parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    parser.add_argument('--backtest', action='store_true', help='백테스팅 모드 (--from, --to 필수)')
    parser.add_argument('--low_period', type=int, default=12, help='전저점 계산 기간 (일, 기본값: 12)')
    parser.add_argument('--silent', action='store_true', help='간략 출력 모드 (최종 결과만 표시)')
    
    args = parser.parse_args()
    
    # 백테스팅 모드 검증
    if args.backtest and (not args.from_date or not args.to_date):
        print("❌ 백테스팅 모드는 --from, --to 옵션이 필수입니다.")
        print("\n사용 예시:")
        print("  python macd_rsi_separation.py --from 20250101 --to 20250131 --backtest")
        sys.exit(1)
    
    if not args.silent:
        print("=" * 60)
        if args.backtest:
            print("MACD, RSI, 이격도 골든 크로스 종목 선별 + 백테스팅")
        else:
            print("MACD, RSI, 이격도 골든 크로스 종목 선별 프로그램")
        print("=" * 60)
        print()
    
    # 날짜 범위 설정
    if args.from_date:
        start_date = args.from_date
        end_date = args.to_date if args.to_date else datetime.now().strftime("%Y%m%d")
    else:
        # 기본값: 어제 (마지막 거래일 1일)
        # 어제가 휴장일이면 데이터 로드 시 자동으로 가장 최근 거래일이 선택됨
        yesterday = datetime.now() - timedelta(days=1)
        end_date = yesterday.strftime("%Y%m%d")
        start_date = end_date  # 1일만 분석
    
    # 분석을 위해 더 많은 데이터 필요 (최소 150일: 충분한 거래일 확보)
    extended_start = (datetime.strptime(start_date, "%Y%m%d") - timedelta(days=150)).strftime("%Y%m%d")
    
    if not args.silent:
        print(f"분석 기간: {start_date} ~ {end_date}")
        print(f"데이터 로드 기간: {extended_start} ~ {end_date} (기술적 지표 계산용)\n")
    
    # 데이터 로드
    trading_days = DataLoader.load_kospi200_data(extended_start, end_date)
    
    if trading_days is None:
        sys.exit(1)
    
    if not args.silent:
        print(f"✓ 로드된 거래일: {len(trading_days)}일")
        print(f"  첫 거래일: {trading_days[0]['date']}")
        print(f"  마지막 거래일: {trading_days[-1]['date']}")
        print(f"  종목 수: {len(trading_days[-1]['stocks'])}개\n")
    
    # 종목 선별
    screener = StockScreener(trading_days, silent=args.silent)
    
    if not args.silent:
        print(f"MACD 검색 범위: {start_date} ~ {end_date}")
    
    # 1단계: MACD 골든 크로스
    macd_stocks = screener.find_macd_golden_cross(start_date=start_date, end_date=end_date)
    
    if not macd_stocks:
        print("\n⚠️  MACD 골든 크로스 종목이 없어 분석을 종료합니다.")
        save_results([], start_date, end_date)
        sys.exit(0)
    
    # 2단계: RSI 골든 크로스 (MACD 이전 10일 이내)
    rsi_stocks = screener.find_rsi_golden_cross(macd_stocks, lookback_days=10)
    
    if not rsi_stocks:
        print("\n⚠️  RSI 골든 크로스 종목이 없어 분석을 종료합니다.")
        save_results([], start_date, end_date)
        sys.exit(0)
    
    # 3단계: 장단기 이격도 골든 크로스 (MACD 이전 10일 이내)
    final_stocks = screener.find_ma_separation_golden_cross(rsi_stocks, lookback_days=10, low_period=args.low_period)
    
    if not final_stocks:
        print("\n⚠️  장단기 이격도 골든 크로스 종목이 없습니다.")
        save_results([], start_date, end_date)
        sys.exit(0)
    
    # 백테스팅 실행 (옵션이 주어진 경우)
    if args.backtest:
        backtested_stocks = backtest_stocks(final_stocks, trading_days, end_date, silent=args.silent)
        
        # 최종 결과 출력 (백테스팅 포함) - silent 모드에서 먼저 표시
        print_final_summary(backtested_stocks, silent=args.silent)
        
        # 백테스팅 통계
        print(f"\n{'='*80}")
        print(f"백테스팅 통계")
        print(f"{'='*80}")
        
        total = len(backtested_stocks)
        profit_count = len([s for s in backtested_stocks if s['backtest']['sell_reason'] == '익절'])
        loss_count = len([s for s in backtested_stocks if s['backtest']['sell_reason'] == '손절'])
        hold_count = len([s for s in backtested_stocks if s['backtest']['sell_reason'] == '홀딩'])
        
        avg_profit = sum(s['backtest']['profit_rate'] for s in backtested_stocks) / total if total > 0 else 0
        win_rate = (profit_count / total * 100) if total > 0 else 0
        
        print(f"총 종목: {total}개")
        print(f"익절: {profit_count}개 ({profit_count/total*100:.1f}%)")
        print(f"손절: {loss_count}개 ({loss_count/total*100:.1f}%)")
        print(f"홀딩: {hold_count}개 ({hold_count/total*100:.1f}%)")
        print(f"평균 수익률: {avg_profit:+.2f}%")
        print(f"승률: {win_rate:.1f}%")
        
        # 결과 저장 (백테스팅 포함)
        save_results(backtested_stocks, start_date, end_date)
    else:
        # 최종 결과 출력
        print_final_summary(final_stocks, silent=args.silent)
        
        # 결과 저장
        save_results(final_stocks, start_date, end_date)
    
    if not args.silent:
        print("\n✅ 분석 완료!")


if __name__ == "__main__":
    main()

