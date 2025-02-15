import requests
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
import json
from pathlib import Path
import time
from region_code import RegionCode

# .env 파일 로드
load_dotenv()

class AptTradeCollector:
    def __init__(self):
        self.api_key = os.getenv('APT_API_KEY')
        self.base_url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev"
        self.cache_dir = Path('apt_data/cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.request_delay = 0.5  # API 요청 간 0.5초 딜레이
        self.region_code = RegionCode()
        
    def _get_cache_path(self, params):
        """캐시 파일 경로 생성"""
        # 파라미터를 정렬하여 일관된 캐시 키 생성
        # API 키는 제외하고 나머지 파라미터로 캐시 키 생성
        cache_params = {k: v for k, v in params.items() if k != 'serviceKey'}
        cache_key = '_'.join(f"{k}_{v}" for k, v in sorted(cache_params.items()))
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_cached_data(self, params):
        """캐시된 데이터 조회"""
        cache_path = self._get_cache_path(params)
        if cache_path.exists():
            cache_age = time.time() - cache_path.stat().st_mtime
            # 캐시 유효기간: 24시간
            if cache_age < 24 * 60 * 60:
                try:
                    with cache_path.open('r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return None
        return None
    
    def _save_to_cache(self, params, data):
        """데이터를 캐시에 저장"""
        cache_path = self._get_cache_path(params)
        with cache_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _call_api(self, params):
        """API 호출 및 응답 처리"""
        # 캐시 확인
        cached_data = self._get_cached_data(params)
        if cached_data:
            print(f"Using cached data for {params.get('DEAL_YMD')}")
            return cached_data
        
        # API 호출
        url = f"{self.base_url}/getRTMSDataSvcAptTradeDev"
        all_items = []
        page_no = 1
        total_count = None
        
        try:
            while True:
                # 페이지 파라미터 설정
                params['numOfRows'] = '1000'  # 한 페이지당 1000건으로 증가
                params['pageNo'] = str(page_no)
                
                response = requests.get(url, params=params)
                
                # 응답 내용 출력 (디버깅용)
                print(f"\nAPI Response for {params.get('DEAL_YMD')} (Page {page_no}):")
                print(f"Status Code: {response.status_code}")
                
                # HTTP 에러 체크
                if response.status_code != 200:
                    print(f"HTTP Error: {response.status_code}")
                    break
                
                root = ET.fromstring(response.text)
                
                # API 응답 코드 확인
                result_code = root.findtext('.//resultCode')
                result_msg = root.findtext('.//resultMsg')
                
                if result_code != '000':
                    print(f"API Error: {result_msg} (Code: {result_code})")
                    break
                
                # 전체 건수 확인
                if total_count is None:
                    total_count = int(root.findtext('.//totalCount') or 0)
                    print(f"Total count: {total_count}")
                
                # 데이터 파싱
                items = []
                for item in root.findall('.//item'):
                    data = {child.tag: child.text for child in item}
                    items.append(data)
                
                if not items:
                    print(f"No more data found for {params.get('DEAL_YMD')} after page {page_no-1}")
                    break
                
                all_items.extend(items)
                print(f"Found {len(items)} records on page {page_no} (Total: {len(all_items)}/{total_count})")
                
                # 모든 데이터를 가져왔는지 확인
                if len(all_items) >= total_count:
                    break
                
                # 다음 페이지로
                page_no += 1
                
                # API 호출 간 딜레이
                time.sleep(self.request_delay)
            
            if all_items:
                print(f"\nTotal records found: {len(all_items)}")
                try:
                    # 캐시 저장
                    self._save_to_cache(params, all_items)
                except Exception as e:
                    print(f"Cache save error: {str(e)}")
            
            return all_items
                
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            return None
        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return None
    
    def get_trade_data(self, lawd_cd, deal_ymd):
        """
        아파트 매매 실거래자료 수집
        lawd_cd : 지역코드 (시군구 5자리)
        deal_ymd : 계약월 (YYYYMM)
        """
        params = {
            'serviceKey': self.api_key,
            'LAWD_CD': lawd_cd,
            'DEAL_YMD': deal_ymd
        }
        
        items = self._call_api(params)
        if not items:
            return pd.DataFrame()
        
        try:
            # 데이터프레임 변환
            df = pd.DataFrame(items)
            if not df.empty:
                print("\n실제 응답 컬럼:")
                print(list(df.columns))
                
                # 컬럼명 한글로 변환
                column_mapping = {
                    'dealYear': '년도',
                    'dealMonth': '월',
                    'dealDay': '일',
                    'sggCd': '시군구코드',
                    'umdNm': '법정동',
                    'aptNm': '아파트명',
                    'dealAmount': '거래금액',
                    'buildYear': '건축년도',
                    'floor': '층',
                    'excluUseAr': '전용면적',
                    'estateAgentSggNm': '시군구'
                }
                
                # 존재하는 컬럼만 매핑
                actual_columns = df.columns
                valid_mapping = {k: v for k, v in column_mapping.items() if k in actual_columns}
                df = df.rename(columns=valid_mapping)
                
                # 거래금액 전처리
                if '거래금액' in df.columns:
                    df['거래금액'] = df['거래금액'].str.strip().str.replace(',', '').astype(float)
                
                # 전용면적 숫자로 변환
                if '전용면적' in df.columns:
                    df['전용면적'] = pd.to_numeric(df['전용면적'], errors='coerce')
                
                # 건축년도 숫자로 변환
                if '건축년도' in df.columns:
                    df['건축년도'] = pd.to_numeric(df['건축년도'], errors='coerce')
                
                # 층수 숫자로 변환
                if '층' in df.columns:
                    df['층'] = pd.to_numeric(df['층'], errors='coerce')
                
                # 시군구 정보 추가
                if '시군구' not in df.columns and '시군구코드' in df.columns:
                    df['시군구'] = df['시군구코드'].apply(lambda x: lawd_cd)
                
                # 년월 필드 추가
                df['년월'] = deal_ymd
                
                return df
            
        except Exception as e:
            print(f"\nData Processing Error: {str(e)}")
            print(f"Data sample: {items[0] if items else 'No items'}")
            print("\nColumns in response:")
            print(list(pd.DataFrame(items).columns))
        
        return pd.DataFrame()
    
    def get_national_trade_data(self, deal_ymd):
        """
        전국 아파트 매매 실거래자료 수집
        deal_ymd : 계약월 (YYYYMM)
        """
        # 지역코드 초기화
        region = RegionCode()
        all_data = []
        
        # 시도별 대표 코드로 데이터 수집
        for city, code in region.get_representative_codes().items():
            print(f"\n{city} 지역 데이터 수집 중...")
            df = self.get_trade_data(code, deal_ymd)
            if not df.empty:
                # 시도 정보 추가
                df['시도'] = city
                all_data.append(df)
                print(f"=> {len(df)}건 수집 완료")
        
        # 전체 데이터 합치기
        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            print(f"\n전체 {len(result_df)}건의 거래 데이터 수집 완료")
            return result_df
        
        return pd.DataFrame()
    
    def get_total_volume(self, year_month):
        """전국 아파트 거래량을 조회합니다."""
        total_volume = 0
        region_volumes = {}

        for city, districts in self.region_code.codes.items():
            city_volume = 0
            print(f"\n{city} 지역 거래량 조회 중...")
            
            for district, code in districts.items():
                try:
                    params = {
                        'serviceKey': self.api_key,
                        'LAWD_CD': code,
                        'DEAL_YMD': year_month
                    }
                    items = self._call_api(params)
                    district_volume = len(items) if items else 0
                    city_volume += district_volume
                    print(f"  - {district}: {district_volume}건")
                    time.sleep(0.5)  # API 호출 간격 조절
                except Exception as e:
                    print(f"  - {district} 조회 실패: {str(e)}")
                    continue
            
            region_volumes[city] = city_volume
            total_volume += city_volume
            print(f"{city} 총 거래량: {city_volume}건")

        print("\n=== 전국 아파트 매매 거래량 요약 ===")
        for city, volume in region_volumes.items():
            print(f"{city}: {volume}건")
        print(f"\n전국 총 거래량: {total_volume}건")
        
        return total_volume

    def get_monthly_volume_summary(self, year_month):
        """특정 년월의 전국 아파트 거래량을 조회합니다."""
        print(f"\n{year_month} 전국 아파트 매매 거래량 조회를 시작합니다...")
        return self.get_total_volume(year_month)

    def save_monthly_summary(self, year_month, output_dir='apt_data/summary'):
        """
        월별 거래량 요약 저장
        """
        df = self.get_monthly_volume_summary(year_month)
        if df.empty:
            return False
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filename = f"national_volume_{year_month}.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return True
    
    def get_monthly_volume(self, lawd_cd, year_month):
        """
        특정 지역, 특정 월의 거래량 집계
        """
        df = self.get_trade_data(lawd_cd, year_month)
        if df.empty:
            return 0
        return len(df)
    
    def save_trade_data(self, lawd_cd, year_month, output_dir='apt_data'):
        """
        거래 데이터를 CSV 파일로 저장
        """
        df = self.get_trade_data(lawd_cd, year_month)
        if df.empty:
            return False
            
        # 저장 디렉토리 생성
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 파일명 생성 (예: apt_trade_11110_202402.csv)
        filename = f"apt_trade_{lawd_cd}_{year_month}.csv"
        filepath = os.path.join(output_dir, filename)
        
        # CSV 파일로 저장
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return True

if __name__ == "__main__":
    # 테스트 실행
    collector = AptTradeCollector()
    
    # 테스트 1: 강남구 데이터 조회
    print("\n=== 강남구 데이터 조회 테스트 ===")
    params = {
        'serviceKey': collector.api_key,
        'LAWD_CD': '11680',  # 강남구
        'DEAL_YMD': '202501'
    }
    items = collector._call_api(params)
    print(f"강남구 거래 건수: {len(items) if items else 0}건")
    if items:
        print("\n첫 번째 거래 정보:")
        for k, v in items[0].items():
            print(f"{k}: {v}")
    
    # 테스트 2: 전국 거래량 요약
    collector.get_monthly_volume_summary("202501")
    
    # 2025년 1월 데이터 조회
    year_month = '202501'
    print(f"Collecting data for {year_month}...")
    
    # 전국 거래량 요약
    df_national = collector.get_monthly_volume_summary(year_month)
    print("\n전국 거래량 요약:")
    print(df_national) 