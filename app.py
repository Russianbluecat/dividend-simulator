import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

# 페이지 설정
st.set_page_config(
    page_title="배당 재투자 시뮬레이터",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_currency_info(ticker):
    """
    티커 기반으로 통화 정보 반환
    """
    ticker_upper = ticker.upper()
    if '.KS' in ticker_upper or '.KQ' in ticker_upper:
        return '₩', 'KRW'
    else:
        return '$', 'USD'

def simple_dividend_forecast(ticker, start_date, end_date, initial_shares=1):
    """
    심플한 배당 재투자 예측 계산기 (개선된 배당 주기 분석 버전)
    """
    
    # 통화 정보 설정
    currency_symbol, currency_code = get_currency_info(ticker)
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("📊 데이터를 가져오는 중...")
    progress_bar.progress(20)

    # 현재 날짜
    today = datetime.now().date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

    # 종목 데이터 가져오기
    try:
        # yfinance 기본 세션 사용 (custom session 제거)
        stock = yf.Ticker(ticker)
        dividends = stock.dividends
        actual_end = min(today, end_date_obj).strftime('%Y-%m-%d')
        actual_dividends = dividends[(dividends.index >= start_date) & (dividends.index <= actual_end)]
        
        # 가격 데이터
        price_data = stock.history(start=start_date, end=actual_end)
        
        progress_bar.progress(40)
        status_text.text("💰 배당 데이터 분석 중...")
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ 데이터를 가져오는 중 오류 발생: {e}")
        return None

    if len(actual_dividends) == 0:
        st.warning("⚠️ 해당 기간에 실제 배당 데이터가 없습니다.")
        return None

    if len(price_data) == 0:
        st.error("❌ 주가 데이터를 찾을 수 없습니다.")
        return None

    # 예측을 위한 기준값
    last_dividend = actual_dividends.iloc[-1]
    current_price = price_data.iloc[-1]['Close']
    
    progress_bar.progress(60)
    status_text.text("🔄 배당 재투자 계산 중...")

    # 초기값 설정
    total_shares = float(initial_shares)
    accumulated_dividends = 0.0
    reinvestment_details = []

    # === 1단계: 실제 데이터로 계산 ===
    for div_date, dividend_per_share in actual_dividends.items():
        div_date_str = div_date.strftime('%Y-%m-%d')

        # 해당 날짜 주가 찾기
        price_on_date = None
        for i in range(5):
            check_date = div_date + timedelta(days=i)
            if check_date in price_data.index:
                price_on_date = price_data.loc[check_date, 'Close']
                break
            check_date = div_date - timedelta(days=i)
            if check_date in price_data.index:
                price_on_date = price_data.loc[check_date, 'Close']
                break

        if price_on_date is None:
            continue

        # 배당 재투자 계산
        total_dividend = dividend_per_share * total_shares
        accumulated_dividends += total_dividend
        new_shares = accumulated_dividends // price_on_date

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

    progress_bar.progress(80)
    status_text.text("🔮 미래 예측 계산 중...")

    # === 배당 주기 분석 로직 ===
    dividend_dates = actual_dividends.index
    
    if len(dividend_dates) > 1:
        # 날짜 간의 평균 간격 계산
        intervals = []
        for i in range(1, len(dividend_dates)):
            interval = (dividend_dates[i] - dividend_dates[i-1]).days
            intervals.append(interval)
        
        avg_interval_days = sum(intervals) / len(intervals)
        
        # 배당 주기 판단
        if 25 <= avg_interval_days <= 35:
            dividend_frequency_unit = '매월'
            dividend_frequency_desc = '매월'
            delta = relativedelta(months=1)
        elif 80 <= avg_interval_days <= 100:
            dividend_frequency_unit = '분기'
            dividend_frequency_desc = '분기별 (3개월)'
            delta = relativedelta(months=3)
        elif 170 <= avg_interval_days <= 200:
            dividend_frequency_unit = '반기'
            dividend_frequency_desc = '반기별 (6개월)'
            delta = relativedelta(months=6)
        elif 350 <= avg_interval_days <= 380:
            dividend_frequency_unit = '연간'
            dividend_frequency_desc = '연간 (12개월)'
            delta = relativedelta(years=1)
        else:
            # 그 외 대부분의 경우 (월, 격월 등)
            dividend_frequency_unit = '매월'
            dividend_frequency_desc = f'매월 (실제 간격: {avg_interval_days:.0f}일)'
            delta = relativedelta(months=1)
    else:
        # 배당 데이터가 1개 이하일 경우 기본값으로 월간 설정
        dividend_frequency_unit = '매월'
        dividend_frequency_desc = '매월 (기본값)'
        delta = relativedelta(months=1)
        avg_interval_days = 30

    # === 2단계: 미래 예측 ===
    if end_date_obj > today:
        # 마지막 배당일 기준으로 다음 배당일 계산
        if len(dividend_dates) > 0:
            last_dividend_date = dividend_dates[-1].date()
            next_dividend_date = last_dividend_date
            # 다음 배당일까지 주기만큼 더하기
            while next_dividend_date <= today:
                if dividend_frequency_unit == '연간':
                    next_dividend_date = next_dividend_date + relativedelta(years=1)
                elif dividend_frequency_unit == '반기':
                    next_dividend_date = next_dividend_date + relativedelta(months=6)
                elif dividend_frequency_unit == '분기':
                    next_dividend_date = next_dividend_date + relativedelta(months=3)
                else:  # 매월
                    next_dividend_date = next_dividend_date + relativedelta(months=1)
        else:
            next_dividend_date = today + delta

        current_date = next_dividend_date
        
        while current_date <= end_date_obj:
            div_date_str = current_date.strftime('%Y-%m-%d')

            # 배당 재투자 계산 (고정값 사용)
            total_dividend = last_dividend * total_shares
            accumulated_dividends += total_dividend
            new_shares = accumulated_dividends // current_price

            if new_shares >= 1:
                accumulated_dividends -= new_shares * current_price
                total_shares += new_shares

            reinvestment_details.append({
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

            # 날짜를 파악된 주기에 맞춰 증가
            current_date += delta

    progress_bar.progress(100)
    status_text.text("✅ 계산 완료!")
    
    # 잠시 후 진행바 제거
    time.sleep(1)
    progress_bar.empty()
    status_text.empty()

    # 데이터프레임 생성
    df = pd.DataFrame(reinvestment_details)
    
    return {
        'final_shares': int(total_shares),
        'shares_gained': int(total_shares - initial_shares),
        'remaining_cash': round(accumulated_dividends, 2),
        'dataframe': df,
        'prediction_assumptions': {
            'dividend_per_payment': round(last_dividend, 4),
            'fixed_price': round(current_price, 2),
            'dividend_frequency': dividend_frequency_desc,
            'avg_interval_days': round(avg_interval_days, 0) if len(dividend_dates) > 1 else None
        },
        'initial_shares': initial_shares
    }

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
        st.write("""
        - **배당 주기 자동 감지**: 실제 배당 이력 분석
        - **지원 주기**: 매월, 분기, 반기, 연간
        - **실제 데이터**: 야후 파이낸스 배당 기록
        - **미래 예측**: 감지된 주기로 배당 반복
        - **주가**: 현재 주가로 고정
        """)
        
        st.markdown("## 📱 모바일 최적화")
        st.info("입력창이 2x2 그리드로 배치되어 모바일에서도 편리하게 사용할 수 있습니다.")
    
    # 입력 섹션 - 모바일 친화적 레이아웃
    st.markdown("---")
    
    # 첫 번째 행: 티커와 초기 보유 수량
    col1_1, col1_2 = st.columns(2)
    
    with col1_1:
        ticker = st.text_input(
            "🎯 티커", 
            placeholder="예: SCHD",
            help="종목 코드를 입력하세요"
        ).upper().strip()

    with col1_2:
        initial_shares = st.number_input(
            "📦 초기 보유 수량", 
            min_value=1, 
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

    # 계산 버튼
    st.markdown("---")
    
    if st.button("🚀 배당 재투자 시뮬레이션 시작", type="primary", use_container_width=True):
        if not ticker:
            st.error("❌ 티커를 입력해주세요!")
            return
            
        if end_date <= start_date:
            st.error("❌ 종료일자가 시작일자보다 이후여야 합니다!")
            return
        
        # 계산 실행
        with st.spinner("계산 중..."):
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
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "초기 보유", 
                    f"{result['initial_shares']:,}주"
                )
            
            with col2:
                st.metric(
                    "최종 보유", 
                    f"{result['final_shares']:,}주",
                    delta=f"+{result['shares_gained']:,}주"
                )
            
            with col3:
                increase_rate = (result['shares_gained'] / result['initial_shares']) * 100
                st.metric(
                    "증가율", 
                    f"{increase_rate:.1f}%"
                )
            
            with col4:
                st.metric(
                    "잔여 현금", 
                    f"{currency_symbol}{result['remaining_cash']:,.2f}"
                )
            
            # 가정사항 표시
            st.markdown("## 💡 예측 가정사항")
            assumptions = result['prediction_assumptions']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info(f"📅 **배당 주기**\n{assumptions['dividend_frequency']}")
            with col2:
                st.info(f"💰 **배당금/회**\n{currency_symbol}{assumptions['dividend_per_payment']}")
            with col3:
                st.info(f"📈 **고정 주가**\n{currency_symbol}{assumptions['fixed_price']}")
            
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
                
                # 숫자 형식 지정하여 표시
                display_df = filtered_df.copy()
                display_df = display_df.round(2)
                
                st.dataframe(
                    display_df,
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

if __name__ == "__main__":
    main()
