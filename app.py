import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import json
import os
from typing import Dict, List, Optional, Tuple, Any
import requests

# 페이지 설정
st.set_page_config(
    page_title="배당 재투자 시뮬레이터",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ValidationError(Exception):
    """사용자 입력 검증 오류"""
    pass

class DataFetchError(Exception):
    """데이터 가져오기 오류"""
    pass

def validate_inputs(ticker: str, start_date: datetime.date, end_date: datetime.date, initial_shares: int) -> List[str]:
    """
    사용자 입력값 검증
    
    Returns:
        List[str]: 오류 메시지 리스트 (비어있으면 모든 입력이 유효함)
    """
    errors = []
    
    # 티커 검증
    if not ticker or len(ticker.strip()) == 0:
        errors.append("❌ 티커를 입력해주세요")
    elif len(ticker.strip()) > 10:
        errors.append("❌ 티커는 10자 이하여야 합니다")
    elif not ticker.replace('.', '').replace('-', '').isalnum():
        errors.append("❌ 티커는 영문, 숫자, '.', '-'만 포함할 수 있습니다")
    
    # 날짜 검증
    if end_date <= start_date:
        errors.append("❌ 종료일자가 시작일자보다 이후여야 합니다")
    
    # 기간이 너무 짧은 경우
    if (end_date - start_date).days < 30:
        errors.append("⚠️ 시뮬레이션 기간이 30일 미만입니다. 더 긴 기간을 권장합니다")
    
    # 미래 날짜가 너무 먼 경우
    today = datetime.now().date()
    if end_date > today + timedelta(days=3650):  # 10년 후
        errors.append("⚠️ 종료일자가 너무 먼 미래입니다 (최대 10년)")
    
    # 초기 보유 주식 검증
    if initial_shares <= 0:
        errors.append("❌ 초기 보유 수량은 1 이상이어야 합니다")
    elif initial_shares > 1000000:
        errors.append("⚠️ 초기 보유 수량이 너무 큽니다 (최대 100만주)")
    
    return errors

@st.cache_data(ttl=300, show_spinner=False)  # 5분 캐시
def fetch_stock_data(ticker: str, start_date: str, end_date: str) -> Tuple[pd.Series, pd.DataFrame]:
    """
    주식 데이터 가져오기 (배당금 및 가격 데이터)
    
    Args:
        ticker: 주식 티커
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        
    Returns:
        Tuple[pd.Series, pd.DataFrame]: (배당금 데이터, 가격 데이터)
        
    Raises:
        DataFetchError: 데이터 가져오기 실패시
    """
    try:
        # 네트워크 타임아웃 설정
        stock = yf.Ticker(ticker)
        
        # 기본 정보 확인 (티커 유효성 검사)
        info = stock.info
        if not info or len(info) < 5:  # 기본 정보가 너무 적으면 유효하지 않은 티커
            raise DataFetchError(f"'{ticker}'는 유효하지 않은 티커입니다.")
        
        # 배당금 데이터 가져오기
        dividends = stock.dividends
        if dividends.empty:
            raise DataFetchError(f"'{ticker}'의 배당금 데이터를 찾을 수 없습니다.")
        
        # 가격 데이터 가져오기
        today = datetime.now().date()
        actual_end = min(today, datetime.strptime(end_date, '%Y-%m-%d').date()).strftime('%Y-%m-%d')
        
        price_data = stock.history(start=start_date, end=actual_end)
        if price_data.empty:
            raise DataFetchError(f"'{ticker}'의 가격 데이터를 찾을 수 없습니다.")
        
        return dividends, price_data
        
    except requests.exceptions.RequestException:
        raise DataFetchError("네트워크 연결을 확인해주세요. 인터넷 연결이 불안정합니다.")
    except Exception as e:
        if "invalid" in str(e).lower() or "not found" in str(e).lower():
            raise DataFetchError(f"'{ticker}'는 존재하지 않는 티커입니다. 올바른 티커를 입력해주세요.")
        else:
            raise DataFetchError(f"데이터 조회 중 오류가 발생했습니다: {str(e)}")

def analyze_dividend_frequency(dividend_dates: pd.DatetimeIndex) -> Tuple[str, str, relativedelta, float]:
    """
    배당 주기 분석
    
    Args:
        dividend_dates: 배당금 지급일 인덱스
        
    Returns:
        Tuple[str, str, relativedelta, float]: (주기 단위, 설명, 델타, 평균 간격일)
    """
    if len(dividend_dates) <= 1:
        return '매월', '매월 (기본값)', relativedelta(months=1), 30.0
    
    # 날짜 간의 평균 간격 계산
    intervals = []
    for i in range(1, len(dividend_dates)):
        interval = (dividend_dates[i] - dividend_dates[i-1]).days
        intervals.append(interval)
    
    avg_interval_days = sum(intervals) / len(intervals)
    
    # 배당 주기 판단
    if 25 <= avg_interval_days <= 35:
        return '매월', '매월', relativedelta(months=1), avg_interval_days
    elif 80 <= avg_interval_days <= 100:
        return '분기', '분기별 (3개월)', relativedelta(months=3), avg_interval_days
    elif 170 <= avg_interval_days <= 200:
        return '반기', '반기별 (6개월)', relativedelta(months=6), avg_interval_days
    elif 350 <= avg_interval_days <= 380:
        return '연간', '연간 (12개월)', relativedelta(years=1), avg_interval_days
    else:
        # 기타 경우 (격월, 불규칙 등)
        return '매월', f'매월 (실제 간격: {avg_interval_days:.0f}일)', relativedelta(months=1), avg_interval_days

def find_nearest_price(target_date: pd.Timestamp, price_data: pd.DataFrame, max_days: int = 5) -> Optional[float]:
    """
    특정 날짜에 가장 가까운 주가 찾기
    
    Args:
        target_date: 목표 날짜
        price_data: 가격 데이터
        max_days: 최대 검색 일수
        
    Returns:
        Optional[float]: 찾은 주가 또는 None
    """
    price_dates = set(price_data.index)
    
    # 정확한 날짜부터 시작해서 앞뒤로 검색
    for i in range(max_days + 1):
        # 당일 또는 이후 날짜 확인
        if i == 0:
            check_date = target_date
        else:
            check_date = target_date + timedelta(days=i)
        
        if check_date in price_dates:
            return price_data.loc[check_date, 'Close']
            
        # 이전 날짜 확인
        if i > 0:
            check_date = target_date - timedelta(days=i)
            if check_date in price_dates:
                return price_data.loc[check_date, 'Close']
    
    return None

def calculate_actual_reinvestment(dividends: pd.Series, price_data: pd.DataFrame, initial_shares: float, ticker: str) -> Tuple[float, float, List[Dict]]:
    """
    실제 배당 데이터를 기반으로 재투자 계산
    
    Args:
        dividends: 배당금 데이터
        price_data: 가격 데이터  
        initial_shares: 초기 보유 주식 수
        ticker: 주식 티커
        
    Returns:
        Tuple[float, float, List[Dict]]: (총 주식 수, 누적 현금, 재투자 상세내역)
    """
    total_shares = float(initial_shares)
    accumulated_dividends = 0.0
    reinvestment_details = []
    
    # 통화 정보 - 티커를 기준으로 가져오기
    currency_symbol, _ = get_currency_info(ticker)
    
    for div_date, dividend_per_share in dividends.items():
        div_date_str = div_date.strftime('%Y-%m-%d')
        
        # 해당 날짜 주가 찾기
        price_on_date = find_nearest_price(div_date, price_data)
        if price_on_date is None:
            continue
            
        # 배당 재투자 계산
        total_dividend = dividend_per_share * total_shares
        accumulated_dividends += total_dividend
        new_shares = int(accumulated_dividends // price_on_date)
        
        if new_shares >= 1:
            accumulated_dividends -= new_shares * price_on_date
            total_shares += new_shares
        
        reinvestment_details.append({
            '날짜': div_date_str,
            f'주당배당({currency_symbol})': round(dividend_per_share, 4),
            '보유주식': round(total_shares - new_shares, 0),
            f'총배당금({currency_symbol})': round(total_dividend, 2),
            f'누적현금({currency_symbol})': round(accumulated_dividends, 2),
            f'주가({currency_symbol})': round(price_on_date, 2),
            '신규매수': int(new_shares),
            '총보유주식': round(total_shares, 0),
            '구분': '실제'
        })
    
    return total_shares, accumulated_dividends, reinvestment_details

def calculate_future_forecast(end_date_str: str, dividend_frequency: str, delta: relativedelta,
                            last_dividend: float, current_price: float, total_shares: float,
                            accumulated_dividends: float, dividend_dates: pd.DatetimeIndex, ticker: str) -> Tuple[float, float, List[Dict]]:
    """
    미래 배당 예측 계산
    
    Args:
        end_date_str: 종료 날짜 문자열
        dividend_frequency: 배당 주기
        delta: 날짜 증가 단위
        last_dividend: 마지막 배당금
        current_price: 현재 주가
        total_shares: 현재 보유 주식 수
        accumulated_dividends: 누적 현금
        dividend_dates: 기존 배당일들
        ticker: 주식 티커
        
    Returns:
        Tuple[float, float, List[Dict]]: (최종 주식 수, 최종 누적 현금, 예측 상세내역)
    """
    today = datetime.now().date()
    end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    if end_date_obj <= today:
        return total_shares, accumulated_dividends, []
    
    forecast_details = []
    # 통화 정보 - 티커를 기준으로 가져오기
    currency_symbol, _ = get_currency_info(ticker)
    
    # 다음 배당일 계산
    if len(dividend_dates) > 0:
        last_dividend_date = dividend_dates[-1].date()
        next_dividend_date = last_dividend_date
        
        # 다음 배당일까지 주기만큼 더하기
        while next_dividend_date <= today:
            next_dividend_date = next_dividend_date + delta
    else:
        next_dividend_date = today + delta
    
    current_date = next_dividend_date
    
    while current_date <= end_date_obj:
        div_date_str = current_date.strftime('%Y-%m-%d')
        
        # 배당 재투자 계산
        total_dividend = last_dividend * total_shares
        accumulated_dividends += total_dividend
        new_shares = int(accumulated_dividends // current_price)
        
        if new_shares >= 1:
            accumulated_dividends -= new_shares * current_price
            total_shares += new_shares
        
        forecast_details.append({
            '날짜': div_date_str,
            f'주당배당({currency_symbol})': round(last_dividend, 4),
            '보유주식': round(total_shares - new_shares, 0),
            f'총배당금({currency_symbol})': round(total_dividend, 2),
            f'누적현금({currency_symbol})': round(accumulated_dividends, 2),
            f'주가({currency_symbol})': round(current_price, 2),
            '신규매수': int(new_shares),
            '총보유주식': round(total_shares, 0),
            '구분': '예측'
        })
        
        current_date += delta
    
    return total_shares, accumulated_dividends, forecast_details

def simple_dividend_forecast(ticker: str, start_date: str, end_date: str, initial_shares: int = 1) -> Optional[Dict[str, Any]]:
    """
    배당 재투자 시뮬레이션 메인 함수 (리팩토링된 버전)
    
    Args:
        ticker: 주식 티커
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)  
        initial_shares: 초기 보유 주식 수
        
    Returns:
        Optional[Dict]: 시뮬레이션 결과 또는 None
    """
    # 통화 정보 설정
    currency_symbol, currency_code = get_currency_info(ticker)
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1단계: 데이터 가져오기
        status_text.text("📊 데이터를 가져오는 중...")
        progress_bar.progress(20)
        
        dividends, price_data = fetch_stock_data(ticker, start_date, end_date)
        
        # 해당 기간의 실제 배당 데이터 필터링
        today = datetime.now().date()
        actual_end = min(today, datetime.strptime(end_date, '%Y-%m-%d').date()).strftime('%Y-%m-%d')
        actual_dividends = dividends[(dividends.index >= start_date) & (dividends.index <= actual_end)]
        
        if len(actual_dividends) == 0:
            st.warning("⚠️ 해당 기간에 실제 배당 데이터가 없습니다.")
            return None
            
        progress_bar.progress(40)
        status_text.text("💰 배당 데이터 분석 중...")
        
        # 2단계: 배당 주기 분석
        dividend_frequency_unit, dividend_frequency_desc, delta, avg_interval_days = analyze_dividend_frequency(actual_dividends.index)
        
        progress_bar.progress(60)
        status_text.text("🔄 배당 재투자 계산 중...")
        
        # 3단계: 실제 데이터로 재투자 계산 (ticker 파라미터 추가)
        total_shares, accumulated_dividends, actual_details = calculate_actual_reinvestment(
            actual_dividends, price_data, initial_shares, ticker
        )
        
        progress_bar.progress(80)
        status_text.text("🔮 미래 예측 계산 중...")
        
        # 4단계: 미래 예측 계산 (ticker 파라미터 추가)
        last_dividend = actual_dividends.iloc[-1]
        current_price = price_data.iloc[-1]['Close']
        
        final_shares, final_cash, forecast_details = calculate_future_forecast(
            end_date, dividend_frequency_unit, delta, last_dividend, current_price,
            total_shares, accumulated_dividends, actual_dividends.index, ticker
        )
        
        progress_bar.progress(100)
        status_text.text("✅ 계산 완료!")
        
        # 5단계: 결과 조합
        all_details = actual_details + forecast_details
        df = pd.DataFrame(all_details)
        
        result = {
            'final_shares': int(final_shares),
            'shares_gained': int(final_shares - initial_shares),
            'remaining_cash': round(final_cash, 2),
            'dataframe': df,
            'prediction_assumptions': {
                'dividend_per_payment': round(last_dividend, 4),
                'fixed_price': round(current_price, 2),
                'dividend_frequency': dividend_frequency_desc,
                'avg_interval_days': round(avg_interval_days, 0) if len(actual_dividends.index) > 1 else None
            },
            'initial_shares': initial_shares
        }
        
        # 잠시 후 진행바 제거
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        return result
        
    except DataFetchError as e:
        progress_bar.empty()
        status_text.empty()
        st.error(str(e))
        
        # 복구 방안 제시
        st.markdown("### 💡 해결 방법:")
        if "네트워크" in str(e):
            st.info("📶 인터넷 연결을 확인하고 다시 시도해주세요.")
        elif "유효하지 않은" in str(e) or "존재하지 않는" in str(e):
            st.info("""
            📝 **올바른 티커 입력 방법:**
            - 미국 주식: AAPL, MSFT, GOOGL
            - 미국 ETF: SPY, QQQ, SCHD, JEPQ
            - 한국 주식: 005930.KS (삼성전자)
            - 한국 ETF: 284430.KS (KODEX 200)
            """)
        elif "배당금 데이터" in str(e):
            st.info("💰 해당 종목은 배당을 지급하지 않거나 배당 이력이 없습니다. 다른 배당주를 시도해보세요.")
        
        return None
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
        st.info("🔄 다시 시도해주세요. 문제가 지속되면 다른 티커로 시도해보세요.")
        return None


def get_currency_info(ticker):
    """
    티커 기반으로 통화 정보 반환
    """
    ticker_upper = ticker.upper()
    if '.KS' in ticker_upper or '.KQ' in ticker_upper:
        return '₩', 'KRW'
    else:
        return '$', 'USD'
        
def update_visitor_stats():
    """GitHub Gist를 활용한 영구 방문자 통계"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # GitHub Personal Access Token (Streamlit Secrets에 저장)
    github_token = st.secrets.get("GITHUB_TOKEN", None)
    gist_id = st.secrets.get("GIST_ID", None)
    
    if not github_token or not gist_id:
        return 0, 0, today
    
    try:
        # 기존 통계 가져오기
        headers = {"Authorization": f"token {github_token}"}
        response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
        
        if response.status_code == 200:
            gist_data = response.json()
            stats_content = gist_data["files"]["visitor_stats.json"]["content"]
            stats = json.loads(stats_content)
        else:
            # 처음 실행시
            stats = {"total_visitors": 0, "daily_visitors": {}, "first_visit_date": today}
        
        # 세션 중복 방지
        if "visited_today" not in st.session_state:
            st.session_state.visited_today = True
            
            # 통계 업데이트
            stats["total_visitors"] += 1
            if today not in stats["daily_visitors"]:
                stats["daily_visitors"][today] = 0
            stats["daily_visitors"][today] += 1
            
            # GitHub Gist 업데이트
            update_data = {
                "files": {
                    "visitor_stats.json": {
                        "content": json.dumps(stats, ensure_ascii=False, indent=2)
                    }
                }
            }
            requests.patch(f"https://api.github.com/gists/{gist_id}", 
                         headers=headers, 
                         json=update_data)
        
        return stats["total_visitors"], stats["daily_visitors"].get(today, 0), stats.get("first_visit_date", today)
        
    except Exception:
        return 0, 0, today

def display_visitor_stats():
    """방문자 통계 표시"""
    total, today_count, first_date = update_visitor_stats()
    
    if total == 0 and today_count == 0:  # 설정이 안된 경우
        return
    
    st.markdown("---")
    st.markdown("### 📊 방문자 통계")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style='text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white;'>
            <h3 style='margin: 0; font-size: 1rem;'>👥 누적 방문자</h3>
            <h2 style='margin: 0.5rem 0 0 0; font-size: 2rem; color: #FFD700;'>{total:,}명</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='text-align: center; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white;'>
            <h3 style='margin: 0; font-size: 1rem;'>📅 오늘 방문자</h3>
            <h2 style='margin: 0.5rem 0 0 0; font-size: 2rem; color: #FFE4E6;'>{today_count:,}명</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style='text-align: center; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white;'>
            <h3 style='margin: 0; font-size: 1rem;'>🚀 서비스 시작</h3>
            <h2 style='margin: 0.5rem 0 0 0; font-size: 1.5rem; color: #E1F9FE;'>{first_date}</h2>
        </div>
        """, unsafe_allow_html=True)
        
# 메인 UI
def main():
    st.title("📈 배당 재투자 시뮬레이터")
    st.markdown("### 배당금으로 주식을 재투자했을 때의 복리 효과를 계산해보세요!")
    
    # 사이드바
    with st.sidebar:
        st.markdown("## 💡 사용 가이드")
        st.info("""
        **티커 입력 예시:**
        - 미국 주식/ETF: JEPQ, SCHD, AAPL
        - 한국 주식: 005930.KS (삼성전자)
        - 한국 ETF: 284430.KS (KODEX 200)
        """)
        
        st.markdown("## 📊 개선된 예측 방법")
        st.markdown("""
        - **배당 주기 자동 감지**:<br>실제 배당 이력 분석
        - **지원 주기**:<br>매월, 분기, 반기, 연간
        - **실제 데이터**:<br>야후 파이낸스 배당 기록
        - **미래 예측**:<br>감지된 주기로 배당 반복
        - **주가**:<br>현재 주가로 고정
        """, unsafe_allow_html=True)
        
        st.markdown("## 🔧 최근 업데이트")
        st.success(
        """
        - ✅ **성능 최적화**  
          데이터 캐싱 도입  
        
        - ✅ **입력 검증**  
          강화된 유효성 검사
          
        - ✅ **에러 처리**  
          구체적인 해결방안 제시 
          
        - ✅ **코드 구조**  
          함수 분리로 안정성 향상  
          
        - ✅ **통화 표시**  
          한국 주식 원화 표시 수정  
        """)
    
    # 입력 섹션 - 모바일 친화적 레이아웃
    st.markdown("---")
    
    # 첫 번째 행: 티커와 초기 보유 수량
    col1_1, col1_2 = st.columns(2)
    
    with col1_1:
        ticker = st.text_input(
            "🎯 티커", 
            placeholder="예: SCHD",
            help="종목 코드를 입력하세요",
            max_chars=10
        ).upper().strip()

    with col1_2:
        initial_shares = st.number_input(
            "📦 초기 보유 수량", 
            min_value=1, 
            max_value=1000000,
            value=100,
            help="처음에 보유한 주식 수"
        )
    
    # 두 번째 행: 시작일자와 종료일자
    col2_1, col2_2 = st.columns(2)
    
    with col2_1:
        start_date = st.date_input(
            "📅 시작일자", 
            value=datetime(2025, 1, 1),
            help="시뮬레이션 시작 날짜"
        )

    with col2_2:
        end_date = st.date_input(
            "📅 종료일자", 
            value=datetime(2026, 12, 31),
            help="시뮬레이션 종료 날짜"
        )

    # 입력 검증
    validation_errors = validate_inputs(ticker, start_date, end_date, initial_shares)
    
    # 오류 메시지 표시
    if validation_errors:
        for error in validation_errors:
            if "❌" in error:
                st.error(error)
            else:
                st.warning(error)
    
    # 계산 버튼
    st.markdown("---")
    
    # 유효성 검사 통과시에만 버튼 활성화
    button_disabled = any("❌" in error for error in validation_errors)
    
    if st.button("🚀 배당 재투자 시뮬레이션 시작", 
                 type="primary", 
                 use_container_width=True,
                 disabled=button_disabled):
        
        # 계산 실행
        result = simple_dividend_forecast(
            ticker=ticker,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            initial_shares=initial_shares
        )
        
        if result:
            # 통화 정보 가져오기
            currency_symbol, currency_code = get_currency_info(ticker)
            
            # 결과 표시
            st.success("✅ 계산이 완료되었습니다!")
            
            # 메트릭 표시
            st.markdown("## 📊 결과 요약")
            
            # 최종 보유 주식 수를 크게 강조
            st.markdown("""
            <div style='text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; margin: 1rem 0; border-radius: 15px; 
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);'>
                <h2 style='color: white; margin: 0; font-size: 1.5rem; font-weight: 300;'>🎯 최종 보유 주식</h2>
                <h1 style='color: #FFD700; margin: 0.5rem 0; font-size: 4rem; font-weight: bold; 
                           text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{:,}주</h1>
                <p style='color: #E8F4FD; margin: 0; font-size: 1.2rem; font-weight: 500;'>
                    💎 초기 대비 <span style='color: #FFD700; font-weight: bold;'>+{:,}주</span> 증가 
                    (<span style='color: #00E676; font-weight: bold;'>+{:.1f}%</span>)
                </p>
            </div>
            """.format(
                result['final_shares'], 
                result['shares_gained'], 
                (result['shares_gained'] / result['initial_shares']) * 100
            ), unsafe_allow_html=True)
            
            # 나머지 메트릭들
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "초기 보유", 
                    f"{result['initial_shares']:,}주"
                )
            
            with col2:
                increase_rate = (result['shares_gained'] / result['initial_shares']) * 100
                st.metric(
                    "증가율", 
                    f"{increase_rate:.1f}%"
                )
            
            with col3:
                st.metric(
                    "잔여 현금", 
                    f"{currency_symbol}{result['remaining_cash']:,.2f}"
                )
            
            # 가정사항 표시
            st.markdown("## 💡 예측 가정사항")
            assumptions = result['prediction_assumptions']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                <div style='text-align: center; background-color: #e1f5fe; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #0288d1;'>
                    <h4 style='margin: 0; color: #01579b;'>📅 배당 주기</h4>
                    <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; font-weight: bold; color: #01579b;'>{}</p>
                </div>
                """.format(assumptions['dividend_frequency']), unsafe_allow_html=True)
            with col2:
                st.markdown("""
                <div style='text-align: center; background-color: #e8f5e8; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #4caf50;'>
                    <h4 style='margin: 0; color: #2e7d32;'>💰 배당금/회</h4>
                    <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; font-weight: bold;color: #2e7d32;'>{}{}</p>
                </div>
                """.format(currency_symbol, assumptions['dividend_per_payment']), unsafe_allow_html=True)
            with col3:
                st.markdown("""
                <div style='text-align: center; background-color: #fff3e0; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #ff9800;'>
                    <h4 style='margin: 0; color: #f57c00;'>📈 고정 주가</h4>
                    <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; font-weight: bold;color: #f57c00;'>{}{}</p>
                </div>
                """.format(currency_symbol, assumptions['fixed_price']), unsafe_allow_html=True)
            
            # 추가 정보 (실제 간격이 있는 경우)
            if assumptions['avg_interval_days'] is not None:
                st.markdown(f"**📊 실제 배당 간격 분석**: 평균 {assumptions['avg_interval_days']:.0f}일")
            
            # 차트 생성
            df = result['dataframe']
            if not df.empty:
                st.markdown("## 📈 보유 주식 수 변화")
                
                # 날짜를 datetime으로 변환
                df['날짜_dt'] = pd.to_datetime(df['날짜'])
                
                fig = px.line(
                    df, 
                    x='날짜_dt', 
                    y='총보유주식',
                    color='구분',
                    title=f"{ticker} 배당 재투자 시뮬레이션 ({assumptions['dividend_frequency']})",
                    labels={
                        '날짜_dt': '날짜',
                        '총보유주식': '총 보유 주식 (주)',
                        '구분': '데이터 구분'
                    }
                )
                
                fig.update_layout(
                    hovermode='x unified',
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 데이터 테이블
                st.markdown("## 📋 상세 내역")
                
                # 필터 옵션
                col1, col2 = st.columns(2)
                with col1:
                    show_actual = st.checkbox("실제 데이터 보기", True)
                with col2:
                    show_forecast = st.checkbox("예측 데이터 보기", True)
                
                # 데이터 필터링
                filtered_df = df.copy()
                if not show_actual:
                    filtered_df = filtered_df[filtered_df['구분'] != '실제']
                if not show_forecast:
                    filtered_df = filtered_df[filtered_df['구분'] != '예측']
                
                # 날짜_dt 컬럼 제거 (중복이므로)
                if '날짜_dt' in filtered_df.columns:
                    filtered_df = filtered_df.drop('날짜_dt', axis=1)
                
                # 숫자 형식 지정 및 표시용 데이터프레임 생성
                display_df = filtered_df.copy()
                
                # 숫자 컬럼들에 천의 자리 쉼표 적용
                numeric_columns = ['보유주식', '신규매수', '총보유주식']
                currency_columns = [col for col in display_df.columns if currency_symbol in col]
                
                for col in numeric_columns:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                
                for col in currency_columns:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
                
                # 스타일링된 데이터프레임 표시
                styled_df = display_df.style.set_table_styles([
                    # 날짜와 구분 컬럼 가운데 정렬
                    {'selector': 'td:nth-child(1)', 'props': [('text-align', 'center')]},  # 날짜
                    {'selector': 'td:nth-child(9)', 'props': [('text-align', 'center')]},  # 구분 (마지막 컬럼)
                    # 헤더도 가운데 정렬
                    {'selector': 'th:nth-child(1)', 'props': [('text-align', 'center')]},  # 날짜 헤더
                    {'selector': 'th:nth-child(9)', 'props': [('text-align', 'center')]},  # 구분 헤더
                    # 헤더 스타일
                    {'selector': 'th', 'props': [('background-color', '#f0f2f6'), ('font-weight', 'bold')]},
                    # 전체 테이블 스타일
                    {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},
                    {'selector': 'td, th', 'props': [('border', '1px solid #ddd'), ('padding', '8px')]}
                ])
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    height=400
                )
                
                # CSV 다운로드
                csv = df.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="📥 결과를 CSV로 다운로드",
                    data=csv,
                    file_name=f"{ticker}_dividend_simulation_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    # 👇 여기에 추가! (main() 함수의 마지막 줄)
    display_visitor_stats()


if __name__ == "__main__":
    main()
