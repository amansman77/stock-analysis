import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from pathlib import Path

# 현재 스크립트의 디렉토리에서 .env 파일 찾기
env_path = Path(__file__).resolve().parent / '.env'
print(f"Looking for .env file at: {env_path}")

if not env_path.exists():
    print(f"Warning: .env file not found at {env_path}")
else:
    print(f".env file found and exists")
    
# .env 파일 로드
load_dotenv(dotenv_path=env_path)

# 환경변수 가져오기 전에 현재 환경변수 상태 출력
print("\nCurrent environment variables:")
for key in ['DISCORD_WEBHOOK_URL', 'STOCK_NAME', 'DATA_DAYS']:
    print(f"{key} raw value: '{os.getenv(key)}'")

# 환경변수 가져오기
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
STOCK_NAMES = [name.strip() for name in os.getenv('STOCK_NAME', '티웨이홀딩스').split(',')]
DATA_DAYS = int(os.getenv('DATA_DAYS', '200').strip())  # 기본값 설정

def get_krx_code(market=None, force_update=False):
    """
    주식 종목 코드 조회 (ETF 포함)
    force_update: True일 경우 캐시된 파일을 무시하고 새로 데이터를 가져옴
    """
    # 캐시 파일 경로
    cache_dir = 'stock_data'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file = os.path.join(cache_dir, 'krx_code.csv')
    
    # 오늘 날짜
    today = datetime.now().date()
    
    # 캐시된 파일이 있고 오늘 생성된 것이면 그것을 사용
    if not force_update and os.path.exists(cache_file):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file)).date()
        if file_mtime == today:
            print(f"캐시된 종목 코드 데이터 사용 (생성일: {file_mtime})")
            return pd.read_csv(cache_file)
    
    print("KRX에서 종목 코드 데이터 새로 가져오기...")
    
    # 일반 주식 데이터 가져오기
    stock_code = None
    try:
        url = 'http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd'
        stock_params = {
            'bld': 'dbms/MDC/STAT/standard/MDCSTAT01901',
            'mktId': 'ALL',
            'share': '1',
            'csvxls_isNo': 'false',
        }
        headers = {
            'Referer': 'http://data.krx.co.kr/contents/MDC/MDI/mdiLoader',
            'User-Agent': 'Mozilla/5.0',
            'X-Requested-With': 'XMLHttpRequest'
        }
        response = requests.post(url, data=stock_params, headers=headers)
        stock_data = response.json()
        if 'OutBlock_1' in stock_data:
            stock_code = pd.DataFrame(stock_data['OutBlock_1'])
            stock_code = stock_code.rename(columns={'ISU_SRT_CD': 'code', 'ISU_ABBRV': 'name'})
            print(f"일반 주식 데이터 조회 성공: {len(stock_code)}개")
    except Exception as e:
        print(f"일반 주식 데이터 조회 실패: {str(e)}")
    
    # ETF 데이터 가져오기
    etf_code = None
    try:
        etf_params = {
            'bld': 'dbms/MDC/STAT/standard/MDCSTAT04301',
            'mktId': 'ETF',
            'share': '1',
            'csvxls_isNo': 'false',
        }
        response = requests.post(url, data=etf_params, headers=headers)
        etf_data = response.json()
        if 'OutBlock_1' in etf_data:
            etf_code = pd.DataFrame(etf_data['OutBlock_1'])
            etf_code = etf_code.rename(columns={'ISU_SRT_CD': 'code', 'ISU_ABBRV': 'name'})
            print(f"ETF 데이터 조회 성공: {len(etf_code)}개")
    except Exception as e:
        print(f"ETF 데이터 조회 실패: {str(e)}")
    
    # 데이터 합치기
    if stock_code is not None and etf_code is not None:
        code_df = pd.concat([stock_code[['name', 'code']], etf_code[['name', 'code']]], ignore_index=True)
    elif stock_code is not None:
        code_df = stock_code[['name', 'code']]
    elif etf_code is not None:
        code_df = etf_code[['name', 'code']]
    else:
        raise Exception("주식 및 ETF 데이터를 모두 가져오는데 실패했습니다.")
    
    # 종목코드 형식 통일
    code_df['code'] = code_df['code'].astype(str).str.zfill(6)
    
    # 중복 제거
    code_df = code_df.drop_duplicates(subset=['code'], keep='first')
    
    # 캐시 파일로 저장
    code_df.to_csv(cache_file, index=False)
    print(f"전체 {len(code_df)}개 종목 데이터 저장 완료: {cache_file}")
    
    return code_df

def is_trading_day(date):
    """
    주어진 날짜가 거래일인지 확인
    - 주말(토,일) 제외
    - 공휴일은 별도 체크 필요
    """
    # 주말 체크
    if date.weekday() >= 5:  # 5=토요일, 6=일요일
        return False
    return True

def calculate_macd_daily(df):
    """
    일간 MACD 지표 계산 (12, 26, 9)
    
    1. MACD Line = 12일 EMA - 26일 EMA
    2. Signal Line = MACD Line의 9일 EMA
    3. MACD Histogram = MACD Line - Signal Line
    """
    # 종가 데이터
    close = df['close']
    
    # EMA 계산을 위한 알파값 계산 - 기본값 사용
    alpha12 = 2 / (12 + 1)
    alpha26 = 2 / (26 + 1)
    alpha9 = 2 / (9 + 1)
    
    # 1. EMA 계산
    # 1-1. 12일 EMA (단기) 계산 - 초기값을 SMA로 설정
    sma12 = close.rolling(window=12, min_periods=1).mean()
    ema12 = pd.Series(index=close.index, dtype='float64')
    ema12.iloc[0] = sma12.iloc[0]
    
    for i in range(1, len(close)):
        ema12.iloc[i] = close.iloc[i] * alpha12 + ema12.iloc[i-1] * (1 - alpha12)
    
    df['ema12'] = ema12.round(4)
    
    # 1-2. 26일 EMA (장기) 계산 - 초기값을 SMA로 설정
    sma26 = close.rolling(window=26, min_periods=1).mean()
    ema26 = pd.Series(index=close.index, dtype='float64')
    ema26.iloc[0] = sma26.iloc[0]
    
    for i in range(1, len(close)):
        ema26.iloc[i] = close.iloc[i] * alpha26 + ema26.iloc[i-1] * (1 - alpha26)
    
    df['ema26'] = ema26.round(4)
    
    # 2. MACD Line 계산
    macd_line = (ema12 - ema26)
    df['macd_line'] = macd_line.round(4)
    
    # 3. Signal Line 계산 - 초기값을 SMA로 설정
    sma9 = macd_line.rolling(window=9, min_periods=1).mean()
    signal_line = pd.Series(index=macd_line.index, dtype='float64')
    signal_line.iloc[0] = sma9.iloc[0]
    
    for i in range(1, len(macd_line)):
        signal_line.iloc[i] = macd_line.iloc[i] * alpha9 + signal_line.iloc[i-1] * (1 - alpha9)
    
    df['signal_line'] = signal_line.round(4)
    
    # 4. MACD Histogram 계산 (편향 보정 없음)
    df['macd_hist'] = (df['macd_line'] - df['signal_line']).round(2)
    
    return df

def calculate_macd_weekly(df):
    """
    주간 MACD 지표 계산 (12, 26, 9)
    
    1. MACD Line = 12일 EMA - 26일 EMA
    2. Signal Line = MACD Line의 9일 EMA
    3. MACD Histogram = MACD Line - Signal Line
    """
    # 종가 데이터
    close = df['close']
    
    # EMA 계산을 위한 알파값 계산 - 주간 데이터용 조정값 사용
    alpha12 = 2 / (12 + 1.15)
    alpha26 = 2 / (26 + 1.15)
    alpha9 = 2 / (9 + 1.15)
    
    # 1. EMA 계산
    # 1-1. 12일 EMA (단기) 계산 - 초기값을 SMA로 설정
    sma12 = close.rolling(window=12, min_periods=1).mean()
    ema12 = pd.Series(index=close.index, dtype='float64')
    ema12.iloc[0] = sma12.iloc[0]
    
    for i in range(1, len(close)):
        ema12.iloc[i] = close.iloc[i] * alpha12 + ema12.iloc[i-1] * (1 - alpha12)
    
    df['ema12'] = ema12.round(4)
    
    # 1-2. 26일 EMA (장기) 계산 - 초기값을 SMA로 설정
    sma26 = close.rolling(window=26, min_periods=1).mean()
    ema26 = pd.Series(index=close.index, dtype='float64')
    ema26.iloc[0] = sma26.iloc[0]
    
    for i in range(1, len(close)):
        ema26.iloc[i] = close.iloc[i] * alpha26 + ema26.iloc[i-1] * (1 - alpha26)
    
    df['ema26'] = ema26.round(4)
    
    # 2. MACD Line 계산
    macd_line = (ema12 - ema26)
    df['macd_line'] = macd_line.round(4)
    
    # 3. Signal Line 계산 - 초기값을 SMA로 설정
    sma9 = macd_line.rolling(window=9, min_periods=1).mean()
    signal_line = pd.Series(index=macd_line.index, dtype='float64')
    signal_line.iloc[0] = sma9.iloc[0]
    
    for i in range(1, len(macd_line)):
        signal_line.iloc[i] = macd_line.iloc[i] * alpha9 + signal_line.iloc[i-1] * (1 - alpha9)
    
    df['signal_line'] = signal_line.round(4)
    
    # 4. MACD Histogram 계산 - 편향 보정 적용
    macd_hist = (df['macd_line'] - df['signal_line'])
    bias_correction = -1.0
    df['macd_hist'] = (macd_hist + bias_correction).round(2)
    
    return df

def get_stock_price(code, num_of_pages, sort_date = True):
    # 데이터를 저장할 디렉토리 생성
    data_dir = 'stock_data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # CSV 파일 경로
    file_path = os.path.join(data_dir, f'{code}_daily.csv')
    
    # 기존 데이터 로드
    existing_df = pd.DataFrame()
    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        existing_df['date'] = pd.to_datetime(existing_df['date'])
        
    # 최신 데이터 날짜 확인
    latest_date = existing_df['date'].max() if not existing_df.empty else pd.Timestamp.min
    
    # 오늘 날짜
    today = pd.Timestamp.now().normalize()
    
    # 새로운 데이터를 저장할 데이터프레임
    df = pd.DataFrame()
    
    # 데이터 업데이트가 필요한 경우: 파일이 없거나, 최신 데이터가 오래된 경우
    if not os.path.exists(file_path) or (latest_date < today and is_trading_day(today)):
        print(f"데이터 업데이트 중: {code}")
        
        url = f"http://finance.naver.com/item/sise_day.nhn?code={code}"
        headers = {'User-agent': 'Mozilla/5.0'} 
        response = requests.get(url=url, headers=headers)
        response.encoding = 'euc-kr'  # 네이버 금융은 EUC-KR 인코딩 사용
        bs = BeautifulSoup(response.text, 'html.parser')
        pgrr = bs.find("td", class_="pgRR")
        last_page = int(pgrr.a["href"].split('=')[-1])
        
        pages = min(last_page, num_of_pages)
        new_df = pd.DataFrame()

        for page in range(1, pages+1):
            page_url = '{}&page={}'.format(url, page)
            response = requests.get(page_url, headers={'User-agent': 'Mozilla/5.0'})
            response.encoding = 'euc-kr'
            new_df = pd.concat([new_df, pd.read_html(response.text, encoding='euc-kr')[0]], ignore_index=True)
        
        new_df = new_df.rename(columns={'날짜':'date','종가':'close','전일비':'diff'
                    ,'시가':'open','고가':'high','저가':'low','거래량':'volume'})
        new_df['date'] = pd.to_datetime(new_df['date'])
        new_df = new_df.dropna()
        
        # 숫자 데이터 처리
        numeric_columns = ['close', 'open', 'high', 'low', 'volume']
        for col in numeric_columns:
            if new_df[col].dtype == object:
                new_df[col] = new_df[col].str.replace(',', '').astype(int)
            else:
                new_df[col] = new_df[col].astype(int)
        
        if new_df['diff'].dtype == object:
            new_df['diff'] = new_df['diff'].str.extract('([\d,]+)').fillna('0')
            new_df['diff'] = new_df['diff'].str.replace(',', '').astype(int)
        else:
            new_df['diff'] = new_df['diff'].astype(int)
        
        new_df = new_df[['date', 'open', 'high', 'low', 'close', 'diff', 'volume']]
        
        # 기존 데이터와 새로운 데이터 병합
        if existing_df.empty:
            df = new_df
        else:
            # 중복 제거하면서 데이터 병합
            df = pd.concat([existing_df, new_df])
            df = df.drop_duplicates(subset=['date'], keep='last')
        
        # 날짜 기준으로 정렬
        if sort_date:
            df = df.sort_values(by='date').reset_index(drop=True)
            
        # MACD 계산
        df = calculate_macd_daily(df)
        
        # 데이터 저장
        save_columns = ['date', 'open', 'high', 'low', 'close', 'diff', 'volume', 
                       'ema12', 'ema26', 'macd_line', 'signal_line', 'macd_hist']
        df[save_columns].to_csv(file_path, index=False)
    else:
        df = existing_df
    
    # 최근 30주 데이터 필터링
    thirty_weeks_ago = datetime.now() - timedelta(weeks=30)
    df = df[df['date'] >= thirty_weeks_ago]
    
    return df

def get_weekly_data(df, code):
    """
    일간 데이터를 주간 데이터로 변환 (금요일 기준)
    """
    # 데이터를 저장할 디렉토리 생성
    data_dir = 'stock_data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 주간 데이터 파일 경로
    file_path = os.path.join(data_dir, f'{code}_weekly.csv')
    
    # 기존 주간 데이터 로드
    existing_weekly_df = pd.DataFrame()
    if os.path.exists(file_path):
        existing_weekly_df = pd.read_csv(file_path)
        existing_weekly_df['date'] = pd.to_datetime(existing_weekly_df['date'])
    
    print(f"입력 데이터 수: {len(df)}")
    
    # 날짜를 기준으로 정렬
    df = df.sort_values('date', ascending=True)
    
    # 주차 계산 방식 변경 (%Y-%U -> %Y-%W: 월요일 시작 기준)
    df['year_week'] = df['date'].dt.strftime('%Y-%W')
    
    # 주간 데이터 계산
    weekly_data = []
    for year_week, group in df.groupby('year_week'):
        if len(group) > 0:
            data = {
                'date': group['date'].iloc[-1],    # 주의 마지막 거래일
                'open': group['open'].iloc[0],     # 주의 첫 거래일 시가
                'high': group['high'].max(),       # 주의 고가
                'low': group['low'].min(),         # 주의 저가
                'close': group['close'].iloc[-1],  # 주의 마지막 거래일 종가
                'volume': group['volume'].sum()    # 주간 거래량 합계
            }
            weekly_data.append(data)
    
    new_weekly_df = pd.DataFrame(weekly_data)
    
    # 기존 데이터와 새로운 데이터 병합
    if existing_weekly_df.empty:
        weekly_df = new_weekly_df
    else:
        # 중복 제거하면서 데이터 병합
        weekly_df = pd.concat([existing_weekly_df, new_weekly_df])
        weekly_df = weekly_df.drop_duplicates(subset=['date'], keep='last')
    
    # 날짜 기준으로 정렬
    weekly_df = weekly_df.sort_values(by='date').reset_index(drop=True)
    
    # 데이터 확인용 출력
    print(f"주간 데이터 수: {len(weekly_df)}")
    
    # 전주 대비 차이 계산
    weekly_df['diff'] = weekly_df['close'].diff().fillna(0).astype(int)
    
    # 주간 데이터로 MACD 계산
    weekly_df = calculate_macd_weekly(weekly_df)
    
    # 데이터 저장
    save_columns = ['date', 'open', 'high', 'low', 'close', 'diff', 'volume', 
                   'ema12', 'ema26', 'macd_line', 'signal_line', 'macd_hist']
    weekly_df[save_columns].to_csv(file_path, index=False)
        
    return weekly_df.tail(4)

def check_macd_signals(weekly_df):
    """
    주간 MACD 히스토그램의 부호 변화를 확인하여 매수/매도 시그널 생성
    """
    signals = []
    
    # 최소 2주 이상의 데이터가 필요
    if len(weekly_df) < 2:
        return signals
    
    # 최근 2주간의 데이터만 사용
    last_two_weeks = weekly_df.tail(2)
    prev_hist = last_two_weeks.iloc[0]['macd_hist']
    curr_hist = last_two_weeks.iloc[1]['macd_hist']
    curr_date = last_two_weeks.iloc[1]['date']
    curr_price = last_two_weeks.iloc[1]['close']
    
    # 음봉 -> 양봉 (매수 시그널)
    if prev_hist < 0 and curr_hist > 0:
        signals.append({
            'type': 'BUY',
            'date': curr_date,
            'price': curr_price,
            'reason': f'MACD 히스토그램 부호 전환 (음 → 양): {prev_hist:.2f} → {curr_hist:.2f}'
        })
    
    # 양봉 -> 음봉 (매도 시그널)
    elif prev_hist > 0 and curr_hist < 0:
        signals.append({
            'type': 'SELL',
            'date': curr_date,
            'price': curr_price,
            'reason': f'MACD 히스토그램 부호 전환 (양 → 음): {prev_hist:.2f} → {curr_hist:.2f}'
        })
    
    return signals

# Discord 알림 기능 추가
def send_to_discord(message, webhook_url):
    """Discord로 메시지 전송"""
    data = {
        "content": message,
        "username": "주식 알리미",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2474/2474475.png"
    }
    
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Discord 메시지 전송 실패: {str(e)}")
        return False

def format_discord_message(item_name, stock, signals, weekly_df):
    """Discord 메시지 포맷팅"""
    message = f"🔔 **{item_name}({stock}) 주간 MACD 분석 결과**\n\n"
    
    # 최근 4주 데이터 요약
    message += "📊 **최근 4주 요약**\n```\n"
    message += "날짜          종가      전주비    MACD\n"
    message += "-" * 40 + "\n"
    
    for _, row in weekly_df.iterrows():
        message += f"{row['date'].strftime('%Y-%m-%d')}  "
        message += f"{row['close']:8,}  "
        message += f"{row['diff']:+8,}  "
        message += f"{row['macd_hist']:+6.2f}\n"
    message += "```\n"
    
    # 매매 시그널
    if signals:
        for signal in signals:
            if signal['type'] == 'BUY':
                message += "\n🔵 **매수 시그널 발생!**\n"
            else:
                message += "\n🔴 **매도 시그널 발생!**\n"
            
            message += f"📅 날짜: {signal['date'].strftime('%Y-%m-%d')}\n"
            message += f"💰 가격: {signal['price']:,}원\n"
            message += f"📊 {signal['reason']}\n"
    else:
        message += "\n💡 현재 매매 시그널 없음\n"
    
    return message

def analyze_stocks():
    """여러 주식 분석 및 Discord 알림 전송"""
    all_results = []
    error_stocks = []
    
    for item_name in STOCK_NAMES:
        try:
            print(f"\n=== {item_name} 분석 시작 ===")
            stock = get_krx_code().query("name==@item_name")['code'].iloc[0]
            df = get_stock_price(stock, DATA_DAYS)
            weekly_df = get_weekly_data(df, stock)
            
            if weekly_df is not None:
                signals = check_macd_signals(weekly_df)
                
                # 콘솔 출력
                print(f"\n=== {item_name}({stock}) 주간 MACD 분석 결과 ===")
                print("\n주간          종가      전주비    거래량     MACD히스토그램")
                print("-" * 65)

                for _, row in weekly_df.iterrows():
                    print(f"{row['date'].strftime('%Y-%m-%d')}  "
                          f"{row['close']:8,}  "
                          f"{row['diff']:+8,}  "
                          f"{row['volume']:10,}  "
                          f"{row['macd_hist']:+8.2f}")
                
                # Discord 알림 전송
                if DISCORD_WEBHOOK_URL:
                    message = format_discord_message(item_name, stock, signals, weekly_df)
                    send_to_discord(message, DISCORD_WEBHOOK_URL)
                
                all_results.append({
                    'name': item_name,
                    'code': stock,
                    'signals': signals is not None and len(signals) > 0
                })
                
        except Exception as e:
            error_message = f"{item_name} 분석 중 오류 발생: {str(e)}"
            print(error_message)
            error_stocks.append(item_name)
            if DISCORD_WEBHOOK_URL:
                send_to_discord(f"⚠️ **오류 발생**\n{error_message}", DISCORD_WEBHOOK_URL)
    
    # 전체 분석 결과 요약
    if DISCORD_WEBHOOK_URL and all_results:
        summary = "📊 **전체 분석 결과 요약**\n\n"
        summary += f"✅ 분석 완료: {len(all_results)}개 종목\n"
        if error_stocks:
            summary += f"❌ 분석 실패: {len(error_stocks)}개 종목 ({', '.join(error_stocks)})\n"
        
        signals_found = [result['name'] for result in all_results if result['signals']]
        if signals_found:
            summary += f"\n🔔 매매 시그널 발생 종목: {', '.join(signals_found)}"
        else:
            summary += "\n💡 매매 시그널이 발생한 종목이 없습니다."
        
        send_to_discord(summary, DISCORD_WEBHOOK_URL)
    
    return {
        'success': True,
        'analyzed': len(all_results),
        'errors': len(error_stocks)
    }

# CLI 실행용 메인 함수
def main():
    if DISCORD_WEBHOOK_URL:
        print("Discord 알림 기능이 활성화되었습니다.")
    else:
        print("Warning: DISCORD_WEBHOOK_URL이 설정되지 않아 Discord 알림이 비활성화됩니다.")
    
    print(f"분석할 종목: {', '.join(STOCK_NAMES)}")
    
    # 분석 실행
    analyze_stocks()

if __name__ == "__main__":
    main()