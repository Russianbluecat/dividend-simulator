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
        st.success("""
        ✅ **성능 최적화**: 데이터 캐싱 도입
        ✅ **입력 검증**: 강화된 유효성 검사  
        ✅ **에러 처리**: 구체적인 해결방안 제시
        ✅ **코드 구조**: 함수 분리로 안정성 향상
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

if __name__ == "__main__":
    main()
