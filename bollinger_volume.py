#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
볼린저 밴드 + 거래량 전략 종목 선별 프로그램

전략:
1. 볼린저 밴드 하단(-2σ) 터치
2. 3일 이내 반등하여 중심선(20일 MA) 돌파
3. 반등 시 거래량이 평균 거래량의 2배 이상
4. RSI가 30 이하에서 50 이상으로 회복
5. MACD 골든크로스

손절/익절:
- 손절가: 볼린저 밴드 하단 터치일 기준 이전 N일(--low_period) 최저가
- 익절가: 손절폭의 2배
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
        """이동평균 계산"""
        if len(data) < period:
            return [None] * len(data)
        
        result = [None] * (period - 1)
        for i in range(period - 1, len(data)):
            result.append(sum(data[i-period+1:i+1]) / period)
        
        return result
    
    @staticmethod
    def calculate_std(data, period):
        """표준편차 계산"""
        if len(data) < period:
            return [None] * len(data)
        
        result = [None] * (period - 1)
        for i in range(period - 1, len(data)):
            window = data[i-period+1:i+1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            result.append(variance ** 0.5)
        
        return result
    
    @staticmethod
    def calculate_bollinger_bands(data, period=20, num_std=2):
        """볼린저 밴드 계산"""
        ma = TechnicalIndicators.calculate_ma(data, period)
        std = TechnicalIndicators.calculate_std(data, period)
        
        upper = []
        lower = []
        for m, s in zip(ma, std):
            if m is None or s is None:
                upper.append(None)
                lower.append(None)
            else:
                upper.append(m + num_std * s)
                lower.append(m - num_std * s)
        
        return ma, upper, lower
    
    @staticmethod
    def calculate_ema(data, period):
        """지수 이동평균 계산"""
        if len(data) < period:
            return [None] * len(data)
        
        multiplier = 2 / (period + 1)
        ema = [None] * (period - 1)
        ema.append(sum(data[:period]) / period)
        
        for i in range(period, len(data)):
            ema.append((data[i] - ema[-1]) * multiplier + ema[-1])
        
        return ema
    
    @staticmethod
    def calculate_macd(data, fast=12, slow=26, signal=9):
        """MACD 계산"""
        ema_fast = TechnicalIndicators.calculate_ema(data, fast)
        ema_slow = TechnicalIndicators.calculate_ema(data, slow)
        
        macd_line = []
        for f, s in zip(ema_fast, ema_slow):
            if f is None or s is None:
                macd_line.append(None)
            else:
                macd_line.append(f - s)
        
        signal_line = TechnicalIndicators.calculate_ema(
            [m if m is not None else 0 for m in macd_line], signal
        )
        
        return macd_line, signal_line
    
    @staticmethod
    def calculate_rsi(data, period=14):
        """RSI 계산"""
        if len(data) < period + 1:
            return [None] * len(data)
        
        gains = []
        losses = []
        
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        result = [None]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            result.append(100)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                result.append(100)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - (100 / (1 + rs)))
        
        return result


class DataLoader:
    """데이터 로딩 클래스"""
    
    @staticmethod
    def load_kospi200_data(start_date, end_date):
        """KOSPI 200 데이터 로드"""
        base_dir = "data/json/kospi200"
        
        if not os.path.exists(base_dir):
            print(f"❌ 데이터 폴더가 없습니다: {base_dir}")
            print(f"   먼저 get_data.py를 실행하여 데이터를 수집하세요:")
            print(f"   python get_data.py --config config.json --from {start_date} --to {end_date}")
            return None
        
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        
        all_days = []
        for year in range(start_year, end_year + 1):
            file_path = f"{base_dir}/{year}/kospi200_data.json"
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    year_data_count = len(data['data'])
                    all_days.extend(data['data'])
                    print(f"  ✓ {year}년 데이터 로드: {year_data_count}일")
            else:
                print(f"  ⚠️  {year}년 데이터 파일 없음: {file_path}")
        
        if not all_days:
            print(f"❌ 데이터가 없습니다.")
            print(f"   먼저 get_data.py를 실행하여 데이터를 수집하세요:")
            print(f"   python get_data.py --config config.json --from {start_date} --to {end_date}")
            return None
        
        filtered_days = [d for d in all_days if start_date <= d['date'] <= end_date]
        
        if not filtered_days:
            print(f"❌ {start_date} ~ {end_date} 기간의 데이터가 없습니다.")
            print(f"   먼저 get_data.py를 실행하여 데이터를 수집하세요:")
            print(f"   python get_data.py --config config.json --from {start_date} --to {end_date}")
            return None
        
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
        
        latest_day = self.trading_days[-1]
        stocks = [{'code': s['code'], 'name': s['name']} for s in latest_day['stocks']]
        return stocks
    
    def find_bollinger_volume_stocks(self, start_date=None, end_date=None, low_period=12, debug=False):
        """볼린저 밴드 + 거래량 전략 종목 찾기"""
        if not self.silent:
            print(f"\n{'='*60}")
            print(f"볼린저 밴드 + 거래량 전략 종목 검색")
            print(f"{'='*60}")
        
        selected_stocks = []
        total = len(self.all_stocks)
        
        # 디버그용 통계
        debug_stats = {
            'total_checked': 0,
            'trend_filter': 0,
            'bb_touch': 0,
            'bb_middle_cross': 0,
            'volume_surge': 0,
            'rsi_recovery': 0,
            'macd_gc': 0,
            'all_passed': 0
        }
        
        for idx, stock_info in enumerate(self.all_stocks, 1):
            if not self.silent and idx % 50 == 0:
                print(f"진행중: {idx}/{total} ({idx/total*100:.1f}%)")
            
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            
            timeseries = DataLoader.get_stock_timeseries(self.trading_days, stock_code)
            
            if len(timeseries) < 150:  # 120일 + 여유
                continue
            
            closes = [t['close'] for t in timeseries]
            volumes = [t['volume'] for t in timeseries]
            lows = [t['low'] for t in timeseries]
            
            # 볼린저 밴드 계산
            bb_middle, bb_upper, bb_lower = TechnicalIndicators.calculate_bollinger_bands(closes, 20, 2)
            
            # MACD 계산
            macd_line, signal_line = TechnicalIndicators.calculate_macd(closes)
            
            # RSI 계산
            rsi_line = TechnicalIndicators.calculate_rsi(closes, 14)
            
            # 평균 거래량 계산
            avg_volume = TechnicalIndicators.calculate_ma(volumes, 20)
            
            # 추세 확인용 이동평균선 계산
            ma60 = TechnicalIndicators.calculate_ma(closes, 60)
            ma120 = TechnicalIndicators.calculate_ma(closes, 120)
            
            # 검색 범위 설정: start_date부터 end_date 사이의 인덱스 찾기
            search_start_idx = 0  # 0부터 시작 (조건 체크에서 120일 이상만 검사)
            search_end_idx = len(timeseries)
            
            if start_date:
                # start_date에 해당하는 인덱스 찾기
                for i, t in enumerate(timeseries):
                    if t['date'] >= start_date:
                        search_start_idx = i
                        break
            
            if end_date:
                # end_date에 해당하는 인덱스 찾기
                for i, t in enumerate(timeseries):
                    if t['date'] > end_date:
                        search_end_idx = i
                        break
            
            # 전략 조건 확인 (역순: 최신 신호 우선)
            for i in range(search_end_idx - 1, search_start_idx - 1, -1):
                passed, stage = self._check_strategy_conditions(
                    i, closes, volumes, lows, bb_middle, bb_upper, bb_lower,
                    macd_line, signal_line, rsi_line, avg_volume, ma60, ma120, debug
                )
                
                if debug and stage > 0:
                    debug_stats['total_checked'] += 1
                    if stage >= 1: debug_stats['trend_filter'] += 1
                    if stage >= 2: debug_stats['bb_touch'] += 1
                    if stage >= 3: debug_stats['bb_middle_cross'] += 1
                    if stage >= 4: debug_stats['volume_surge'] += 1
                    if stage >= 5: debug_stats['rsi_recovery'] += 1
                    if stage >= 6: debug_stats['macd_gc'] += 1
                    if passed: debug_stats['all_passed'] += 1
                
                if passed:
                    # 조건 만족 시점의 정보 수집
                    bb_touch_idx = self._find_bb_lower_touch(i, closes, bb_lower)
                    
                    if bb_touch_idx is None:
                        continue
                    
                    entry_price = closes[i]
                    current_close = closes[-1]
                    
                    # 손절가 계산 (BB 하단 터치일 기준 이전 N일 최저가)
                    lookback_start = max(0, bb_touch_idx - low_period)
                    lookback_end = bb_touch_idx + 1
                    support_low = min(lows[lookback_start:lookback_end])
                    
                    stop_loss_amount = entry_price - support_low
                    stop_loss = int(support_low)
                    stop_loss_pct = ((support_low - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                    
                    take_profit = int(entry_price + (stop_loss_amount * 2))
                    take_profit_pct = ((take_profit - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                    
                    profit_rate = ((current_close - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                    
                    # 볼린저 밴드 위치 계산
                    bb_position = ((current_close - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1]) * 100) if (bb_upper[-1] - bb_lower[-1]) != 0 else 50
                    
                    selected_stocks.append({
                        'code': stock_code,
                        'name': stock_name,
                        'signal_date': timeseries[i]['date'],
                        'signal_index': i,
                        'bb_touch_date': timeseries[bb_touch_idx]['date'],
                        'bb_touch_index': bb_touch_idx,
                        'entry_price': int(entry_price),
                        'current_price': int(current_close),
                        'profit_rate': round(profit_rate, 2),
                        'bb_position': round(bb_position, 2),
                        'volume_ratio': round(volumes[i] / avg_volume[i], 2) if avg_volume[i] and avg_volume[i] != 0 else 0,
                        'rsi_value': round(rsi_line[i], 2) if rsi_line[i] is not None else 0,
                        'macd_value': round(macd_line[i], 2) if macd_line[i] is not None else 0,
                        'macd_signal': round(signal_line[i], 2) if signal_line[i] is not None else 0,
                        'stop_loss': stop_loss,
                        'stop_loss_pct': round(stop_loss_pct, 2),
                        'take_profit': take_profit,
                        'take_profit_pct': round(take_profit_pct, 2),
                        'risk_reward_ratio': 2.0,
                        'support_low': int(support_low)
                    })
                    break  # 종목당 한 번만
        
        if not self.silent:
            print(f"\n✓ 전략 조건 만족 종목: {len(selected_stocks)}개")
            for stock in selected_stocks[:10]:
                print(f"  - {stock['name']} ({stock['code']}): {stock['signal_date']}, "
                      f"진입가 {stock['entry_price']:,}원 → 현재가 {stock['current_price']:,}원 ({stock['profit_rate']:+.1f}%), "
                      f"거래량 {stock['volume_ratio']:.1f}배")
            
            if len(selected_stocks) > 10:
                print(f"  ... 외 {len(selected_stocks) - 10}개 종목")
        
        if debug:
            print(f"\n{'='*60}")
            print(f"디버그 통계 (각 조건별 통과 비율)")
            print(f"{'='*60}")
            if debug_stats['total_checked'] > 0:
                print(f"0단계 - 검사 대상: {debug_stats['total_checked']:,}")
                print(f"1단계 - 추세 필터 (60>120, 현재>60): {debug_stats['trend_filter']:,} / {debug_stats['total_checked']:,} ({debug_stats['trend_filter']/debug_stats['total_checked']*100:.1f}%)")
                if debug_stats['trend_filter'] > 0:
                    print(f"2단계 - BB 하단 터치: {debug_stats['bb_touch']:,} / {debug_stats['trend_filter']:,} ({debug_stats['bb_touch']/debug_stats['trend_filter']*100:.1f}%)")
                if debug_stats['bb_touch'] > 0:
                    print(f"3단계 - BB 중심선 돌파: {debug_stats['bb_middle_cross']:,} / {debug_stats['bb_touch']:,} ({debug_stats['bb_middle_cross']/debug_stats['bb_touch']*100:.1f}%)")
                if debug_stats['bb_middle_cross'] > 0:
                    print(f"4단계 - 거래량 증가: {debug_stats['volume_surge']:,} / {debug_stats['bb_middle_cross']:,} ({debug_stats['volume_surge']/debug_stats['bb_middle_cross']*100:.1f}%)")
                if debug_stats['volume_surge'] > 0:
                    print(f"5단계 - RSI 회복: {debug_stats['rsi_recovery']:,} / {debug_stats['volume_surge']:,} ({debug_stats['rsi_recovery']/debug_stats['volume_surge']*100:.1f}%)")
                if debug_stats['rsi_recovery'] > 0:
                    print(f"6단계 - MACD 골든크로스: {debug_stats['macd_gc']:,} / {debug_stats['rsi_recovery']:,} ({debug_stats['macd_gc']/debug_stats['rsi_recovery']*100:.1f}%)")
                print(f"최종 선택: {debug_stats['all_passed']:,} 종목")
            else:
                print("분석할 데이터가 없습니다.")
        
        return selected_stocks
    
    def _check_strategy_conditions(self, idx, closes, volumes, lows, bb_middle, bb_upper, bb_lower,
                                   macd_line, signal_line, rsi_line, avg_volume, ma60, ma120, debug=False):
        """전략 조건 확인 (반환: (통과여부, 도달단계))"""
        stage = 0
        
        if idx < 120:  # 최소 120일 전 데이터 필요
            return False, stage
        
        # 인덱스 범위 확인
        if (idx >= len(rsi_line) or idx >= len(avg_volume) or 
            idx >= len(bb_middle) or idx >= len(bb_lower) or idx >= len(bb_upper) or
            idx >= len(macd_line) or idx >= len(signal_line) or
            idx >= len(ma60) or idx >= len(ma120)):
            return False, stage
        
        # 필수 값 확인
        if None in [bb_middle[idx], bb_upper[idx], bb_lower[idx], macd_line[idx], signal_line[idx], 
                    rsi_line[idx], avg_volume[idx], ma60[idx], ma120[idx]]:
            return False, stage
        
        # 1. 추세 필터: 중장기 상승 추세 확인 (가장 중요!)
        # - 60일선 > 120일선: 중장기 상승 추세
        # - 현재가 > 60일선: 단기도 상승 추세
        if ma60[idx] <= ma120[idx] or closes[idx] <= ma60[idx]:
            return False, stage
        stage = 1
        
        # 2. 3일 이내 볼린저 밴드 하단 터치 확인
        bb_touched = False
        for j in range(max(0, idx - 3), idx + 1):
            if j < len(bb_lower) and j < len(lows) and bb_lower[j] is not None and lows[j] <= bb_lower[j]:
                bb_touched = True
                break
        
        if not bb_touched:
            return False, stage
        stage = 2
        
        # 3. 현재 중심선(20일 MA) 돌파 확인
        if closes[idx] <= bb_middle[idx]:
            return False, stage
        stage = 3
        
        # 4. 거래량 1.5배 이상 증가
        if avg_volume[idx] == 0 or volumes[idx] < avg_volume[idx] * 1.5:
            return False, stage
        stage = 4
        
        # 5. RSI 회복 확인
        # - 과거 10일 내 RSI 40 이하였던 시점이 있어야 함
        # - 현재 RSI가 그때보다 5 이상 상승해야 함
        rsi_recovery = False
        min_rsi_in_period = None
        
        for j in range(max(0, idx - 10), idx + 1):
            if j < len(rsi_line) and rsi_line[j] is not None:
                if min_rsi_in_period is None or rsi_line[j] < min_rsi_in_period:
                    min_rsi_in_period = rsi_line[j]
        
        current_rsi = rsi_line[idx] if idx < len(rsi_line) and rsi_line[idx] is not None else None
        
        if min_rsi_in_period is not None and current_rsi is not None:
            if min_rsi_in_period <= 40 and current_rsi >= min_rsi_in_period + 5:
                rsi_recovery = True
        
        if not rsi_recovery:
            return False, stage
        stage = 5
        
        # 6. MACD 골든크로스 + 히스토그램 양수 확인 (강화!)
        macd_gc = False
        for j in range(max(1, idx - 10), idx + 1):
            if (j < len(macd_line) and j < len(signal_line) and j > 0 and
                macd_line[j] is not None and signal_line[j] is not None and
                macd_line[j-1] is not None and signal_line[j-1] is not None):
                # 골든크로스 + MACD 히스토그램이 양수
                if (macd_line[j-1] <= signal_line[j-1] and macd_line[j] > signal_line[j] and
                    macd_line[j] - signal_line[j] > 0):
                    macd_gc = True
                    break
        
        if not macd_gc:
            return False, stage
        stage = 6
        
        return True, stage
    
    def _find_bb_lower_touch(self, current_idx, closes, bb_lower):
        """볼린저 밴드 하단 터치 시점 찾기 (최근 3일 내)"""
        for j in range(max(0, current_idx - 3), current_idx + 1):
            if j < len(bb_lower) and j < len(closes) and bb_lower[j] is not None and closes[j] <= bb_lower[j] * 1.01:  # 1% 여유
                return j
        return None


def save_results(results, start_date, end_date):
    """결과 저장 (CSV 형식)"""
    year = end_date[:4]
    output_dir = f'data/json/kospi200/{year}/result'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f'{output_dir}/bollinger_volume_{start_date}_{end_date}.csv'
    
    # 신호일 기준으로 정렬
    sorted_results = sorted(results, key=lambda x: x['signal_date'])
    
    if not sorted_results:
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['전략', 'Bollinger Bands + Volume Strategy'])
            writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
            writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(['선택종목수', '0'])
        print(f"\n{'='*60}")
        print(f"✓ 결과 저장 완료: {output_file}")
        print(f"{'='*60}")
        return
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['전략', 'Bollinger Bands + Volume Strategy'])
        writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
        writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(['선택종목수', str(len(sorted_results))])
        writer.writerow([])
        
        if 'backtest' in sorted_results[0]:
            headers = [
                '신호일', '종목코드', '종목명', 'BB터치일', '진입가', '현재가', '수익률(%)',
                'BB위치(%)', '거래량비율', 'RSI', 'MACD', 'Signal',
                '손절가', '손절률(%)', '익절가', '익절률(%)', '지지선',
                '백테스트_진입일', '백테스트_진입가', '백테스트_청산일', '백테스트_청산가',
                '백테스트_청산사유', '백테스트_수익률(%)'
            ]
        else:
            headers = [
                '신호일', '종목코드', '종목명', 'BB터치일', '진입가', '현재가', '수익률(%)',
                'BB위치(%)', '거래량비율', 'RSI', 'MACD', 'Signal',
                '손절가', '손절률(%)', '익절가', '익절률(%)', '지지선'
            ]
        
        writer.writerow(headers)
        
        for stock in sorted_results:
            row = [
                stock['signal_date'],
                stock['code'],
                stock['name'],
                stock['bb_touch_date'],
                stock['entry_price'],
                stock['current_price'],
                stock['profit_rate'],
                stock['bb_position'],
                stock['volume_ratio'],
                stock['rsi_value'],
                stock['macd_value'],
                stock['macd_signal'],
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
        signal_date = stock['signal_date']
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
        
        # 신호 발생일 찾기
        signal_index = next((i for i, d in enumerate(stock_data) if d['date'] == signal_date), None)
        
        if signal_index is None or signal_index >= len(stock_data) - 1:
            continue
        
        # 익일 시가로 매수
        buy_index = signal_index + 1
        buy_price = stock_data[buy_index]['open']
        buy_date = stock_data[buy_index]['date']
        
        # 손절가/익절가 도달 여부 확인
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
        # 신호 발생 정보 테이블
        print(f"\n[신호 발생 정보]")
        print(f"{'종목명':<12} {'코드':<8} {'신호일':<10} {'BB터치일':<10} {'거래량비':>8} {'RSI':>6} {'BB위치':>8}")
        print("-" * 75)
        
        for stock in results:
            name = stock['name'][:10] + '..' if len(stock['name']) > 12 else stock['name']
            print(f"{name:<12} {stock['code']:<8} "
                  f"{stock['signal_date']:<10} "
                  f"{stock['bb_touch_date']:<10} "
                  f"{stock['volume_ratio']:>7.1f}배 "
                  f"{stock['rsi_value']:>6.1f} "
                  f"{stock['bb_position']:>7.1f}%")
        
        # 매매 전략 테이블
        print(f"\n[매매 전략 (손절/익절)]")
        print(f"{'종목명':<12} {'진입가':>10} {'현재가':>10} {'수익률':>8} {'손절가':>10} {'손절률':>8} {'익절가':>10} {'익절률':>8}")
        print("-" * 95)
        
        for stock in results:
            name = stock['name'][:10] + '..' if len(stock['name']) > 12 else stock['name']
            print(f"{name:<12} "
                  f"{stock['entry_price']:>10,}원 "
                  f"{stock['current_price']:>10,}원 "
                  f"{stock['profit_rate']:>7.2f}% "
                  f"{stock['stop_loss']:>10,}원 "
                  f"{stock['stop_loss_pct']:>7.2f}% "
                  f"{stock['take_profit']:>10,}원 "
                  f"{stock['take_profit_pct']:>7.2f}%")
        
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
        print(f"  - 평균 거래량 비율: {sum(s['volume_ratio'] for s in results) / len(results):.2f}배")
        print(f"  - 평균 RSI: {sum(s['rsi_value'] for s in results) / len(results):.1f}")
        print(f"  - 평균 BB 위치: {sum(s['bb_position'] for s in results) / len(results):.1f}%")
        print(f"  - 평균 진입가: {sum(s['entry_price'] for s in results) / len(results):,.0f}원")
        print(f"  - 평균 현재가: {sum(s['current_price'] for s in results) / len(results):,.0f}원")
        print(f"  - 평균 수익률: {sum(s['profit_rate'] for s in results) / len(results):+.2f}%")
    
    # 개별 종목 상세 정보
    print(f"\n[종목별 상세 정보]")
    for idx, stock in enumerate(results, 1):
        print(f"\n{idx}. {stock['name']} ({stock['code']})")
        print(f"   신호 발생일: {stock['signal_date']} | BB 하단 터치일: {stock['bb_touch_date']}")
        print(f"   진입가: {stock['entry_price']:,}원 | 현재가: {stock['current_price']:,}원 | 수익률: {stock['profit_rate']:+.2f}%")
        print(f"   거래량: 평균의 {stock['volume_ratio']:.1f}배 | RSI: {stock['rsi_value']:.1f} | BB위치: {stock['bb_position']:.1f}%")
        print(f"   💔 손절가: {stock['stop_loss']:,}원 ({stock['stop_loss_pct']:+.2f}%)")
        print(f"   💰 익절가: {stock['take_profit']:,}원 ({stock['take_profit_pct']:+.2f}%)")
        print(f"   📊 손익비: 1:{stock['risk_reward_ratio']:.0f}")
        
        # 백테스팅 정보 (있는 경우)
        if 'backtest' in stock:
            bt = stock['backtest']
            result_text = f"{'✅ 익절' if bt['sell_reason'] == '익절' else '❌ 손절' if bt['sell_reason'] == '손절' else '⏳ 홀딩'}"
            print(f"   🔍 백테스트: {bt['buy_date']}({bt['buy_price']:,}원) → {bt['sell_date']}({bt['sell_price']:,}원) "
                  f"| {result_text} | {bt['profit_rate']:+.2f}% | {bt['days_held']}일 보유")


def main():
    parser = argparse.ArgumentParser(
        description='볼린저 밴드 + 거래량 전략 종목 선별 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  1. 특정 기간 분석:
     python bollinger_volume.py --from 20250101 --to 20250131

  2. 어제 (마지막 거래일) 분석 (기본):
     python bollinger_volume.py

  3. 백테스팅:
     python bollinger_volume.py --from 20250101 --to 20250131 --backtest

  4. 간략 모드:
     python bollinger_volume.py --from 20250101 --to 20250131 --silent

  5. 디버그 모드 (각 조건별 통과율 확인):
     python bollinger_volume.py --from 20250101 --to 20250131 --debug

전략 조건 (상승 추세 내 조정 반등 포착):
  0. 추세 필터: 60일선 > 120일선 & 현재가 > 60일선 (필수!)
  1. 볼린저 밴드 하단(-2σ) 터치
  2. 3일 이내 반등하여 중심선(20일 MA) 돌파
  3. 반등 시 거래량이 평균 거래량의 1.5배 이상
  4. RSI 과매도(≤40)에서 +5 이상 회복 (10일 내)
  5. MACD 골든크로스 + 히스토그램 양수 (10일 내)
        '''
    )
    
    parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    parser.add_argument('--backtest', action='store_true', help='백테스팅 모드 (--from, --to 필수)')
    parser.add_argument('--low_period', type=int, default=20, help='전저점 계산 기간 (일, 기본값: 20, 권장: 20-30)')
    parser.add_argument('--silent', action='store_true', help='간략 출력 모드 (최종 결과만 표시)')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 (각 조건별 통과율 표시)')
    
    args = parser.parse_args()
    
    # 백테스팅 모드 검증
    if args.backtest and (not args.from_date or not args.to_date):
        print("❌ 백테스팅 모드는 --from, --to 옵션이 필수입니다.")
        print("\n사용 예시:")
        print("  python bollinger_volume.py --from 20250101 --to 20250131 --backtest")
        sys.exit(1)
    
    if not args.silent:
        print("=" * 60)
        if args.backtest:
            print("볼린저 밴드 + 거래량 전략 종목 선별 + 백테스팅")
        else:
            print("볼린저 밴드 + 거래량 전략 종목 선별 프로그램")
        print("=" * 60)
        print()
    
    # 날짜 범위 설정
    if args.from_date:
        start_date = args.from_date
        end_date = args.to_date if args.to_date else datetime.now().strftime("%Y%m%d")
    else:
        yesterday = datetime.now() - timedelta(days=1)
        end_date = yesterday.strftime("%Y%m%d")
        start_date = end_date
    
    # 분석을 위해 더 많은 데이터 필요 (최소 250일: 150+ 거래일 확보)
    extended_start = (datetime.strptime(start_date, "%Y%m%d") - timedelta(days=250)).strftime("%Y%m%d")
    
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
        print(f"검색 범위: {start_date} ~ {end_date}")
    
    # 전략 실행
    selected_stocks = screener.find_bollinger_volume_stocks(
        start_date=start_date,
        end_date=end_date,
        low_period=args.low_period,
        debug=args.debug
    )
    
    if not selected_stocks:
        print("\n⚠️  전략 조건을 만족하는 종목이 없습니다.")
        save_results([], start_date, end_date)
        sys.exit(0)
    
    # 백테스팅 실행 (옵션이 주어진 경우)
    if args.backtest:
        backtested_stocks = backtest_stocks(selected_stocks, trading_days, end_date, silent=args.silent)
        
        # 최종 결과 출력 (백테스팅 포함)
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
        print_final_summary(selected_stocks, silent=args.silent)
        
        # 결과 저장
        save_results(selected_stocks, start_date, end_date)
    
    if not args.silent:
        print("\n✅ 분석 완료!")


if __name__ == "__main__":
    main()

