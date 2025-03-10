# Bitcoin Portfolio Rebalancing Bot

자동으로 비트코인과 현금 간의 포트폴리오를 리밸런싱하는 Python 봇입니다. 이 봇은 Bithumb API를 사용하여 설정된 비율에 따라 비트코인과 현금 간의 균형을 자동으로 유지합니다.

## 주요 기능

- 포트폴리오의 비트코인 비중이 설정된 임계값을 벗어날 경우 자동 리밸런싱
- 정기적인 포트폴리오 상태 확인 및 리밸런싱
- 성과 기록 및 시각화
- 로그 기록
- Bithumb API를 통한 실시간 가격 조회 및 주문 실행

## 설치 방법

1. 필요한 패키지 설치:

```bash
pip install pandas numpy matplotlib python-dotenv pyjwt schedule requests
```

2. `.env` 파일 생성 후 다음 내용 추가:

```
BITHUMB_ACCESS_KEY=귀하의_빗썸_API_키
BITHUMB_SECRET_KEY=귀하의_빗썸_시크릿_키
```

## 설정

코드의 상단에서 다음 매개변수를 수정하여 봇을 설정할 수 있습니다:

```python
# 리밸런싱 설정
TARGET_RATIO = 0.5      # 비트코인 50%, 현금 50%
LOWER_THRESHOLD = 0.4   # 하한 임계값
UPPER_THRESHOLD = 0.6   # 상한 임계값
TICKER = "BTC"          # 거래할 암호화폐 티커
FEE_RATE = 0.0025       # 0.25% 거래 수수료 (Bithumb 기준)
CHECK_INTERVAL = 6      # 포트폴리오 상태 확인 간격 (시간)
LOG_FILE = "rebalancing_log.txt"
```

## 사용 방법

다음 명령으로 봇을 실행합니다:

```bash
python rebalancing_bot.py
```

봇은 다음과 같은 작업을 수행합니다:

1. 시작 시 설정된 목표 비율과 임계값을 표시
2. 현재 포트폴리오 상태를 확인하고 필요한 경우 리밸런싱
3. 정기적인 간격으로 포트폴리오 상태 확인 및 리밸런싱 실행
4. 매일 오전 9시에 성과 기록 및 시각화

## 주요 함수

| 함수                    | 설명                                        |
| ----------------------- | ------------------------------------------- |
| `bithumb_api_call()`    | Bithumb API를 호출하는 함수 (JWT 인증 방식) |
| `get_balance()`         | 계정의 자산 정보를 조회하는 함수            |
| `get_ticker()`          | 현재 BTC 시세를 조회하는 함수               |
| `place_buy_order()`     | 비트코인 매수 주문을 실행하는 함수          |
| `place_sell_order()`    | 비트코인 매도 주문을 실행하는 함수          |
| `rebalance_portfolio()` | 포트폴리오 리밸런싱을 실행하는 함수         |
| `log_action()`          | 작업 로그를 기록하는 함수                   |
| `record_performance()`  | 포트폴리오 성과를 기록하고 시각화하는 함수  |
| `main()`                | 메인 실행 함수 - 스케줄러 설정              |

## 출력 파일

- `rebalancing_log.txt`: 봇의 작업 로그
- `performance_history.csv`: 포트폴리오 성과 데이터
- `performance_chart.png`: 성과 시각화 차트

## 성과 시각화

`record_performance()` 함수는 다음과 같은 차트를 생성합니다:

1. BTC 가격 추이
2. 포트폴리오 총 가치 추이
3. BTC 비중 추이 (목표 비중과 임계값 포함)
4. 자산 구성 추이 (BTC 평가금액 및 KRW 잔고)

## 주의사항

- 이 봇은 실제 자금을 사용하여 거래합니다. 신중하게 테스트하고 사용하세요.
- 암호화폐 시장은 변동성이 크므로 투자 위험을 인지하고 사용하세요.
- API 키와 시크릿은 안전하게 보관하고 노출되지 않도록 주의하세요.
- 작은 금액으로 먼저 테스트한 후 실제 운영에 사용하는 것을 권장합니다.

## API 호출 문제 해결

JWT 인증 관련 오류가 발생할 경우 `bithumb_api_call()` 함수에서 다음 사항을 확인하세요:

1. `query_hash` 생성이 올바르게 되었는지 확인
2. 타임스탬프가 밀리초 단위로 올바르게 생성되었는지 확인
3. `Content-Type` 헤더가 올바르게 설정되었는지 확인
4. POST 요청 시 데이터가 올바른 형식으로 전송되었는지 확인

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

## 기여

이슈 또는 풀 리퀘스트를 통해 프로젝트에 기여할 수 있습니다.
