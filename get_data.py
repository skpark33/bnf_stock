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

        print("📊 KOSPI 200 데이터 수집 모드 (pykrx 사용)")

    def get_kospi200_stocks(self, use_cache=True, cache_file="kospi_200_code.json"):
        """KOSPI 200 종목 코드 조회 (캐싱 지원)"""
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    print(f"✓ 캐시 파일에서 KOSPI 200 종목 {len(cached_data['stocks'])}개 로드 완료")
                    print(f"  캐시 생성일: {cached_data['created_at']}")
                    return cached_data['stocks']
            except Exception as e:
                print(f"⚠️ 캐시 파일 읽기 실패: {e}")
                print("  새로 종목 코드를 가져옵니다...")

        try:
            stock_codes = stock.get_index_portfolio_deposit_file("1028")

            stocks = []
            for code in stock_codes:
                name = stock.get_market_ticker_name(code)
                stocks.append({
                    'code': code,
                    'name': name
                })

            print(f"✓ KOSPI 200 종목 {len(stocks)}개 로드 완료")

            if use_cache:
                try:
                    cache_data = {
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'stocks': stocks
                    }
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=2)
                    print(f"✓ 종목 코드를 '{cache_file}'에 저장했습니다.")
                except Exception as e:
                    print(f"⚠️ 캐시 파일 저장 실패: {e}")

            return stocks
        except Exception as e:
            print(f"❌ KOSPI 200 종목 코드 조회 실패: {e}")
            return []

    def get_historical_data_pykrx(self, stock_code, target_date):
        """pykrx를 이용한 특정일 데이터 조회"""
        try:
            df = stock.get_market_ohlcv(target_date, target_date, stock_code)
            if df.empty:
                return None
            return df
        except Exception as e:
            return None


class DataCollector:
    """KOSPI 200 전체 데이터 수집"""

    def __init__(self, api_client):
        self.api = api_client

    def get_output_file_path(self, year):
        """연도별 출력 파일 경로 반환"""
        return f"data/json/kospi200/{year}/kospi200_data.json"

    def is_trading_day(self, target_date):
        """거래일인지 확인"""
        try:
            # KOSPI 지수로 거래일 확인
            df = stock.get_index_ohlcv(target_date, target_date, "1001")
            return not df.empty
        except:
            return False

    def collect_data_for_date(self, stock_codes, target_date):
        """특정 날짜의 KOSPI 200 전체 종목 데이터 수집"""
        date_str = target_date
        date_obj = datetime.strptime(target_date, "%Y%m%d")
        
        print(f"\n{'='*60}")
        print(f"📅 데이터 수집 날짜: {date_obj.strftime('%Y-%m-%d')} ({date_obj.strftime('%A')})")
        print(f"{'='*60}")

        # 거래일 확인
        if not self.is_trading_day(target_date):
            print(f"⚠️  {target_date}는 휴장일입니다.")
            return {
                'date': target_date,
                'is_holiday': True,
                'stocks': []
            }

        print(f"✓ 거래일 확인 완료")
        
        results = []
        total = len(stock_codes)

        print(f"📊 총 {total}개 종목 데이터 수집 시작...")
        print("-" * 60)

        for idx, stock_info in enumerate(stock_codes, 1):
            try:
                if idx % 50 == 0:
                    print(f"진행중: {idx}/{total} ({idx/total*100:.1f}%)")

                stock_code = stock_info['code']
                stock_name = stock_info['name']

                # API 호출 간격 (과부하 방지)
                time.sleep(0.05)

                df = self.api.get_historical_data_pykrx(stock_code, target_date)
                
                if df is None or df.empty:
                    continue

                # 데이터 추출
                row = df.iloc[0]
                
                result = {
                    'code': stock_code,
                    'name': stock_name,
                    'open': int(row['시가']),
                    'high': int(row['고가']),
                    'low': int(row['저가']),
                    'close': int(row['종가']),
                    'volume': int(row['거래량']),
                    'value': int(row['거래대금']) if '거래대금' in row else 0
                }
                
                results.append(result)

            except Exception as e:
                # 에러 발생 시 해당 종목은 건너뛰기
                continue

        print(f"\n✓ 데이터 수집 완료: {len(results)}/{total}개 종목")

        return {
            'date': target_date,
            'is_holiday': False,
            'stocks': results
        }

    def save_results_by_year(self, all_data):
        """수집된 데이터를 연도별로 JSON 파일로 저장"""
        try:
            # 연도별로 데이터 그룹화
            data_by_year = {}
            for day_data in all_data:
                year = day_data['date'][:4]  # YYYYMMDD에서 YYYY 추출
                if year not in data_by_year:
                    data_by_year[year] = []
                data_by_year[year].append(day_data)

            # 연도별로 파일 저장
            for year, year_data in data_by_year.items():
                output_file = self.get_output_file_path(year)
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                output = {
                    'year': year,
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'total_days': len(year_data),
                    'data': year_data
                }

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)

                trading_days = sum(1 for d in year_data if not d['is_holiday'])
                holidays = len(year_data) - trading_days
                
                print(f"\n{'='*60}")
                print(f"✓ JSON 저장 완료: {output_file}")
                print(f"  {year}년: 총 {len(year_data)}일 (거래일: {trading_days}일, 휴장일: {holidays}일)")
                print(f"{'='*60}")

        except Exception as e:
            print(f"❌ 결과 저장 실패: {e}")


def load_existing_data_by_year(year):
    """특정 연도의 기존 JSON 파일 로드"""
    output_file = f"data/json/kospi200/{year}/kospi200_data.json"
    if not os.path.exists(output_file):
        return None
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ {year}년 파일 로드 실패: {e}")
        return None


def get_all_years_from_directory():
    """저장된 모든 연도 목록 가져오기"""
    base_dir = "data/json/kospi200"
    if not os.path.exists(base_dir):
        return []
    
    years = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and item.isdigit() and len(item) == 4:
            years.append(item)
    
    return sorted(years)


def get_last_date_from_all_data():
    """모든 연도 데이터에서 마지막 날짜 추출"""
    years = get_all_years_from_directory()
    if not years:
        return None
    
    # 가장 최근 연도부터 역순으로 확인
    for year in reversed(years):
        data = load_existing_data_by_year(year)
        if data and 'data' in data and data['data']:
            dates = [d['date'] for d in data['data']]
            dates.sort()
            return dates[-1]
    
    return None


def merge_data_by_year(new_data):
    """신규 데이터를 연도별로 기존 데이터와 병합"""
    # 연도별로 데이터 그룹화
    data_by_year = {}
    for day_data in new_data:
        year = day_data['date'][:4]
        if year not in data_by_year:
            data_by_year[year] = []
        data_by_year[year].append(day_data)

    # 각 연도별로 병합
    for year, year_new_data in data_by_year.items():
        output_file = f"data/json/kospi200/{year}/kospi200_data.json"
        existing_data = load_existing_data_by_year(year)
        
        if existing_data:
            # 기존 데이터가 있으면 병합
            existing_dates = {d['date'] for d in existing_data['data']}
            
            # 중복되지 않은 신규 데이터만 추가
            for new_entry in year_new_data:
                if new_entry['date'] not in existing_dates:
                    existing_data['data'].append(new_entry)
            
            # 날짜순 정렬
            existing_data['data'].sort(key=lambda x: x['date'])
            
            # 메타데이터 업데이트
            existing_data['generated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            existing_data['total_days'] = len(existing_data['data'])
        else:
            # 기존 데이터가 없으면 새로 생성
            existing_data = {
                'year': year,
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_days': len(year_new_data),
                'data': sorted(year_new_data, key=lambda x: x['date'])
            }
        
        # 저장
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        trading_days = sum(1 for d in existing_data['data'] if not d['is_holiday'])
        holidays = existing_data['total_days'] - trading_days
        
        print(f"\n{'='*60}")
        print(f"✓ 데이터 병합 완료: {output_file}")
        print(f"  {year}년: 총 {existing_data['total_days']}일 (거래일: {trading_days}일, 휴장일: {holidays}일)")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='KOSPI 200 종목 전체 데이터 수집 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  1. 특정 기간 데이터 수집:
     python get_data.py --config config.json --from 20250101 --to 20250131

  2. 특정일 데이터 수집:
     python get_data.py --config config.json --from 20250115

  3. 누락된 데이터 추가 (마지막 날짜 다음날부터 어제까지):
     python get_data.py --config config.json --add

출력:
  - data/json/kospi200/[연도]/kospi200_data.json (연도별로 파일 분리)
  - 휴장일은 date와 is_holiday: true로 표시됨
        '''
    )

    parser.add_argument('--config', required=True, help='설정 파일 경로 (JSON)')
    parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    parser.add_argument('--add', action='store_true', 
                       help='기존 데이터의 마지막 날짜 다음날부터 어제까지 데이터 추가')

    args = parser.parse_args()

    print("=" * 60)
    print("KOSPI 200 종목 데이터 수집 프로그램")
    print("=" * 60)

    # --add 옵션 처리
    if args.add:
        print("\n📌 --add 옵션: 누락된 데이터 추가 모드")
        
        last_date = get_last_date_from_all_data()
        if not last_date:
            print(f"❌ 기존 데이터 파일이 없습니다.")
            print("   --from 옵션을 사용하여 처음부터 데이터를 수집하세요.")
            sys.exit(1)
        
        print(f"✓ 기존 데이터 마지막 날짜: {last_date}")
        
        # 마지막 날짜 다음날부터 어제까지
        start_date = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        
        if start_date > end_date:
            print(f"✓ 추가할 데이터가 없습니다. (마지막 날짜가 최신입니다)")
            sys.exit(0)
        
        print(f"📅 추가 수집 기간: {start_date} ~ {end_date}")
        
        args.from_date = start_date
        args.to_date = end_date

    # 날짜 범위 처리
    if not args.from_date:
        print("❌ --from 옵션 또는 --add 옵션이 필요합니다.")
        print("\n사용 예시:")
        print("  python get_data.py --config config.json --from 20250101 --to 20250131")
        print("  python get_data.py --config config.json --add")
        sys.exit(1)

    try:
        start = datetime.strptime(args.from_date, "%Y%m%d")
        end = datetime.strptime(args.to_date, "%Y%m%d") if args.to_date else start

        date_list = []
        current = start
        while current <= end:
            date_list.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)

        print(f"\n📅 데이터 수집 기간: {args.from_date} ~ {end.strftime('%Y%m%d')}")
        print(f"   총 {len(date_list)}일 처리 예정\n")

    except ValueError:
        print("❌ 날짜 형식이 잘못되었습니다. YYYYMMDD 형식으로 입력해주세요.")
        sys.exit(1)

    # 설정 파일 로드
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

    # API 클라이언트 초기화 (실제로는 pykrx만 사용하지만 config 호환성을 위해 유지)
    try:
        api = KISAPIClient(
            app_key,
            app_secret,
            account,
            mock=mock
        )
    except Exception as e:
        print(f"\n❌ API 초기화 실패: {e}")
        sys.exit(1)

    # 종목 코드 로딩
    print("=" * 60)
    print("KOSPI 200 종목 코드 로딩 중...")
    print("=" * 60)

    kospi200_stocks = api.get_kospi200_stocks(use_cache=True)
    
    if not kospi200_stocks:
        print("❌ 종목 코드를 가져올 수 없습니다.")
        sys.exit(1)
    
    print(f"✓ 총 {len(kospi200_stocks)}개 종목 로드 완료\n")

    # 데이터 수집
    collector = DataCollector(api)
    all_data = []

    for target_date in date_list:
        date_data = collector.collect_data_for_date(kospi200_stocks, target_date)
        all_data.append(date_data)
        time.sleep(0.5)  # 날짜 간 대기

    # 결과 저장 (--add 옵션인 경우 병합, 아니면 새로 저장)
    if args.add:
        merge_data_by_year(all_data)
    else:
        collector.save_results_by_year(all_data)

    print("\n✅ 작업 완료!")


if __name__ == "__main__":
    main()

