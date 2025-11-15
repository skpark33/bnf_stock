#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
모멘텀 + 추세 전략 종목 선별 프로그램

전략:
1. 추세 필터: 60일선 > 120일선, 현재가 > 60일선 (상승 추세 확인)
2. 20일 신고가 돌파
3. 거래량 폭발 (평균 거래량의 2배 이상)
4. MACD > Signal (상승 모멘텀 확인)

손절/익절:
- 손절가: 신고가 돌파일 기준 이전 N일(--low_period) 최저가
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
        
        return macd_line, signal_line
    
    @staticmethod
    def find_highest(data, period):
        """기간 내 최고가 찾기"""
        if len(data) < period:
            return [None] * len(data)
        
        result = [None] * (period - 1)
        for i in range(period - 1, len(data)):
            result.append(max(data[i-period+1:i+1]))
        
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
            print(f"   python get_data.py --from {start_date} --to {end_date}")
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
            print(f"   python get_data.py --from {start_date} --to {end_date}")
            return None
        
        # 날짜 범위로 필터링
        filtered_days = [
            day for day in all_days
            if start_date <= day['date'] <= end_date and not day.get('is_holiday', False)
        ]
        
        return filtered_days
    
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
    
    def find_momentum_trend_stocks(self, start_date=None, end_date=None, low_period=20, debug=False):
        """모멘텀 + 추세 전략 종목 찾기"""
        if not self.silent:
            print(f"\n{'='*60}")
            print(f"모멘텀 + 추세 전략 종목 검색")
            print(f"{'='*60}")
        
        selected_stocks = []
        total = len(self.all_stocks)
        
        # 디버그용 통계
        debug_stats = {
            'total_checked': 0,
            'trend_filter': 0,
            'new_high': 0,
            'volume_surge': 0,
            'macd_positive': 0,
            'all_passed': 0
        }
        
        for idx, stock_info in enumerate(self.all_stocks, 1):
            if not self.silent and idx % 50 == 0:
                print(f"진행중: {idx}/{total} ({idx/total*100:.1f}%)")
            
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            
            timeseries = DataLoader.get_stock_timeseries(self.trading_days, stock_code)
            
            # 디버그: 첫 번째 종목의 timeseries 길이 확인
            if debug and idx == 1:
                print(f"\n[디버그] 데이터 로드 확인")
                print(f"  trading_days 전체 길이: {len(self.trading_days)}일")
                print(f"  첫 종목 timeseries 길이: {len(timeseries)}일")
                if timeseries:
                    print(f"  timeseries 첫 날짜: {timeseries[0]['date']}")
                    print(f"  timeseries 마지막 날짜: {timeseries[-1]['date']}")
                print(f"  필요 최소 길이: 150일")
                print(f"  통과 여부: {'통과' if len(timeseries) >= 150 else '탈락'}\n")
            
            if len(timeseries) < 150:  # 120일 + 여유
                continue
            
            closes = [t['close'] for t in timeseries]
            highs = [t['high'] for t in timeseries]
            volumes = [t['volume'] for t in timeseries]
            lows = [t['low'] for t in timeseries]
            
            # 이동평균 계산
            ma60 = TechnicalIndicators.calculate_ma(closes, 60)
            ma120 = TechnicalIndicators.calculate_ma(closes, 120)
            
            # 20일 최고가 계산
            high_20 = TechnicalIndicators.find_highest(highs, 20)
            
            # MACD 계산
            macd_line, signal_line = TechnicalIndicators.calculate_macd(closes)
            
            # 평균 거래량 계산
            avg_volume = TechnicalIndicators.calculate_ma(volumes, 20)
            
            # 검색 범위 설정: start_date부터 end_date 사이의 인덱스 찾기
            search_start_idx = 0  # 120이 아닌 0부터 시작
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
            
            # 디버그: 첫 번째 종목에 대해 범위 확인
            if debug and idx == 1:
                print(f"\n[디버그] 첫 번째 종목: {stock_name}")
                print(f"  timeseries 길이: {len(timeseries)}")
                print(f"  timeseries 첫 날짜: {timeseries[0]['date']}")
                print(f"  timeseries 마지막 날짜: {timeseries[-1]['date']}")
                print(f"  search_start_idx: {search_start_idx} ({timeseries[search_start_idx]['date'] if search_start_idx < len(timeseries) else 'N/A'})")
                print(f"  search_end_idx: {search_end_idx}")
                print(f"  검색 범위: {search_end_idx - search_start_idx}일\n")
            
            # 전략 조건 확인 (순방향: 초기 신호 우선, 빠른 진입)
            for i in range(search_start_idx, search_end_idx):
                passed, stage = self._check_strategy_conditions(
                    i, closes, highs, volumes, lows, ma60, ma120, high_20,
                    macd_line, signal_line, avg_volume, debug
                )
                
                if debug and stage > 0:
                    debug_stats['total_checked'] += 1
                    if stage >= 1: debug_stats['trend_filter'] += 1
                    if stage >= 2: debug_stats['new_high'] += 1
                    if stage >= 3: debug_stats['volume_surge'] += 1
                    if stage >= 4: debug_stats['macd_positive'] += 1
                    if passed: debug_stats['all_passed'] += 1
                
                if passed:
                    # 조건 만족 시점의 정보 수집
                    entry_price = closes[i]
                    current_close = closes[-1]
                    
                    # 단순 고정 퍼센트 손익 (피보나치 수열 기반)
                    # 손절: -8%
                    stop_loss = int(entry_price * 0.92)
                    stop_loss_pct = -8.0
                    
                    # 1차 익절: +13% (50% 청산)
                    take_profit_1 = int(entry_price * 1.13)
                    take_profit_1_pct = 13.0
                    
                    # 2차 익절: +21% (나머지 50% 청산)
                    take_profit_2 = int(entry_price * 1.21)
                    take_profit_2_pct = 21.0
                    
                    # 지지선 계산 (참고용)
                    lookback_start = max(0, i - low_period)
                    lookback_end = i + 1
                    support_low = min(lows[lookback_start:lookback_end])
                    
                    profit_rate = ((current_close - entry_price) / entry_price) * 100 if entry_price != 0 else 0
                    
                    # 20일 최고가 대비 현재가 비율
                    high_20_breakout = ((closes[i] - high_20[i-1]) / high_20[i-1] * 100) if i > 0 and high_20[i-1] else 0
                    
                    selected_stocks.append({
                        'code': stock_code,
                        'name': stock_name,
                        'signal_date': timeseries[i]['date'],
                        'signal_index': i,
                        'entry_price': int(entry_price),
                        'current_price': int(current_close),
                        'profit_rate': round(profit_rate, 2),
                        'high_20_breakout': round(high_20_breakout, 2),
                        'volume_ratio': round(volumes[i] / avg_volume[i], 2) if avg_volume[i] and avg_volume[i] != 0 else 0,
                        'macd_value': round(macd_line[i], 2) if macd_line[i] is not None else 0,
                        'macd_signal': round(signal_line[i], 2) if signal_line[i] is not None else 0,
                        'ma60': int(ma60[i]) if ma60[i] is not None else 0,
                        'ma120': int(ma120[i]) if ma120[i] is not None else 0,
                        'stop_loss': stop_loss,
                        'stop_loss_pct': round(stop_loss_pct, 2),
                        'take_profit_1': take_profit_1,
                        'take_profit_1_pct': round(take_profit_1_pct, 2),
                        'take_profit_2': take_profit_2,
                        'take_profit_2_pct': round(take_profit_2_pct, 2),
                        'risk_reward_ratio': 1.625,  # (13+21)/2 / 8
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
                    print(f"2단계 - 20일 신고가 근접 (95~102%): {debug_stats['new_high']:,} / {debug_stats['trend_filter']:,} ({debug_stats['new_high']/debug_stats['trend_filter']*100:.1f}%)")
                if debug_stats['new_high'] > 0:
                    print(f"3단계 - 거래량 폭발 (2배): {debug_stats['volume_surge']:,} / {debug_stats['new_high']:,} ({debug_stats['volume_surge']/debug_stats['new_high']*100:.1f}%)")
                if debug_stats['volume_surge'] > 0:
                    print(f"4단계 - MACD > Signal: {debug_stats['macd_positive']:,} / {debug_stats['volume_surge']:,} ({debug_stats['macd_positive']/debug_stats['volume_surge']*100:.1f}%)")
                print(f"최종 선택: {debug_stats['all_passed']:,} 종목")
            else:
                print("분석할 데이터가 없습니다.")
        
        return selected_stocks
    
    def _check_strategy_conditions(self, idx, closes, highs, volumes, lows, ma60, ma120, high_20,
                                   macd_line, signal_line, avg_volume, debug=False):
        """전략 조건 확인 (반환: (통과여부, 도달단계))"""
        stage = 0
        
        if idx < 120:  # 최소 120일 전 데이터 필요
            return False, stage
        
        # 인덱스 범위 확인
        if (idx >= len(closes) or idx >= len(highs) or idx >= len(volumes) or
            idx >= len(ma60) or idx >= len(ma120) or idx >= len(high_20) or
            idx >= len(macd_line) or idx >= len(signal_line) or idx >= len(avg_volume)):
            return False, stage
        
        # 필수 값 확인
        if None in [ma60[idx], ma120[idx], macd_line[idx], signal_line[idx], avg_volume[idx]]:
            return False, stage
        
        if idx == 0 or high_20[idx-1] is None:
            return False, stage
        
        # 1. 추세 필터: 중장기 상승 추세 확인
        # - 60일선 > 120일선: 중장기 상승 추세
        # - 현재가 > 60일선: 단기도 상승 추세
        if ma60[idx] <= ma120[idx] or closes[idx] <= ma60[idx]:
            return False, stage
        stage = 1
        
        # 2. 20일 신고가 근접 (95~102% 범위)
        # 돌파 직전(95~100%) + 돌파 직후 초반(100~102%)을 모두 포착
        if closes[idx] < high_20[idx-1] * 0.95 or closes[idx] > high_20[idx-1] * 1.02:
            return False, stage
        stage = 2
        
        # 3. 거래량 폭발 (평균의 2배 이상)
        if avg_volume[idx] == 0 or volumes[idx] < avg_volume[idx] * 2.0:
            return False, stage
        stage = 3
        
        # 4. MACD > Signal (상승 모멘텀 확인)
        if macd_line[idx] <= signal_line[idx]:
            return False, stage
        stage = 4
        
        return True, stage


def save_results(results, start_date, end_date):
    """결과 저장 (CSV 형식)"""
    year = end_date[:4]
    output_dir = f'data/json/kospi200/{year}/result'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f'{output_dir}/momentum_trend_{start_date}_{end_date}.csv'
    
    # 신호일 기준으로 정렬
    sorted_results = sorted(results, key=lambda x: x['signal_date'])
    
    if not sorted_results:
        # 빈 결과는 빈 CSV 파일 생성
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['전략', 'Momentum + Trend Strategy'])
            writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
            writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(['선택종목수', '0'])
        print(f"\n{'='*60}")
        print(f"✓ 결과 저장 완료: {output_file}")
        print(f"{'='*60}")
        return
    
    # CSV 작성
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        # 헤더 정보
        writer = csv.writer(f)
        writer.writerow(['전략', 'Momentum + Trend Strategy'])
        writer.writerow(['분석기간', f'{start_date} ~ {end_date}'])
        writer.writerow(['생성일시', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(['선택종목수', str(len(sorted_results))])
        
        # 백테스팅 통계 (백테스팅 결과가 있는 경우)
        if 'backtest' in sorted_results[0]:
            writer.writerow([])  # 빈 줄
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
        
        writer.writerow([])  # 빈 줄
        
        # 컬럼 헤더
        if 'backtest' in sorted_results[0]:
            # 백테스팅 포함
            headers = [
                '신호일', '종목코드', '종목명', '진입가', '현재가', '수익률(%)',
                '신고가대비(%)', '거래량비율', 'MACD', 'Signal', 'MA60', 'MA120',
                '손절가', '손절률(%)', '1차익절가', '1차익절률(%)', '2차익절가', '2차익절률(%)', '지지선',
                '백테스트_진입일', '백테스트_진입가', '백테스트_청산일',
                '백테스트_청산사유', '백테스트_수익률(%)'
            ]
        else:
            # 백테스팅 없음
            headers = [
                '신호일', '종목코드', '종목명', '진입가', '현재가', '수익률(%)',
                '신고가대비(%)', '거래량비율', 'MACD', 'Signal', 'MA60', 'MA120',
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
                stock['high_20_breakout'],
                stock['volume_ratio'],
                stock['macd_value'],
                stock['macd_signal'],
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


def backtest_stocks(results, trading_days, end_date, silent=False, single_profit_cut=False):
    """백테스팅: 익일 시가 매수 후 단계적 손절/익절 확인"""
    if not silent:
        print(f"\n{'='*80}")
        print(f"백테스팅 실행 중...")
        if single_profit_cut:
            print(f"(단일 익절 모드: 21%에서 전량 청산)")
        else:
            print(f"(다단계 익절 모드: 13%에서 50%, 21%에서 50%)")
        print(f"{'='*80}\n")
    
    backtested_results = []
    
    for stock in results:
        stock_code = stock['code']
        signal_idx = stock['signal_index']
        
        # 해당 종목의 전체 시계열 데이터 가져오기
        timeseries = DataLoader.get_stock_timeseries(trading_days, stock_code)
        
        if signal_idx + 1 >= len(timeseries):
            continue
        
        # 익일 시가로 진입
        entry_price = timeseries[signal_idx + 1]['open']
        
        # 시가가 0이거나 None인 경우 스킵 (데이터 오류)
        if not entry_price or entry_price == 0:
            continue
        
        stop_loss = stock['stop_loss']
        take_profit_1 = stock['take_profit_1']
        take_profit_2 = stock['take_profit_2']
        
        # 단계적 익절 추적
        remaining_position = 1.0  # 100% 포지션
        total_profit = 0.0
        exit_date = None
        exit_reason = None
        first_exit_date = None
        first_exit_reason = None
        
        # 진입일 다음날부터 현재까지 검사
        for i in range(signal_idx + 1, len(timeseries)):
            day = timeseries[i]
            
            # 손절가 먼저 확인 (저가가 손절가 이하)
            if day['low'] <= stop_loss:
                # 남은 포지션 전량 손절
                total_profit += remaining_position * ((stop_loss - entry_price) / entry_price) * 100
                if not first_exit_date:
                    first_exit_date = day['date']
                    first_exit_reason = 'stop_loss'
                exit_date = day['date']
                exit_reason = 'stop_loss'
                remaining_position = 0.0
                break
            
            # 단일 익절 모드: 21%에서 전량 청산
            if single_profit_cut:
                if remaining_position == 1.0 and day['high'] >= take_profit_2:
                    # 전량 익절 (21%)
                    total_profit += 1.0 * ((take_profit_2 - entry_price) / entry_price) * 100
                    exit_date = day['date']
                    exit_reason = 'take_profit_2'
                    remaining_position = 0.0
                    if not first_exit_date:
                        first_exit_date = day['date']
                        first_exit_reason = 'take_profit_2'
                    break
            # 다단계 익절 모드: 13%에서 50%, 21%에서 50%
            else:
                # 1차 익절가 확인 (고가가 1차 익절가 이상)
                if remaining_position == 1.0 and day['high'] >= take_profit_1:
                    # 50% 익절
                    total_profit += 0.5 * ((take_profit_1 - entry_price) / entry_price) * 100
                    remaining_position = 0.5
                    if not first_exit_date:
                        first_exit_date = day['date']
                        first_exit_reason = 'take_profit_1'
                    # 계속 진행하여 2차 익절 체크
                
                # 2차 익절가 확인 (고가가 2차 익절가 이상)
                if remaining_position == 0.5 and day['high'] >= take_profit_2:
                    # 나머지 50% 익절
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
        
        # 최종 평균 수익률
        avg_profit_rate = total_profit
        
        backtested_stock = stock.copy()
        backtested_stock['backtest'] = {
            'entry_price': int(entry_price),
            'entry_date': timeseries[signal_idx + 1]['date'],
            'exit_date': exit_date,
            'exit_reason': exit_reason,
            'profit_rate': round(avg_profit_rate, 2),
            'first_exit_date': first_exit_date if first_exit_date else exit_date,
            'first_exit_reason': first_exit_reason if first_exit_reason else exit_reason
        }
        
        backtested_results.append(backtested_stock)
    
    return backtested_results


def print_final_summary(results, silent=False):
    """최종 결과 요약 출력"""
    if silent:
        # 간략 모드: 종목별 상세 정보만
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
            
            # 청산 사유별 메시지
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
        
        print(f"  거래량: 평균 대비 {stock['volume_ratio']:.1f}배")
        print(f"  신고가 대비: {stock['high_20_breakout']:+.2f}%")
        print(f"  MACD: {stock['macd_value']:.2f} (Signal: {stock['macd_signal']:.2f})")
        print(f"  손절가: {stock['stop_loss']:,}원 ({stock['stop_loss_pct']:+.2f}%)")
        print(f"  1차 익절가: {stock['take_profit_1']:,}원 (+{stock['take_profit_1_pct']:.1f}%, 50% 청산)")
        print(f"  2차 익절가: {stock['take_profit_2']:,}원 (+{stock['take_profit_2_pct']:.1f}%, 나머지 청산)")
        print(f"  지지선: {stock['support_low']:,}원")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='모멘텀 + 추세 전략 종목 선별 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  1. 특정 기간 분석:
     python momentum_trend.py --from 20250101 --to 20250131

  2. 어제 신호 확인:
     python momentum_trend.py

  3. 백테스팅:
     python momentum_trend.py --from 20250101 --to 20250131 --backtest

  4. 간략 출력:
     python momentum_trend.py --from 20250101 --to 20250131 --silent

  5. 디버그 모드 (각 조건별 통과율 확인):
     python momentum_trend.py --from 20250101 --to 20250131 --debug

전략 조건 (강한 모멘텀 포착):
  0. 추세 필터: 60일선 > 120일선 & 현재가 > 60일선 (필수!)
  1. 20일 신고가 돌파
  2. 거래량 폭발 (평균의 2배 이상)
  3. MACD > Signal (상승 모멘텀 확인)
        '''
    )
    
    parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    parser.add_argument('--backtest', action='store_true', help='백테스팅 모드 (--from, --to 필수)')
    parser.add_argument('--low_period', type=int, default=20, help='변동폭 계산 기간 (일, 기본값: 20, 피보나치 손익 계산에 사용)')
    parser.add_argument('--silent', action='store_true', help='간략 출력 모드 (최종 결과만 표시)')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 (각 조건별 통과율 표시)')
    parser.add_argument('--single-profit-cut', action='store_true', help='단일 익절 모드 (21%에서 전량 청산, 13% 익절 없음)')
    
    args = parser.parse_args()
    
    # 백테스팅 모드 검증
    if args.backtest and (not args.from_date or not args.to_date):
        print("❌ 백테스팅 모드는 --from, --to 옵션이 필수입니다.")
        print("\n사용 예시:")
        print("  python momentum_trend.py --from 20250101 --to 20250131 --backtest")
        sys.exit(1)
    
    if not args.silent:
        print("=" * 60)
        if args.backtest:
            print("모멘텀 + 추세 전략 종목 선별 + 백테스팅")
        else:
            print("모멘텀 + 추세 전략 종목 선별 프로그램")
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
    selected_stocks = screener.find_momentum_trend_stocks(
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
        backtested_stocks = backtest_stocks(
            selected_stocks, 
            trading_days, 
            end_date, 
            silent=args.silent,
            single_profit_cut=args.single_profit_cut
        )
        
        # 최종 결과 출력 (백테스팅 포함)
        print_final_summary(backtested_stocks, silent=args.silent)
        
        # 백테스팅 통계
        print(f"\n{'='*80}")
        if args.single_profit_cut:
            print(f"백테스팅 통계 (단일 익절: 21%에서 전량 청산)")
        else:
            print(f"백테스팅 통계 (단계적 익절: 13%에서 50%, 21%에서 나머지 50%)")
        print(f"{'='*80}")
        
        total = len(backtested_stocks)
        profits = [s['backtest']['profit_rate'] for s in backtested_stocks]
        
        # 청산 사유별 카운트
        stop_loss_count = sum(1 for s in backtested_stocks if s['backtest']['exit_reason'] == 'stop_loss')
        take_profit_1_count = sum(1 for s in backtested_stocks if s['backtest']['exit_reason'] == 'take_profit_1')
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
        
        if args.single_profit_cut:
            # 단일 익절 모드
            print(f"익절 (21%, 전량 청산): {take_profit_2_count}개 ({take_profit_2_count/total*100:.1f}%)")
            print(f"전량 홀딩: {holding_100_count}개 ({holding_100_count/total*100:.1f}%)")
        else:
            # 다단계 익절 모드
            print(f"1차 익절 (13%, 50% 청산): {take_profit_1_count}개 ({take_profit_1_count/total*100:.1f}%)")
            print(f"2차 익절 (21%, 전량 청산): {take_profit_2_count}개 ({take_profit_2_count/total*100:.1f}%)")
            print(f"1차 익절 후 홀딩: {holding_50_count}개 ({holding_50_count/total*100:.1f}%)")
            print(f"전량 홀딩: {holding_100_count}개 ({holding_100_count/total*100:.1f}%)")
        print(f"")
        print(f"평균 수익률: {avg_profit:+.2f}%")
        print(f"최대 수익률: {max_profit:+.2f}%")
        print(f"최소 수익률: {min_profit:+.2f}%")
        print(f"{'='*80}")
        
        # 결과 저장
        save_results(backtested_stocks, start_date, end_date)
    else:
        # 백테스팅 없는 경우
        print_final_summary(selected_stocks, silent=args.silent)
        save_results(selected_stocks, start_date, end_date)


if __name__ == "__main__":
    main()

