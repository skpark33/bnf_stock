import json
import os
import argparse
import sys
import pandas as pd
from datetime import datetime, timedelta
from pykrx import stock
import time
import warnings
warnings.filterwarnings('ignore')


class BNFBacktester:
    """BNF 매매법 백테스팅"""

    def __init__(self, config_file=None):
        """백테스터 초기화"""
        self.selected_stocks = []
        self.config = None

        if config_file:
            self._load_config(config_file)

    def _load_config(self, config_file):
        """설정 파일 로드"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"✓ 설정 파일 '{config_file}' 로드 완료\n")
        except FileNotFoundError:
            print(f"❌ 설정 파일 '{config_file}'을 찾을 수 없습니다.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"❌ 설정 파일 '{config_file}'의 JSON 형식이 잘못되었습니다.")
            sys.exit(1)

    def load_json_files(self, from_date, to_date):
        """기간 내 모든 JSON 파일 로드"""
        print("=" * 60)
        print(f"JSON 파일 로딩 중... ({from_date} ~ {to_date})")
        print("=" * 60)

        start = datetime.strptime(from_date, "%Y%m%d")
        end = datetime.strptime(to_date, "%Y%m%d")

        current = start
        loaded_files = 0
        total_stocks = 0

        while current <= end:
            date_str = current.strftime("%Y%m%d")
            json_file = f"data/json/result_{date_str}.json"

            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    trading_date = data.get('trading_date', date_str)
                    stocks = data.get('selected_stocks', [])

                    for stock_data in stocks:
                        # 필요한 정보 추출
                        stock_info = {
                            'trading_date': trading_date,
                            'code': stock_data['code'],
                            'name': stock_data['name'],
                            'entry_price': stock_data['price'],
                            'stop_loss_price': stock_data['trading_strategy']['stop_loss']['price'],
                            'take_profit_level1_price': stock_data['trading_strategy']['take_profit'][0]['price'] if len(stock_data['trading_strategy']['take_profit']) > 0 else None,
                            'take_profit_level2_price': stock_data['trading_strategy']['take_profit'][1]['price'] if len(stock_data['trading_strategy']['take_profit']) > 1 else None,
                        }
                        self.selected_stocks.append(stock_info)
                        total_stocks += 1

                    loaded_files += 1
                    print(f"✓ {date_str}: {len(stocks)}개 종목 로드")

                except Exception as e:
                    print(f"❌ {json_file} 로드 실패: {e}")

            current += timedelta(days=1)

        print(f"\n총 {loaded_files}개 파일에서 {total_stocks}개 종목 로드 완료\n")
        return self.selected_stocks

    def get_stock_price_data(self, stock_code, start_date, end_date, max_retries=3):
        """주가 데이터 가져오기 (재시도 로직 포함)"""
        for attempt in range(max_retries):
            try:
                df = stock.get_market_ohlcv(start_date, end_date, stock_code)
                if df is not None and not df.empty:
                    return df
                time.sleep(0.1)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.2 * (attempt + 1))
                else:
                    print(f"  ⚠️  {stock_code} 데이터 조회 실패: {e}")
                    return None
        return None

    def simulate_trading(self, stock_info):
        """개별 종목 매매 시뮬레이션"""
        code = stock_info['code']
        name = stock_info['name']
        trading_date = stock_info['trading_date']
        entry_price = stock_info['entry_price']
        stop_loss = stock_info['stop_loss_price']
        tp_level1 = stock_info['take_profit_level1_price']
        tp_level2 = stock_info['take_profit_level2_price']

        # 거래일 이후 30일 계산
        start_date = datetime.strptime(trading_date, "%Y%m%d")
        # 다음날부터 시작 (거래일 당일은 이미 진입한 것으로 간주)
        start_date = start_date + timedelta(days=1)
        end_date = start_date + timedelta(days=30)

        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")

        # 주가 데이터 가져오기
        df = self.get_stock_price_data(code, start_date_str, end_date_str)

        if df is None or df.empty:
            # 데이터가 없으면 스킵
            print(f"  ⚠️  {name} ({code}): {start_date_str}~{end_date_str} 데이터 없음")
            return None

        # 매매 시뮬레이션 변수
        position = 1.0  # 보유 비율 (100%)
        total_profit = 0.0
        sold_level1 = False
        sold_level2 = False
        exit_price = None
        exit_date = None
        exit_reason = None

        # 일별 데이터 순회
        for date, row in df.iterrows():
            date_str = date.strftime("%Y%m%d")
            high = row['고가']
            low = row['저가']
            close = row['종가']

            # 손절가 체크 (저가가 손절가 이하)
            if low <= stop_loss and position > 0:
                # 전량 손절
                profit = (stop_loss - entry_price) * position
                total_profit += profit
                exit_price = stop_loss
                exit_date = date_str
                exit_reason = "손절"
                position = 0
                break

            # 익절 Level 1 체크 (고가가 익절1 이상)
            if not sold_level1 and tp_level1 and high >= tp_level1 and position > 0:
                # 20% 익절
                profit = (tp_level1 - entry_price) * 0.2
                total_profit += profit
                position -= 0.2
                sold_level1 = True

                if exit_date is None:
                    exit_date = date_str
                    exit_price = tp_level1
                    exit_reason = "익절1차"

            # 익절 Level 2 체크 (고가가 익절2 이상)
            if not sold_level2 and tp_level2 and high >= tp_level2 and position > 0:
                # 나머지 전량 익절 (80% 또는 전량)
                profit = (tp_level2 - entry_price) * position
                total_profit += profit
                position = 0
                sold_level2 = True
                exit_price = tp_level2
                exit_date = date_str
                exit_reason = "익절2차" if sold_level1 else "익절전량"
                break

        # 30일 내에 모두 매도되지 않았다면 마지막 날 종가로 매도
        if position > 0:
            last_close = df.iloc[-1]['종가']
            last_date = df.index[-1].strftime("%Y%m%d")
            profit = (last_close - entry_price) * position
            total_profit += profit
            exit_price = last_close
            exit_date = last_date
            if exit_reason is None:
                exit_reason = "기간만료"
            else:
                exit_reason = exit_reason + "+기간만료"
            position = 0

        # 수익률 계산
        profit_rate = (total_profit / entry_price) * 100

        result = {
            'trading_date': trading_date,
            'code': code,
            'name': name,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss,
            'tp_level1_price': tp_level1,
            'tp_level2_price': tp_level2,
            'exit_price': exit_price,
            'exit_date': exit_date,
            'exit_reason': exit_reason,
            'profit': round(total_profit, 2),
            'profit_rate': round(profit_rate, 2)
        }

        return result

    def run_backtest(self):
        """전체 백테스팅 실행"""
        print("=" * 60)
        print("백테스팅 시작...")
        print("=" * 60)

        results = []
        total = len(self.selected_stocks)

        for idx, stock_info in enumerate(self.selected_stocks, 1):
            if idx % 10 == 0:
                print(f"진행중: {idx}/{total} ({idx/total*100:.1f}%)")

            result = self.simulate_trading(stock_info)

            if result:
                results.append(result)
                # 간단한 진행 상황 출력
                profit_symbol = "💰" if result['profit_rate'] > 0 else "💔"
                print(f"{profit_symbol} {result['name']} ({result['code']}): {result['profit_rate']:+.2f}% - {result['exit_reason']}")

            # API 부하 방지
            time.sleep(0.1)

        print(f"\n백테스팅 완료! 총 {len(results)}개 종목 분석됨\n")

        return results

    def save_results(self, results, from_date, to_date):
        """결과를 CSV로 저장"""
        if not results:
            print("저장할 결과가 없습니다.")
            return

        # data/profit 폴더 생성
        os.makedirs('data/profit', exist_ok=True)

        # CSV 파일명
        csv_filename = f"data/profit/{from_date}-{to_date}.csv"

        # DataFrame 생성
        df = pd.DataFrame(results)

        # 컬럼 순서 정리
        columns_order = [
            'trading_date', 'code', 'name',
            'entry_price', 'tp_level1_price', 'tp_level2_price', 'stop_loss_price',
            'exit_date', 'exit_price', 'exit_reason',
            'profit', 'profit_rate'
        ]

        df = df[columns_order]

        # 컬럼명 한글화
        df.columns = [
            '선택일자', '종목코드', '종목명',
            '진입가격', '익절1차가격', '익절2차가격', '손절가격',
            '청산일자', '청산가격', '청산사유',
            '순이익', '순이익률(%)'
        ]

        # CSV 저장
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

        print(f"✓ CSV 저장: {csv_filename}\n")

        # 통계 출력
        self.print_statistics(df)

    def print_statistics(self, df):
        """백테스팅 통계 출력"""
        print("=" * 60)
        print("백테스팅 통계")
        print("=" * 60)

        total_trades = len(df)
        winning_trades = len(df[df['순이익률(%)'] > 0])
        losing_trades = len(df[df['순이익률(%)'] < 0])
        breakeven_trades = len(df[df['순이익률(%)'] == 0])

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        avg_profit_rate = df['순이익률(%)'].mean()
        max_profit_rate = df['순이익률(%)'].max()
        min_profit_rate = df['순이익률(%)'].min()

        total_profit = df['순이익'].sum()

        print(f"총 거래 수: {total_trades}건")
        print(f"수익 거래: {winning_trades}건")
        print(f"손실 거래: {losing_trades}건")
        print(f"무승부: {breakeven_trades}건")
        print(f"승률: {win_rate:.2f}%")
        print(f"\n평균 수익률: {avg_profit_rate:+.2f}%")
        print(f"최대 수익률: {max_profit_rate:+.2f}%")
        print(f"최소 수익률: {min_profit_rate:+.2f}%")
        print(f"총 순이익: {total_profit:+,.2f}원")
        print("=" * 60)

        # 청산 사유별 통계
        print("\n청산 사유별 분포:")
        print("-" * 60)
        exit_reasons = df['청산사유'].value_counts()
        for reason, count in exit_reasons.items():
            pct = (count / total_trades * 100)
            print(f"{reason}: {count}건 ({pct:.1f}%)")
        print("=" * 60)

        # 상위/하위 5개 종목
        print("\n수익률 상위 5개 종목:")
        print("-" * 60)
        top5 = df.nlargest(5, '순이익률(%)')
        for idx, row in top5.iterrows():
            print(f"{row['종목명']} ({row['종목코드']}): {row['순이익률(%)']:+.2f}% - {row['청산사유']}")

        print("\n수익률 하위 5개 종목:")
        print("-" * 60)
        bottom5 = df.nsmallest(5, '순이익률(%)')
        for idx, row in bottom5.iterrows():
            print(f"{row['종목명']} ({row['종목코드']}): {row['순이익률(%)']:+.2f}% - {row['청산사유']}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='BNF 매매법 백테스팅 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  python bnf_stock_back_test.py --config config.json --from 20250101 --to 20250131
        '''
    )

    parser.add_argument('--config', help='설정 파일 경로 (JSON)')
    parser.add_argument('--from', dest='from_date', required=True, help='시작일 (YYYYMMDD) - 필수')
    parser.add_argument('--to', dest='to_date', required=True, help='종료일 (YYYYMMDD) - 필수')

    args = parser.parse_args()

    print("=" * 60)
    print("BNF 매매법 백테스팅 프로그램")
    print("=" * 60)

    # 날짜 검증
    try:
        from_date = datetime.strptime(args.from_date, "%Y%m%d")
        to_date = datetime.strptime(args.to_date, "%Y%m%d")

        if from_date > to_date:
            print("❌ 시작일이 종료일보다 늦을 수 없습니다.")
            sys.exit(1)
    except ValueError:
        print("❌ 날짜 형식이 잘못되었습니다. YYYYMMDD 형식으로 입력해주세요.")
        sys.exit(1)

    print(f"\n분석 기간: {args.from_date} ~ {args.to_date}\n")

    # 백테스터 초기화
    backtester = BNFBacktester(config_file=args.config)

    # JSON 파일 로드
    selected_stocks = backtester.load_json_files(args.from_date, args.to_date)

    if not selected_stocks:
        print("❌ 해당 기간에 선택된 종목이 없습니다.")
        sys.exit(1)

    # 백테스팅 실행
    results = backtester.run_backtest()

    # 결과 저장
    if results:
        backtester.save_results(results, args.from_date, args.to_date)
    else:
        print("❌ 백테스팅 결과가 없습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
