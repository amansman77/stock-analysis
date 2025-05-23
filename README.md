# 주식 MACD 분석 및 알림 봇

KRX(한국거래소)에서 제공하는 주식 데이터를 기반으로 MACD 기술적 분석을 수행하고 Discord를 통해 매매 시그널을 알려주는 프로그램입니다.

## 디스코드 채널

실제 알림 동작을 확인하고 싶으시다면 아래 디스코드 채널에 참여해보세요:
[주식 매매 알리미 채널](https://discord.gg/DzQhfQ868W)

### 알림 예시

채널에서 확인할 수 있는 정보:
- 매매 시그널 발생 시 상세 분석 정보
- 일일 분석 결과 요약
- 실시간 오류 알림

## 주요 기능

- KRX에서 실시간 주식/ETF 종목 정보 조회
- 일별/주간 주가 데이터 수집 및 분석
- MACD(Moving Average Convergence Divergence) 기술적 분석
- Discord 웹훅을 통한 매매 시그널 알림 (시그널 발생 종목만 상세 정보 전송)
- 캐시 기능으로 API 호출 최적화
- GitHub Actions를 통한 자동 실행 지원

## 설치 방법

1. Python 3.10 이상 설치
2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

## 환경 설정

`.env` 파일을 생성하고 다음 설정을 추가하세요:

```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url
STOCK_NAME=종목1,종목2,종목3  # 콤마로 구분된 종목명 목록
DATA_DAYS=200  # 분석할 과거 데이터 일수
```

## 사용 방법

### 로컬 실행
```bash
python main.py
```

### GitHub Actions
- 매주 토요일 오전 9시(KST)에 자동 실행
- GitHub 저장소의 Actions 탭에서 수동 실행 가능

## 출력 정보

1. 종목별 주간 MACD 분석 결과
   - 최근 4주 주가 데이터 요약
   - MACD 매매 시그널
   - 거래량 정보

2. Discord 알림
   - 매매 시그널이 발생한 종목에 대해서만 상세 분석 내용 전송
   - 전체 분석 결과 요약 (분석 완료 종목 수, 실패 종목, 시그널 발생 종목)
   - 분석 시간 정보
   - 오류 발생 시 알림

## 데이터 캐시

- `stock_data/krx_code.csv`: 종목 코드 정보 캐시 (일 1회 갱신)
- `stock_data/{종목코드}_daily.csv`: 일별 데이터 캐시
- `stock_data/{종목코드}_weekly.csv`: 주간 데이터 캐시

## 주의사항

- 주말 및 공휴일은 거래일에서 제외됩니다.
- KRX API 호출 제한이 있을 수 있으니 적절한 간격을 두고 사용하세요.
- Discord 웹훅 URL이 설정되지 않으면 콘솔에만 결과가 출력됩니다.
- GitHub Actions 실행 시 자동으로 분석 결과가 저장소에 커밋됩니다.

## 기술 스택

- Python 3.10
- pandas: 데이터 처리 및 분석
- requests & BeautifulSoup4: 웹 크롤링
- python-dotenv: 환경 변수 관리
- GitHub Actions: CI/CD 및 자동화

## 시도된 기능

### 아파트 실거래가 데이터 수집 (보류)

국토교통부 아파트 매매 실거래가 상세 자료 API를 활용한 전국 아파트 거래량 수집을 시도했으나, 다음과 같은 이유로 적용이 보류되었습니다:

1. **비효율적인 데이터 수집 구조**
   - 시군구별로 개별 API 호출이 필요 (전국 약 250개 시군구)
   - 매일 모든 지역의 데이터를 수집하는 것은 API 호출 측면에서 비효율적
   - 실시간성이 필요하지 않은 데이터임에도 과도한 API 호출이 발생

2. **데이터 저장 및 관리의 어려움**
   - 파일 기반 캐시는 대용량 데이터 관리에 적합하지 않음
   - 시계열 데이터의 효율적인 저장과 분석을 위해서는 DB 구조 필요

향후 개선 방향:
- 월별 통계 데이터 중심의 수집 방식으로 전환
- SQLite 등 경량 DB 도입 검토
- API 호출 최적화 (차등 수집 주기 적용)

관련 코드는 `feature/apt-trade` 브랜치에서 관리됩니다. 현재는 main 기능에 통합하지 않았지만, 추후 개선사항이 반영된 버전을 구현할 때 참고할 수 있습니다.
