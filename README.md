# 주식 MACD 분석 및 알림 봇

KRX(한국거래소)에서 제공하는 주식 데이터를 기반으로 MACD 기술적 분석을 수행하고 Discord를 통해 매매 시그널을 알려주는 프로그램입니다.

## 주요 기능

- KRX에서 실시간 주식/ETF 종목 정보 조회
- 일별/주간 주가 데이터 수집 및 분석
- MACD(Moving Average Convergence Divergence) 기술적 분석
- Discord 웹훅을 통한 매매 시그널 알림
- 캐시 기능으로 API 호출 최적화

## 설치 방법

1. Python 3.6 이상 설치
2. 필요한 패키지 설치:
```bash
pip install pandas numpy requests beautifulsoup4 python-dotenv
```

## 환경 설정

`.env` 파일을 생성하고 다음 설정을 추가하세요:

```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url
STOCK_NAME=종목1,종목2,종목3  # 콤마로 구분된 종목명 목록
DATA_DAYS=200  # 분석할 과거 데이터 일수
```

## 사용 방법

```bash
python main.py
```

## 출력 정보

1. 종목별 주간 MACD 분석 결과
   - 최근 4주 주가 데이터 요약
   - MACD 매매 시그널
   - 거래량 정보

2. Discord 알림
   - 매수/매도 시그널 발생 시 알림
   - 전체 분석 결과 요약
   - 오류 발생 시 알림

## 캐시 기능

- `stock_data/krx_code.csv`: 종목 코드 정보 캐시 (일 1회 갱신)
- `stock_data/{종목코드}_daily.csv`: 일별 데이터 캐시
- `stock_data/{종목코드}_weekly.csv`: 주간 데이터 캐시

## 주의사항

- 주말 및 공휴일은 거래일에서 제외됩니다.
- KRX API 호출 제한이 있을 수 있으니 적절한 간격을 두고 사용하세요.
- Discord 웹훅 URL이 설정되지 않으면 콘솔에만 결과가 출력됩니다.
