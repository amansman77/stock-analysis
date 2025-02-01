# 주식 자동 분석 시스템

현재 구현된 주식 자동 분석 시스템은 다음과 같은 기능을 제공합니다:

## 1. 데이터 수집 및 저장
- KRX(한국거래소)에서 주식 종목 정보 수집
- 일별 주가 데이터 자동 수집 및 저장
- 주간 데이터 자동 생성 및 저장

## 2. MACD 기술적 분석
- 일별/주간 MACD(이동평균수렴확산) 지표 계산
- MACD Line, Signal Line, MACD Histogram 산출
- 매수/매도 시그널 자동 감지
  - 매수 시그널: MACD 히스토그램이 음수에서 양수로 전환
  - 매도 시그널: MACD 히스토그램이 양수에서 음수로 전환

## 3. 자동 알림 시스템
- Discord를 통한 실시간 알림
- 주간 분석 결과 자동 전송
- 매수/매도 시그널 발생 시 즉시 알림
- 시스템 오류 발생 시 알림
- 전체 분석 결과 요약 제공

## 4. 자동화 구성
- 환경 변수를 통한 설정 관리 (.env 파일)
  - Discord Webhook URL
  - 분석할 종목명 (쉼표로 구분하여 여러 종목 설정 가능)
  - 데이터 수집 기간
- GitHub Actions를 통한 주간 자동 실행 (매주 토요일 오전 9시)
- 분석 결과 및 데이터 자동 저장

## 설치 및 실행

1. 필요 패키지 설치:
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정:
- `.env` 파일에 다음 내용 설정
```
DISCORD_WEBHOOK_URL=your_webhook_url_here
STOCK_NAME=종목1,종목2,종목3
DATA_DAYS=200
```

3. 실행:
```bash
python main.py
```

## GitHub Actions 설정

이 프로젝트는 GitHub Actions를 통해 자동으로 실행됩니다:
- 매주 토요일 오전 9시(KST)에 자동 실행
- 수동 실행도 가능 (GitHub Actions 탭에서 "Run workflow" 버튼 사용)
- 분석 결과는 Discord로 자동 전송
- 데이터는 저장소에 자동으로 커밋됨

## 향후 계획

- 다양한 투자 자산(코인, 외환 등) 분석 추가
- 추가 기술적 지표 도입
- 투자 성과 분석 및 리포트 기능
- 커뮤니티 기능 추가

## 욕망

- 매주 토요일마다 매수나 매도의 때가 된 종목을 알려줘서 내가 번거롭지 않게 해주면 좋겠다.
- 다른 사람에게 공개하여 추가적인 수익을 내면 좋겠다.
- 주식 종목 뿐만 아니라 코인이나 외환 등 다양한 투자 종목을 알려줘서 내가 번거롭지 않게 해주면 좋겠다.
