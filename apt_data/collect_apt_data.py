from apt_trade import AptTradeCollector
from region_code import RegionCode
from datetime import datetime, timedelta
import pandas as pd
import os
from dateutil.relativedelta import relativedelta

def collect_monthly_data(city='서울', year_month=None):
    """
    특정 도시의 모든 구에 대해 월별 아파트 거래 데이터 수집
    """
    # 수집기 초기화
    collector = AptTradeCollector()
    region = RegionCode()
    
    # 년월 설정 (기본값: 이전 달)
    if year_month is None:
        today = datetime.now()
        first = today.replace(day=1)
        last_month = first - timedelta(days=1)
        year_month = last_month.strftime('%Y%m')
    
    # 해당 도시의 모든 구 코드 가져오기
    districts = region.get_districts(city)
    
    results = []
    for district in districts:
        code = region.get_code(city, district)
        if code:
            # 데이터 수집 및 저장
            collector.save_trade_data(code, year_month)
            
            # 거래량 집계
            volume = collector.get_monthly_volume(code, year_month)
            results.append({
                '도시': city,
                '구': district,
                '년월': year_month,
                '거래량': volume
            })
    
    # 결과를 데이터프레임으로 변환
    df = pd.DataFrame(results)
    
    # 거래량 요약 저장
    summary_dir = 'apt_data/summary'
    if not os.path.exists(summary_dir):
        os.makedirs(summary_dir)
    
    summary_file = f"{summary_dir}/volume_summary_{city}_{year_month}.csv"
    df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    
    return df

def collect_national_monthly_data(last_n_months=12):
    """전국 아파트 매매 거래량을 수집합니다."""
    print("전국 아파트 거래량 수집 중...")
    
    # 데이터 수집기 초기화
    collector = AptTradeCollector()
    
    # 수집할 월 목록 생성
    today = datetime.now()
    months = []
    for i in range(last_n_months):
        target_date = today - relativedelta(months=i)
        months.append(target_date.strftime("%Y%m"))
    
    # 전국 데이터 수집
    all_data = []
    for year_month in months:
        print(f"{year_month} 데이터 수집 중...")
        df = collector.get_national_trade_data(year_month)
        if not df.empty:
            # 월별 거래량 집계
            volume_by_sido = df.groupby('시도').size().reset_index(name='거래량')
            volume_by_sido['년월'] = year_month
            
            # 전국 총계 추가
            total_volume = pd.DataFrame([{
                '시도': '전국',
                '거래량': volume_by_sido['거래량'].sum(),
                '년월': year_month
            }])
            
            all_data.append(pd.concat([volume_by_sido, total_volume]))
    
    if not all_data:
        print("데이터 수집 실패")
        return pd.DataFrame()
    
    # 전체 데이터 합치기
    result_df = pd.concat(all_data, ignore_index=True)
    
    # 결과 저장
    os.makedirs('apt_data/summary', exist_ok=True)
    result_df.to_csv('apt_data/summary/national_volume_summary_all.csv', index=False, encoding='utf-8-sig')
    
    return result_df

if __name__ == "__main__":
    # 최근 12개월의 전국 아파트 거래 데이터 수집
    print("전국 아파트 거래량 수집 중...")
    result_df = collect_national_monthly_data(last_n_months=12)
    
    if not result_df.empty:
        # 전국 월별 거래량 출력
        national_summary = result_df[result_df['시도'] == '전국'].sort_values('년월', ascending=False)
        print("\n전국 월별 거래량 요약:")
        print(national_summary[['년월', '거래량']])
        
        # 최근 월의 시도별 거래량 출력
        latest_month = result_df['년월'].max()
        sido_summary = result_df[
            (result_df['년월'] == latest_month) & 
            (result_df['시도'] != '전국')
        ].sort_values('거래량', ascending=False)
        
        print(f"\n{latest_month} 시도별 거래량 요약:")
        print(sido_summary[['시도', '거래량']])
    else:
        print("데이터 수집 실패") 