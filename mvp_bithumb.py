import os
from dotenv import load_dotenv
import hashlib
import pandas as pd
import numpy as np
import time
import jwt
import uuid
import requests
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import schedule

# Bithumb API 설정
load_dotenv()

API_URL = "https://api.bithumb.com"
ACCESS_KEY = os.getenv("BITHUMB_ACCESS_KEY") # 실제 API 키로 변경 필요
SECRET_KEY = os.getenv("BITHUMB_SECRET_KEY") # 실제 시크릿 키로 변경 필요

# 리밸런싱 설정
TARGET_RATIO = 0.5  # 비트코인 50%, 현금 50%
LOWER_THRESHOLD = 0.4  # 하한 임계값
UPPER_THRESHOLD = 0.6  # 상한 임계값
TICKER = "BTC"  # 거래할 암호화폐 티커
FEE_RATE = 0.0025  # 0.25% 거래 수수료 (Bithumb 기준)
CHECK_INTERVAL = 6  # 포트폴리오 상태 확인 간격 (시간)
LOG_FILE = "rebalancing_log.txt"

# Bithumb API 호출 함수
def bithumb_api_call(endpoint, params=None, method="GET"):
    """
    Bithumb API를 호출하는 함수 (JWT 인증 방식)
    
    Args:
        endpoint (str): API 엔드포인트
        params (dict, optional): API 요청 파라미터
        method (str, optional): HTTP 메소드 (GET/POST)
    
    Returns:
        dict: API 응답 데이터
    """
    if params is None:
        params = {}
    
    # 공개 API 호출 (인증 불필요)
    if method == "GET" and endpoint.startswith("/public"):
        url = f"{API_URL}{endpoint}"
        response = requests.get(url, params=params)
        return response.json()
    
    # 개인 API 호출 (JWT 인증 필요)
    else:
        url = f"{API_URL}{endpoint}"
        
        # 현재 시간을 밀리초 단위로 구함
        timestamp = str(int(time.time() * 1000))
        
        # query_string 생성 (API 요청 파라미터를 쿼리 스트링으로 변환)
        query_string = ""
        if params:
            # params를 쿼리 스트링 형식으로 변환
            query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        
        # JWT 페이로드 생성
        payload = {
            'access_key': ACCESS_KEY,
            'nonce': str(uuid.uuid4()),
            'query_hash': None,
            'query_hash_alg': 'SHA512',
            'timestamp': timestamp
        }
        
        # query_hash 생성 (POST 요청 또는 파라미터가 있는 경우)
        if method == "POST" or query_string:
            m = hashlib.sha512()
            m.update(query_string.encode('utf-8'))
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
        
        # JWT 토큰 생성
        jwt_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        
        # Authorization 헤더 설정
        if isinstance(jwt_token, bytes):  # Python 3.6 이하 버전 대응
            jwt_token = jwt_token.decode('utf-8')
        
        authorization_token = f'Bearer {jwt_token}'
        headers = {
            'Authorization': authorization_token,
            'Content-Type': 'application/json'
        }
        
        # API 요청 전송
        try:
            if method == "POST":
                response = requests.post(url, data=json.dumps(params), headers=headers)
            else:  # GET with auth
                response = requests.get(url, headers=headers)
            
            return response.json()
        except Exception as e:
            print(f"API 호출 중 오류 발생: {e}")
            return {'error': str(e)}

# 계정 잔고 조회
def get_balance():
    """
    Bithumb 계정의 자산 정보를 조회하는 함수
    
    Returns:
        dict: 자산 정보 (KRW 잔고, BTC 보유량, BTC 평가금액)
    """
    endpoint = "/v1/accounts"
    
    response = bithumb_api_call(endpoint, method="GET")
 
    if isinstance(response, list):
        # 응답 형식이 리스트인 경우 (예시 응답과 같은 형태)
        krw_info = next((item for item in response if item.get('currency') == 'KRW'), None)
        btc_info = next((item for item in response if item.get('currency') == TICKER), None)
        
        if krw_info and btc_info:
            krw_balance = float(krw_info.get('balance', 0))
            btc_balance = float(btc_info.get('balance', 0))
            
            # BTC 현재가 조회
            ticker_info = get_ticker()
            #print("ticker_info:", ticker_info)
            btc_price = ticker_info #['trade_price']
            
            # BTC 평가금액 계산
            btc_value = btc_balance * btc_price
            
            return {
                'krw_balance': krw_balance,
                'btc_balance': btc_balance,
                'btc_price': btc_price,
                'btc_value': btc_value,
                'total_value': krw_balance + btc_value,
                'btc_ratio': btc_value / (krw_balance + btc_value) if (krw_balance + btc_value) > 0 else 0
            }
    
    print(f"잔고 조회 실패: {response}")
    return None

# 현재가 조회
def get_ticker():
    """
    현재 BTC 시세를 조회하는 함수
    
    Returns:
        dict: 현재가 정보
    """
    endpoint = f"/v1/ticker?markets=KRW-{TICKER}"
        
    try:
        response = bithumb_api_call(endpoint)
        price = response[0].get('trade_price', 0) if response else 0         
        print(price)
        return price
    
    except Exception as e:
            print("error ===>",e)
            return None

# 매수 주문
def place_buy_order(amount_krw):
    """
    비트코인 매수 주문을 실행하는 함수
    
    Args:
        amount_krw (float): 매수할 금액 (KRW)
    
    Returns:
        dict: 주문 결과
    """
    endpoint = "/v1/orders"
    
    # 주문 금액에서 수수료 차감 (실제 구매 가능 금액)
    actual_amount = amount_krw - (amount_krw * FEE_RATE)
    
    params = {
        'market': f"KRW-{TICKER}",
        'side': 'bid',  # 매수
        'ord_type': 'price',  # 시장가 주문 (금액 지정)
        'price': str(int(actual_amount))
    }
    
    response = bithumb_api_call(endpoint, params, "POST")
    
    # 응답 형식에 맞게 성공 여부 확인
    if response and 'uuid' in response:
        log_action(f"매수 주문 성공: {amount_krw:,.0f}원 (수수료 포함)")
        return {'success': True, 'order_id': response.get('uuid', '')}
    else:
        log_action(f"매수 주문 실패: {response}")
        return {'success': False, 'error': response}
    
# 매도 주문
def place_sell_order(amount_btc):
    """
    비트코인 매도 주문을 실행하는 함수
    
    Args:
        amount_btc (float): 매도할 비트코인 수량
    
    Returns:
        dict: 주문 결과
    """
    endpoint = "/v1/orders"
    
    params = {
        'market': f"KRW-{TICKER}",
        'side': 'ask',  # 매도
        'ord_type': 'market',  # 시장가 주문
        'volume': str(amount_btc)
    }
    
    response = bithumb_api_call(endpoint, params, "POST")
    
    if response.get('uuid'):
        ticker_info = get_ticker()
        estimated_value = amount_btc * ticker_info #['trade_price']
        log_action(f"매도 주문 성공: {amount_btc} BTC (약 {estimated_value:,.0f}원)")
        return {'success': True, 'order_id': response.get('uuid', '')}
    else:
        log_action(f"매도 주문 실패: {response}")
        return {'success': False, 'error': response}

# 리밸런싱 실행
def rebalance_portfolio():
    """
    포트폴리오 리밸런싱을 실행하는 함수
    임계값을 벗어났을 때만 리밸런싱 수행
    """
    log_action("포트폴리오 상태 확인 중...")
    
    # 현재 자산 상태 조회
    balance = get_balance()
    if balance is None:
        log_action("자산 조회 실패, 리밸런싱 중단")
        return
    
    krw_balance = balance['krw_balance']
    btc_balance = balance['btc_balance']
    btc_price = balance['btc_price']
    btc_value = balance['btc_value']
    total_value = balance['total_value']
    current_btc_ratio = balance['btc_ratio']
    
    log_action(f"현재 자산 상태:")
    log_action(f"KRW 잔고: {krw_balance:,.0f}원")
    log_action(f"BTC 보유량: {btc_balance} BTC (현재가: {btc_price:,.0f}원)")
    log_action(f"BTC 평가금액: {btc_value:,.0f}원")
    log_action(f"총 자산: {total_value:,.0f}원")
    log_action(f"현재 BTC 비중: {current_btc_ratio:.4f} ({current_btc_ratio*100:.2f}%)")
    
    # 임계값을 벗어났는지 확인
    if current_btc_ratio < LOWER_THRESHOLD:
        # 비트코인 비중이 너무 낮음 -> 추가 매수
        log_action(f"BTC 비중이 하한선({LOWER_THRESHOLD*100}%)보다 낮습니다. 리밸런싱 실행...")
        
        target_btc_value = total_value * TARGET_RATIO
        buy_amount_krw = target_btc_value - btc_value
        
        log_action(f"목표 BTC 평가금액: {target_btc_value:,.0f}원")
        log_action(f"매수 필요 금액: {buy_amount_krw:,.0f}원")
        
        if buy_amount_krw > 1000:  # 최소 주문 금액 (1,000원)
            # 매수 주문 실행
            order_result = place_buy_order(buy_amount_krw)
            if order_result['success']:
                log_action(f"리밸런싱 완료 (매수)")
            else:
                log_action(f"리밸런싱 실패 (매수 주문 오류)")
        else:
            log_action(f"매수 금액이 최소 주문 금액보다 작아 리밸런싱 건너뜀")
    
    elif current_btc_ratio > UPPER_THRESHOLD:
        # 비트코인 비중이 너무 높음 -> 일부 매도
        log_action(f"BTC 비중이 상한선({UPPER_THRESHOLD*100}%)보다 높습니다. 리밸런싱 실행...")
        
        target_btc_value = total_value * TARGET_RATIO
        sell_amount_krw = btc_value - target_btc_value
        sell_amount_btc = sell_amount_krw / btc_price
        
        log_action(f"목표 BTC 평가금액: {target_btc_value:,.0f}원")
        log_action(f"매도 필요 금액: {sell_amount_krw:,.0f}원")
        log_action(f"매도 필요 수량: {sell_amount_btc} BTC")
        
        if sell_amount_btc * btc_price > 1000:  # 최소 주문 금액 (1,000원)
            # 매도 주문 실행
            order_result = place_sell_order(sell_amount_btc)
            if order_result['success']:
                log_action(f"리밸런싱 완료 (매도)")
            else:
                log_action(f"리밸런싱 실패 (매도 주문 오류)")
        else:
            log_action(f"매도 금액이 최소 주문 금액보다 작아 리밸런싱 건너뜀")
    
    else:
        log_action(f"현재 BTC 비중이 허용 범위 내에 있습니다. 리밸런싱 불필요.")
    
    log_action("=" * 50)

# 로그 기록
def log_action(message):
    """
    작업 로그를 기록하는 함수
    
    Args:
        message (str): 로그 메시지
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    
    print(log_message)
    
    with open(LOG_FILE, "a") as f:
        f.write(log_message + "\n")

# 성과 기록 및 시각화
def record_performance():
    """
    포트폴리오 성과를 기록하고 시각화하는 함수
    """
    # 현재 자산 상태 조회
    balance = get_balance()
    if balance is None:
        log_action("자산 조회 실패, 성과 기록 중단")
        return
    
    # 성과 데이터 저장
    timestamp = datetime.now()
    performance_data = {
        'timestamp': timestamp,
        'btc_price': balance['btc_price'],
        'krw_balance': balance['krw_balance'],
        'btc_balance': balance['btc_balance'],
        'btc_value': balance['btc_value'],
        'total_value': balance['total_value'],
        'btc_ratio': balance['btc_ratio']
    }
    
    # CSV 파일에 성과 데이터 추가
    try:
        performance_df = pd.read_csv('performance_history.csv')
    except FileNotFoundError:
        performance_df = pd.DataFrame(columns=[
            'timestamp', 'btc_price', 'krw_balance', 'btc_balance', 
            'btc_value', 'total_value', 'btc_ratio'
        ])
    
    # DataFrame.append가 deprecated됨에 따라 pandas의 concat 사용
    new_row = pd.DataFrame([performance_data])
    performance_df = pd.concat([performance_df, new_row], ignore_index=True)
    performance_df.to_csv('performance_history.csv', index=False)
    
    # 성과 시각화 (최근 30일)
    if len(performance_df) > 1:
        recent_df = performance_df.tail(30)
        recent_df['timestamp'] = pd.to_datetime(recent_df['timestamp'])
        
        plt.figure(figsize=(12, 15))
        
        # 비트코인 가격 추이
        plt.subplot(4, 1, 1)
        plt.plot(recent_df['timestamp'], recent_df['btc_price'], 'b-')
        plt.title('BTC 가격 추이')
        plt.ylabel('가격 (KRW)')
        plt.grid(True)
        
        # 포트폴리오 가치 추이
        plt.subplot(4, 1, 2)
        plt.plot(recent_df['timestamp'], recent_df['total_value'], 'g-')
        plt.title('포트폴리오 총 가치 추이')
        plt.ylabel('가치 (KRW)')
        plt.grid(True)
        
        # 비트코인 비중 추이
        plt.subplot(4, 1, 3)
        plt.plot(recent_df['timestamp'], recent_df['btc_ratio'] * 100, 'r-')
        plt.axhline(y=TARGET_RATIO * 100, color='k', linestyle='--', label='목표 비중')
        plt.axhline(y=LOWER_THRESHOLD * 100, color='g', linestyle=':', label='하한 임계값')
        plt.axhline(y=UPPER_THRESHOLD * 100, color='g', linestyle=':', label='상한 임계값')
        plt.title('BTC 비중 추이')
        plt.ylabel('BTC 비중 (%)')
        plt.legend()
        plt.grid(True)
        
        # 자산 구성 추이
        plt.subplot(4, 1, 4)
        plt.plot(recent_df['timestamp'], recent_df['btc_value'], 'orange', label='BTC 평가금액')
        plt.plot(recent_df['timestamp'], recent_df['krw_balance'], 'blue', label='KRW 잔고')
        plt.title('자산 구성 추이')
        plt.ylabel('금액 (KRW)')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('performance_chart.png')
        log_action("성과 차트가 업데이트되었습니다: performance_chart.png")

# 메인 함수
def main():
    """
    메인 실행 함수 - 스케줄러 설정
    """
    log_action("비트코인 리밸런싱 봇 시작")
    log_action(f"설정: 목표 비율 {TARGET_RATIO*100}%, 임계값 범위 {LOWER_THRESHOLD*100}%-{UPPER_THRESHOLD*100}%")
    
    # 초기 포트폴리오 상태 확인 및 리밸런싱
    rebalance_portfolio()
    record_performance()
    
    # 정기적인 포트폴리오 상태 확인 및 리밸런싱 스케줄링
    schedule.every(CHECK_INTERVAL).hours.do(rebalance_portfolio)
    
    # 일간 성과 기록 스케줄링 (매일 오전 9시)
    schedule.every().day.at("09:00").do(record_performance)
    
    # 무한 루프로 스케줄러 실행
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분 대기


if __name__ == "__main__":
    main()
