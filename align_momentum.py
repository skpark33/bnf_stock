#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
정배열 + 모멘텀 전략 종목 선별 프로그램

전략:
1. 이동평균선 정배열: 5일 > 20일 > 60일 > 120일
2. 거래량 증가 추세: 최근 5일 평균 > 최근 20일 평균
3. Stochastic 골든크로스: %K가 %D 상향 돌파 (둘 다 80 이하)
4. ADX > 25: 강한 추세 확인

손절/익절:
- 손절: -8% 고정
- 1차 익절: +13% (50% 청산)
- 2차 익절: +21% (나머지 50% 청산)
"""

import json
import os
import sys
import argparse
import csv
from datetime import datetime, timedelta


class TechnicalIndicators:
    """기술적 지표 계산 클래스"""
    
    @staticmethod
    def calculate_ma(data, period):
        """이동평균 계산 (None 값 처리 포함)"""
        if len(data) < period:
            return [None] * len(data)
        
        result = [None] * (period - 1)
        for i in range(period - 1, len(data)):
            window = data[i-period+1:i+1]
            # None 값 필터링
            valid_values = [v for v in window if v is not None]
            if len(valid_values) == period:  # 모든 값이 유효한 경우만 계산
                result.append(sum(valid_values) / period)
            else:
                result.append(None)
        
        return result
    
    @staticmethod
    def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
        """
        Stochastic Oscillator 계산
        %K = (현재가 - N일 최저가) / (N일 최고가 - N일 최저가) × 100
        %D = %K의 3일 이동평균
        """
        if len(closes) < k_period:
            return [None] * len(closes), [None] * len(closes)
        
        k_values = [None] * (k_period - 1)
        
        for i in range(k_period - 1, len(closes)):
            period_high = max(highs[i-k_period+1:i+1])
            period_low = min(lows[i-k_period+1:i+1])
            
            if period_high == period_low:
                k_values.append(50.0)  # 범위가 0이면 중간값
            else:
                k = ((closes[i] - period_low) / (period_high - period_low)) * 100
                k_values.append(k)
        
        # %D = %K의 이동평균
        d_values = TechnicalIndicators.calculate_ma(k_values, d_period)
        
        return k_values, d_values
    
    @staticmethod
    def calculate_adx(highs, lows, closes, period=14):
        """
        ADX (Average Directional Index) 계산
        추세의 강도를 측정 (0~100)
        """
        if len(closes) < period + 1:
            return [None] * len(closes)
        
        # True Range 계산
        tr_list = [None]
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        # +DM, -DM 계산
        plus_dm = [None]
        minus_dm = [None]
        
        for i in range(1, len(highs)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
        
        # 평활화
        atr = TechnicalIndicators.calculate_ma(tr_list, period)
        plus_di_list = []
        minus_di_list = []
        
        for i in range(len(atr)):
            if atr[i] is not None and atr[i] != 0:
                plus_di = (TechnicalIndicators._smooth(plus_dm, period, i) / atr[i]) * 100
                minus_di = (TechnicalIndicators._smooth(minus_dm, period, i) / atr[i]) * 100
                plus_di_list.append(plus_di)
                minus_di_list.append(minus_di)
            else:
                plus_di_list.append(None)
                minus_di_list.append(None)
        
        # DX 계산
        dx_list = []
        for plus_di, minus_di in zip(plus_di_list, minus_di_list):
            if plus_di is not None and minus_di is not None:
                di_sum = plus_di + minus_di
                if di_sum == 0:
                    dx_list.append(0)
                else:
                    dx = (abs(plus_di - minus_di) / di_sum) * 100
                    dx_list.append(dx)
            else:
                dx_list.append(None)
        
        # ADX = DX의 이동평균
        adx = TechnicalIndicators.calculate_ma(dx_list, period)
        
        return adx
    
    @staticmethod
    def _smooth(data, period, index):
        """데이터 평활화 (이동평균)"""
        if index < period - 1:
            return 0
        valid_data = [d for d in data[index-period+1:index+1] if d is not None]
        return sum(valid_data) / len(valid_data) if valid_data else 0
    
    @staticmethod
    def calculate_ema(data, period):
        """지수이동평균 계산"""
        if len(data) < period:
            return [None] * len(data)
        
        multiplier = 2 / (period + 1)
        result = [None] * (period - 1)
        
        # 첫 EMA는 SMA로 시작
        sma = sum(data[:period]) / period
        result.append(sma)
        
        for i in range(period, len(data)):
            ema = (data[i] - result[-1]) * multiplier + result[-1]
            result.append(ema)
        
        return result
    
    @staticmethod
    def calculate_macd(data, fast=12, slow=26, signal=9):
        """MACD 계산"""
        fast_ema = TechnicalIndicators.calculate_ema(data, fast)
        slow_ema = TechnicalIndicators.calculate_ema(data, slow)
        
        macd_line = []
        for f, s in zip(fast_ema, slow_ema):
            if f is not None and s is not None:
                macd_line.append(f - s)
            else:
                macd_line.append(None)
        
        # Signal line
        valid_macd = [m if m is not None else 0 for m in macd_line]
        signal_line = TechnicalIndicators.calculate_ema(valid_macd, signal)
        
        # Histogram
        histogram = []
        for m, s in zip(macd_line, signal_line):
            if m is not None and s is not None:
                histogram.append(m - s)
            else:
                histogram.append(None)
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_rsi(prices, period=14, signal_period=9):
        """RSI 계산 (RSI Line과 Signal Line)"""
        if len(prices) < period + 1:
            return [None] * len(prices), [None] * len(prices)
        
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
        
        # RSI Signal Line 계산
        rsi_signal = TechnicalIndicators.calculate_ma(rsi_values, signal_period)
        
        return rsi_values, rsi_signal


class DataLoader:
    """데이터 로딩 클래스"""
    
    @staticmethod
    def load_kospi200_data(start_date, end_date):
        """KOSPI 200 데이터 로드"""
        base_dir = "data/json/kospi200"
        
        if not os.path.exists(base_dir):
            print(f"오류: {base_dir} 디렉토리가 없습니다.")
            print(f"먼저 get_data.py를 실행하여 데이터를 수집하세요.")
            sys.exit(1)
        
        # 연도별 데이터 로드
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        
        all_data = {}
        
        for year in range(start_year, end_year + 1):
            year_file = f"{base_dir}/{year}/kospi200_data.json"
            
            if not os.path.exists(year_file):
                print(f"경고: {year}년 데이터 파일이 없습니다: {year_file}")
                continue
            
            print(f"데이터 로드 중: {year}년 ({year_file})")
            
            with open(year_file, 'r', encoding='utf-8') as f:
                year_json = json.load(f)
                
                # 배열 형태의 데이터 처리
                if 'data' in year_json:
                    year_data_list = year_json['data']
                else:
                    # 기존 dict 형태도 지원
                    year_data_list = [{'date': k, **v} for k, v in year_json.items() if k not in ['year', 'generated_at', 'total_days']]
                
                total_days = len(year_data_list)
                filtered_days = 0
                
                # 날짜 범위 필터링
                for day_data in year_data_list:
                    date_key = day_data['date']
                    if start_date <= date_key <= end_date:
                        all_data[date_key] = {
                            'is_holiday': day_data.get('is_holiday', False),
                            'stocks': day_data.get('stocks', [])
                        }
                        filtered_days += 1
                
                print(f"  - {year}년 전체: {total_days}일, 필터링 후: {filtered_days}일")
        
        if not all_data:
            print(f"오류: {start_date}~{end_date} 범위의 데이터가 없습니다.")
            print(f"\n확인 사항:")
            print(f"  1. {base_dir}/2024/kospi200_data.json 파일이 존재하는지 확인")
            print(f"  2. {base_dir}/2025/kospi200_data.json 파일이 존재하는지 확인")
            print(f"  3. 파일에 {start_date}~{end_date} 범위의 데이터가 포함되어 있는지 확인")
            sys.exit(1)
        
        # 날짜순 정렬
        sorted_dates = sorted(all_data.keys())
        trading_days = {date: all_data[date] for date in sorted_dates}
        
        print(f"\n총 로드된 거래일 수: {len(trading_days)}일")
        print(f"첫 거래일: {sorted_dates[0]}, 마지막 거래일: {sorted_dates[-1]}")
        
        return trading_days
    
    @staticmethod
    def get_stock_timeseries(trading_days, stock_code):
        """특정 종목의 시계열 데이터 추출"""
        timeseries = []
        
        for date, day_data in trading_days.items():
            if day_data.get('is_holiday'):
                continue
            
            stocks = day_data.get('stocks', [])
            for stock in stocks:
                if stock['code'] == stock_code:
                    timeseries.append({
                        'date': date,
                        'open': stock['open'],
                        'high': stock['high'],
                        'low': stock['low'],
                        'close': stock['close'],
                        'volume': stock['volume']
                    })
                    break
        
        return timeseries


class StockScreener:
    """종목 선별 클래스"""
    
    def __init__(self, trading_days, silent=False):
        self.trading_days = trading_days
        self.silent = silent
    
    def find_align_momentum_stocks(self, start_date=None, end_date=None, low_period=12, debug=False):
        """정배열 + 모멘텀 전략 종목 찾기"""
        selected_stocks = []
        
        debug_stats = {
            'total_checked': 0,
            'align_filter': 0,
            'volume_trend': 0,
            'stoch_cross': 0,
            'adx_strong': 0,
            'macd_positive': 0,
            'rsi_neutral': 0,
            'all_passed': 0
        }
        
        # KOSPI 200 종목 코드 수집
        stock_codes = set()
        for day_data in self.trading_days.values():
            if not day_data.get('is_holiday'):
                for stock in day_data.get('stocks', []):
                    stock_codes.add((stock['code'], stock['name']))
        
        if not self.silent:
            print(f"\n분석 대상: {len(stock_codes)}개 종목")
        
        # 각 종목별 분석
        for idx, (stock_code, stock_name) in enumerate(sorted(stock_codes), 1):
            if not self.silent and idx % 50 == 0:
                print(f"  진행 중: {idx}/{len(stock_codes)} 종목 분석...")
            
            # 종목 시계열 데이터 가져오기
            timeseries = DataLoader.get_stock_timeseries(self.trading_days, stock_code)
            
            if len(timeseries) < 150:  # 120일 + 여유
                continue
            
            closes = [t['close'] for t in timeseries]
            highs = [t['high'] for t in timeseries]
            volumes = [t['volume'] for t in timeseries]
            lows = [t['low'] for t in timeseries]
            
            # 이동평균 계산
            ma5 = TechnicalIndicators.calculate_ma(closes, 5)
            ma20 = TechnicalIndicators.calculate_ma(closes, 20)
            ma60 = TechnicalIndicators.calculate_ma(closes, 60)
            ma120 = TechnicalIndicators.calculate_ma(closes, 120)
            
            # 거래량 이동평균
            vol_ma5 = TechnicalIndicators.calculate_ma(volumes, 5)
            vol_ma20 = TechnicalIndicators.calculate_ma(volumes, 20)
            
            # Stochastic 계산
            stoch_k, stoch_d = TechnicalIndicators.calculate_stochastic(highs, lows, closes)
            
            # ADX 계산
            adx = TechnicalIndicators.calculate_adx(highs, lows, closes)
            
            # MACD 계산
            macd_line, signal_line, _ = TechnicalIndicators.calculate_macd(closes)
            
            # RSI 계산
            rsi_line, _ = TechnicalIndicators.calculate_rsi(closes)
            
            # 검색 범위 설정
            search_start_idx = 120  # 최소 120일 이후부터
            search_end_idx = len(timeseries)
            
            if start_date:
                for i, t in enumerate(timeseries):
                    if t['date'] >= start_date:
                        search_start_idx = max(120, i)
                        break
            
            if end_date:
                for i, t in enumerate(timeseries):
                    if t['date'] > end_date:
                        search_end_idx = i
                        break
            
            # 전략 조건 확인 (순방향: 초기 신호 우선)
            for i in range(search_start_idx, search_end_idx):
                passed, stage = self._check_strategy_conditions(
                    i, closes, highs, volumes, lows, ma5, ma20, ma60, ma120,
                    vol_ma5, vol_ma20, stoch_k, stoch_d, adx, macd_line, signal_line, rsi_line, debug
                )
                
                if debug and stage > 0:
                    debug_stats['total_checked'] += 1
                    if stage >= 1: debug_stats['align_filter'] += 1
                    if stage >= 2: debug_stats['volume_trend'] += 1
                    if stage >= 3: debug_stats['stoch_cross'] += 1
                    if stage >= 4: debug_stats['adx_strong'] += 1
                    if stage >= 5: debug_stats['macd_positive'] += 1
                    if stage >= 6: debug_stats['rsi_neutral'] += 1
                    if passed: debug_stats['all_passed'] += 1
                
                if passed:
                    # 조건 만족 시점의 정보 수집
                    entry_price = closes[i]
                    current_close = closes[-1]
                    
                    # 단순 고정 퍼센트 손익
                    stop_loss = int(entry_price * 0.92)
                    stop_loss_pct = -8.0
                    
                    take_profit_1 = int(entry_price * 1.13)
                    take_profit_1_pct = 13.0
                    
                    take_profit_2 = int(entry_price * 1.21)
                    take_profit_2_pct = 21.0
                    
                    # 지지선 (참고용)
                    lookback_start = max(0, i - low_period)
                    lookback_end = i + 1
                    support_low = min(lows[lookback_start:lookback_end])
                    
                    profit_rate = ((current_close - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                    
                    selected_stocks.append({
                        'code': stock_code,
                        'name': stock_name,
                        'signal_date': timeseries[i]['date'],
                        'signal_index': i,
                        'entry_price': int(entry_price),
                        'current_price': int(current_close),
                        'profit_rate': round(profit_rate, 2),
                        'volume_ratio': round(vol_ma5[i] / vol_ma20[i], 2) if vol_ma20[i] and vol_ma20[i] != 0 else 0,
                        'stoch_k': round(stoch_k[i], 2) if stoch_k[i] is not None else 0,
                        'stoch_d': round(stoch_d[i], 2) if stoch_d[i] is not None else 0,
                        'adx': round(adx[i], 2) if adx[i] is not None else 0,
                        'ma5': int(ma5[i]) if ma5[i] is not None else 0,
                        'ma20': int(ma20[i]) if ma20[i] is not None else 0,
                        'ma60': int(ma60[i]) if ma60[i] is not None else 0,
                        'ma120': int(ma120[i]) if ma120[i] is not None else 0,
                        'stop_loss': stop_loss,
                        'stop_loss_pct': round(stop_loss_pct, 2),
                        'take_profit_1': take_profit_1,
                        'take_profit_1_pct': round(take_profit_1_pct, 2),
                        'take_profit_2': take_profit_2,
                        'take_profit_2_pct': round(take_profit_2_pct, 2),
                        'risk_reward_ratio': 1.625,
                        'support_low': int(support_low)
                    })
                    break  # 종목당 첫 신호만
        
        if not self.silent:
            print(f"\n✓ 전략 조건 만족 종목: {len(selected_stocks)}개")
            for stock in selected_stocks[:10]:
                print(f"  - {stock['name']} ({stock['code']}): {stock['signal_date']}, "
                      f"진입가 {stock['entry_price']:,}원 → 현재가 {stock['current_price']:,}원 ({stock['profit_rate']:+.1f}%), "
                      f"ADX {stock['adx']:.1f}")
            
            if len(selected_stocks) > 10:
                print(f"  ... 외 {len(selected_stocks) - 10}개 종목")
        
        if debug:
            print(f"\n{'='*60}")
            print(f"디버그 통계 (각 조건별 통과 비율)")
            print(f"{'='*60}")
            if debug_stats['total_checked'] > 0:
                print(f"0단계 - 검사 대상: {debug_stats['total_checked']:,}")
                print(f"1단계 - 정배열 (5>20>60>120): {debug_stats['align_filter']:,} / {debug_stats['total_checked']:,} ({debug_stats['align_filter']/debug_stats['total_checked']*100:.1f}%)")
                if debug_stats['align_filter'] > 0:
                    print(f"2단계 - 거래량 증가 추세: {debug_stats['volume_trend']:,} / {debug_stats['align_filter']:,} ({debug_stats['volume_trend']/debug_stats['align_filter']*100:.1f}%)")
                if debug_stats['volume_trend'] > 0:
                    print(f"3단계 - Stochastic 골든크로스: {debug_stats['stoch_cross']:,} / {debug_stats['volume_trend']:,} ({debug_stats['stoch_cross']/debug_stats['volume_trend']*100:.1f}%)")
                if debug_stats['stoch_cross'] > 0:
                    print(f"4단계 - ADX > 25: {debug_stats['adx_strong']:,} / {debug_stats['stoch_cross']:,} ({debug_stats['adx_strong']/debug_stats['stoch_cross']*100:.1f}%)")
                if debug_stats['adx_strong'] > 0:
                    print(f"5단계 - MACD > Signal: {debug_stats['macd_positive']:,} / {debug_stats['adx_strong']:,} ({debug_stats['macd_positive']/debug_stats['adx_strong']*100:.1f}%)")
                if debug_stats['macd_positive'] > 0:
                    print(f"6단계 - RSI 30~70: {debug_stats['rsi_neutral']:,} / {debug_stats['macd_positive']:,} ({debug_stats['rsi_neutral']/debug_stats['macd_positive']*100:.1f}%)")
                print(f"최종 선택: {debug_stats['all_passed']:,} 종목")
            else:
                print("분석할 데이터가 없습니다.")
        
        return selected_stocks
    
    def _check_strategy_conditions(self, idx, closes, highs, volumes, lows, ma5, ma20, ma60, ma120,
                                   vol_ma5, vol_ma20, stoch_k, stoch_d, adx, macd_line, signal_line, rsi_line, debug=False):
        """전략 조건 확인"""
        stage = 0
        
        if idx < 120:
            return False, stage
        
        # 인덱스 범위 및 필수 값 확인
        if (idx >= len(closes) or idx >= len(ma5) or idx >= len(ma20) or
            idx >= len(ma60) or idx >= len(ma120) or idx >= len(stoch_k) or
            idx >= len(stoch_d) or idx >= len(adx) or idx >= len(macd_line) or
            idx >= len(signal_line) or idx >= len(rsi_line)):
            return False, stage
        
        if None in [ma5[idx], ma20[idx], ma60[idx], ma120[idx], stoch_k[idx], stoch_d[idx], adx[idx], 
                    macd_line[idx], signal_line[idx], rsi_line[idx]]:
            return False, stage
        
        if idx == 0 or stoch_k[idx-1] is None or stoch_d[idx-1] is None:
            return False, stage
        
        # 1. 이동평균선 정배열: 5 > 20 > 60 > 120
        if not (ma5[idx] > ma20[idx] > ma60[idx] > ma120[idx]):
            return False, stage
        stage = 1
        
        # 2. 거래량 증가 추세: 5일 평균 > 20일 평균
        if vol_ma5[idx] is None or vol_ma20[idx] is None or vol_ma5[idx] <= vol_ma20[idx]:
            return False, stage
        stage = 2
        
        # 3. Stochastic 골든크로스: %K가 %D를 하향에서 상향 돌파 (둘 다 80 이하)
        if stoch_k[idx] > 80 or stoch_d[idx] > 80:
            return False, stage
        if stoch_k[idx-1] <= stoch_d[idx-1] and stoch_k[idx] > stoch_d[idx]:
            # 골든크로스 발생
            pass
        else:
            return False, stage
        stage = 3
        
        # 4. ADX > 25: 강한 추세 확인
        if adx[idx] <= 25:
            return False, stage
        stage = 4
        
        # 5. MACD > Signal: 상승 모멘텀 확인
        if macd_line[idx] <= signal_line[idx]:
            return False, stage
        stage = 5
        
        # 6. RSI 30~70: 과매수/과매도 배제
        if rsi_line[idx] < 30 or rsi_line[idx] > 70:
            return False, stage
        stage = 6
        
        return True, stage


def save_results(results, start_date, end_date):
    """결과 저장 (CSV 형식)"""
    year = end_date[:4]
    output_dir = f'data/json/kospi200/{year}/result'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f'{output_dir}/align_momentum_{start_date}_{end_date}.csv'
    
    # 신호일 기준으로 정렬
    sorted_results = sorted(results, key=lambda x: x['signal_date'])
    
    if not sorted_results:
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['전략', 'Align + Momentum Strategy'])
            writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
            writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(['선택종목수', '0'])
        print(f"\n{'='*60}")
        print(f"✓ 결과 저장 완료: {output_file}")
        print(f"{'='*60}")
        return
    
    # CSV 작성
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['전략', 'Align + Momentum Strategy'])
        writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
        writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(['선택종목수', str(len(sorted_results))])
        
        # 백테스팅 통계
        if 'backtest' in sorted_results[0]:
            writer.writerow([])
            writer.writerow(['=== 백테스팅 통계 ==='])
            
            total = len(sorted_results)
            profits = [s['backtest']['profit_rate'] for s in sorted_results]
            
            stop_loss_count = sum(1 for s in sorted_results if s['backtest']['exit_reason'] == 'stop_loss')
            take_profit_2_count = sum(1 for s in sorted_results if s['backtest']['exit_reason'] == 'take_profit_2')
            holding_50_count = sum(1 for s in sorted_results if s['backtest']['exit_reason'] == 'holding_50')
            holding_100_count = sum(1 for s in sorted_results if s['backtest']['exit_reason'] == 'holding_100')
            
            win_count = sum(1 for p in profits if p > 0)
            lose_count = sum(1 for p in profits if p < 0)
            
            avg_profit = sum(profits) / len(profits) if profits else 0
            max_profit = max(profits) if profits else 0
            min_profit = min(profits) if profits else 0
            
            writer.writerow(['총 종목 수', total])
            writer.writerow(['승', f'{win_count}개 ({win_count/total*100:.1f}%)'])
            writer.writerow(['패', f'{lose_count}개 ({lose_count/total*100:.1f}%)'])
            writer.writerow(['손절', f'{stop_loss_count}개 ({stop_loss_count/total*100:.1f}%)'])
            writer.writerow(['2차 익절 (21%, 전량 청산)', f'{take_profit_2_count}개 ({take_profit_2_count/total*100:.1f}%)'])
            writer.writerow(['1차 익절 후 홀딩', f'{holding_50_count}개 ({holding_50_count/total*100:.1f}%)'])
            writer.writerow(['전량 홀딩', f'{holding_100_count}개 ({holding_100_count/total*100:.1f}%)'])
            writer.writerow(['평균 수익률', f'{avg_profit:+.2f}%'])
            writer.writerow(['최대 수익률', f'{max_profit:+.2f}%'])
            writer.writerow(['최소 수익률', f'{min_profit:+.2f}%'])
        
        writer.writerow([])
        
        # 컬럼 헤더
        if 'backtest' in sorted_results[0]:
            headers = [
                '신호일', '종목코드', '종목명', '진입가', '현재가', '수익률(%)',
                '거래량비율', 'Stoch%K', 'Stoch%D', 'ADX', 'MA5', 'MA20', 'MA60', 'MA120',
                '손절가', '손절률(%)', '1차익절가', '1차익절률(%)', '2차익절가', '2차익절률(%)', '지지선',
                '백테스트_진입일', '백테스트_진입가', '백테스트_청산일',
                '백테스트_청산사유', '백테스트_수익률(%)'
            ]
        else:
            headers = [
                '신호일', '종목코드', '종목명', '진입가', '현재가', '수익률(%)',
                '거래량비율', 'Stoch%K', 'Stoch%D', 'ADX', 'MA5', 'MA20', 'MA60', 'MA120',
                '손절가', '손절률(%)', '1차익절가', '1차익절률(%)', '2차익절가', '2차익절률(%)', '지지선'
            ]
        
        writer.writerow(headers)
        
        # 데이터 행
        for stock in sorted_results:
            row = [
                stock['signal_date'],
                stock['code'],
                stock['name'],
                stock['entry_price'],
                stock['current_price'],
                stock['profit_rate'],
                stock['volume_ratio'],
                stock['stoch_k'],
                stock['stoch_d'],
                stock['adx'],
                stock['ma5'],
                stock['ma20'],
                stock['ma60'],
                stock['ma120'],
                stock['stop_loss'],
                stock['stop_loss_pct'],
                stock['take_profit_1'],
                stock['take_profit_1_pct'],
                stock['take_profit_2'],
                stock['take_profit_2_pct'],
                stock['support_low']
            ]
            
            if 'backtest' in stock:
                bt = stock['backtest']
                row.extend([
                    bt['entry_date'],
                    bt['entry_price'],
                    bt['exit_date'],
                    bt['exit_reason'],
                    bt['profit_rate']
                ])
            
            writer.writerow(row)
    
    print(f"\n{'='*60}")
    print(f"✓ 결과 저장 완료: {output_file}")
    print(f"{'='*60}")


def backtest_stocks(results, trading_days, end_date, silent=False):
    """백테스팅: 익일 시가 매수 후 단계적 손절/익절 확인"""
    if not silent:
        print(f"\n{'='*80}")
        print(f"백테스팅 실행 중...")
        print(f"{'='*80}\n")
    
    backtested_results = []
    
    for stock in results:
        stock_code = stock['code']
        signal_idx = stock['signal_index']
        
        timeseries = DataLoader.get_stock_timeseries(trading_days, stock_code)
        
        if signal_idx + 1 >= len(timeseries):
            continue
        
        entry_price = timeseries[signal_idx + 1]['open']
        
        if not entry_price or entry_price == 0:
            continue
        
        stop_loss = stock['stop_loss']
        take_profit_1 = stock['take_profit_1']
        take_profit_2 = stock['take_profit_2']
        
        # 단계적 익절 추적
        remaining_position = 1.0
        total_profit = 0.0
        exit_date = None
        exit_reason = None
        
        for i in range(signal_idx + 1, len(timeseries)):
            day = timeseries[i]
            
            # 손절가 확인
            if day['low'] <= stop_loss:
                total_profit += remaining_position * ((stop_loss - entry_price) / entry_price) * 100
                exit_date = day['date']
                exit_reason = 'stop_loss'
                remaining_position = 0.0
                break
            
            # 1차 익절 확인
            if remaining_position == 1.0 and day['high'] >= take_profit_1:
                total_profit += 0.5 * ((take_profit_1 - entry_price) / entry_price) * 100
                remaining_position = 0.5
            
            # 2차 익절 확인
            if remaining_position == 0.5 and day['high'] >= take_profit_2:
                total_profit += 0.5 * ((take_profit_2 - entry_price) / entry_price) * 100
                exit_date = day['date']
                exit_reason = 'take_profit_2'
                remaining_position = 0.0
                break
        
        # 남은 포지션 처리
        if remaining_position > 0:
            current_price = timeseries[-1]['close']
            total_profit += remaining_position * ((current_price - entry_price) / entry_price) * 100
            exit_date = timeseries[-1]['date']
            if remaining_position == 1.0:
                exit_reason = 'holding_100'
            else:
                exit_reason = 'holding_50'
        
        backtested_stock = stock.copy()
        backtested_stock['backtest'] = {
            'entry_price': int(entry_price),
            'entry_date': timeseries[signal_idx + 1]['date'],
            'exit_date': exit_date,
            'exit_reason': exit_reason,
            'profit_rate': round(total_profit, 2)
        }
        
        backtested_results.append(backtested_stock)
    
    return backtested_results


def print_final_summary(results, silent=False):
    """최종 결과 요약 출력"""
    if silent:
        print(f"\n{'='*80}")
        print(f"종목별 상세 정보")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}")
        print(f"최종 선택 종목 상세 정보")
        print(f"{'='*80}\n")
    
    for idx, stock in enumerate(results, 1):
        print(f"[{idx}] {stock['name']} ({stock['code']})")
        print(f"  신호일: {stock['signal_date']}")
        print(f"  진입가: {stock['entry_price']:,}원")
        
        if 'backtest' in stock:
            bt = stock['backtest']
            print(f"  매수일: {bt['entry_date']} (시가 {bt['entry_price']:,}원)")
            
            reason_msg = {
                'stop_loss': '손절 (-8%)',
                'take_profit_1': '1차 익절 후 현재가 청산',
                'take_profit_2': '2차 익절 완료 (전량 청산)',
                'holding_50': '1차 익절 후 50% 홀딩 중',
                'holding_100': '전량 홀딩 중'
            }
            print(f"  청산일: {bt['exit_date']} ({reason_msg.get(bt['exit_reason'], bt['exit_reason'])})")
            print(f"  수익률: {bt['profit_rate']:+.2f}%")
        else:
            print(f"  현재가: {stock['current_price']:,}원")
            print(f"  수익률: {stock['profit_rate']:+.2f}%")
        
        print(f"  거래량비율: {stock['volume_ratio']:.2f} (5일 평균 / 20일 평균)")
        print(f"  Stochastic: %K={stock['stoch_k']:.1f}, %D={stock['stoch_d']:.1f}")
        print(f"  ADX: {stock['adx']:.1f} (추세 강도)")
        print(f"  정배열: MA5({stock['ma5']:,}) > MA20({stock['ma20']:,}) > MA60({stock['ma60']:,}) > MA120({stock['ma120']:,})")
        print(f"  손절가: {stock['stop_loss']:,}원 ({stock['stop_loss_pct']:+.2f}%)")
        print(f"  1차 익절가: {stock['take_profit_1']:,}원 (+{stock['take_profit_1_pct']:.1f}%, 50% 청산)")
        print(f"  2차 익절가: {stock['take_profit_2']:,}원 (+{stock['take_profit_2_pct']:.1f}%, 나머지 청산)")
        print(f"  지지선: {stock['support_low']:,}원")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='정배열 + 모멘텀 전략 종목 선별',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python align_momentum.py --from 20250101 --to 20251114
  python align_momentum.py --from 20250101 --to 20251114 --backtest
  python align_momentum.py --from 20250101 --to 20251114 --backtest --silent
  python align_momentum.py --from 20250101 --to 20251114 --debug
        """
    )
    
    parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    parser.add_argument('--backtest', action='store_true', help='백테스팅 모드')
    parser.add_argument('--low_period', type=int, default=20, help='지지선 계산 기간 (일, 기본값: 20)')
    parser.add_argument('--silent', action='store_true', help='간략 출력 모드')
    parser.add_argument('--debug', action='store_true', help='디버그 모드')
    
    args = parser.parse_args()
    
    # 날짜 설정
    if args.from_date and args.to_date:
        start_date = args.from_date
        end_date = args.to_date
    else:
        # 기본: 어제
        yesterday = datetime.now() - timedelta(days=1)
        start_date = end_date = yesterday.strftime("%Y%m%d")
    
    # 과거 데이터 로드 (120일 이동평균 계산을 위해)
    extended_start = datetime.strptime(start_date, "%Y%m%d") - timedelta(days=250)
    extended_start_str = extended_start.strftime("%Y%m%d")
    
    print(f"\n{'='*80}")
    print(f"정배열 + 모멘텀 전략 종목 선별")
    print(f"{'='*80}")
    print(f"분석 기간: {start_date} ~ {end_date}")
    print(f"데이터 로드: {extended_start_str} ~ {end_date} (이동평균 계산용)")
    print(f"{'='*80}\n")
    
    # 데이터 로드
    trading_days = DataLoader.load_kospi200_data(extended_start_str, end_date)
    
    # 종목 선별
    screener = StockScreener(trading_days, silent=args.silent)
    selected_stocks = screener.find_align_momentum_stocks(
        start_date=start_date,
        end_date=end_date,
        low_period=args.low_period,
        debug=args.debug
    )
    
    if not selected_stocks:
        print("\n조건을 만족하는 종목이 없습니다.")
        save_results([], start_date, end_date)
        sys.exit(0)
    
    # 백테스팅 실행
    if args.backtest:
        backtested_stocks = backtest_stocks(selected_stocks, trading_days, end_date, silent=args.silent)
        
        print_final_summary(backtested_stocks, silent=args.silent)
        
        # 백테스팅 통계
        print(f"\n{'='*80}")
        print(f"백테스팅 통계 (단계적 익절: 13%에서 50%, 21%에서 나머지 50%)")
        print(f"{'='*80}")
        
        total = len(backtested_stocks)
        profits = [s['backtest']['profit_rate'] for s in backtested_stocks]
        
        stop_loss_count = sum(1 for s in backtested_stocks if s['backtest']['exit_reason'] == 'stop_loss')
        take_profit_2_count = sum(1 for s in backtested_stocks if s['backtest']['exit_reason'] == 'take_profit_2')
        holding_50_count = sum(1 for s in backtested_stocks if s['backtest']['exit_reason'] == 'holding_50')
        holding_100_count = sum(1 for s in backtested_stocks if s['backtest']['exit_reason'] == 'holding_100')
        
        win_count = sum(1 for p in profits if p > 0)
        lose_count = sum(1 for p in profits if p < 0)
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        max_profit = max(profits) if profits else 0
        min_profit = min(profits) if profits else 0
        
        print(f"총 종목 수: {total}개")
        print(f"승: {win_count}개 ({win_count/total*100:.1f}%)")
        print(f"패: {lose_count}개 ({lose_count/total*100:.1f}%)")
        print(f"")
        print(f"손절: {stop_loss_count}개 ({stop_loss_count/total*100:.1f}%)")
        print(f"2차 익절 (21%, 전량 청산): {take_profit_2_count}개 ({take_profit_2_count/total*100:.1f}%)")
        print(f"1차 익절 후 홀딩: {holding_50_count}개 ({holding_50_count/total*100:.1f}%)")
        print(f"전량 홀딩: {holding_100_count}개 ({holding_100_count/total*100:.1f}%)")
        print(f"")
        print(f"평균 수익률: {avg_profit:+.2f}%")
        print(f"최대 수익률: {max_profit:+.2f}%")
        print(f"최소 수익률: {min_profit:+.2f}%")
        print(f"{'='*80}")
        
        save_results(backtested_stocks, start_date, end_date)
    else:
        print_final_summary(selected_stocks, silent=args.silent)
        save_results(selected_stocks, start_date, end_date)


if __name__ == '__main__':
    main()

