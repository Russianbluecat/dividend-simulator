# dividend-simulator
# 📈 배당 재투자 시뮬레이터

> 배당금으로 주식을 재투자했을 때의 복리 효과를 시각화하는 웹 애플리케이션
> 
> An interactive web app to explore how reinvesting dividends boosts long-term compounding growth

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 주요 기능

- 🎯 **실시간 데이터**: Yahoo Finance API를 통한 최신 주가/배당 정보
- 📊 **인터랙티브 차트**: 배당 재투자 효과를 시각적으로 확인
- 🔮 **미래 예측**: 최신 배당금 기준으로 미래 수익 시뮬레이션
- 📱 **반응형 디자인**: 모바일/데스크톱 모든 기기에서 완벽 동작
- 📥 **결과 다운로드**: CSV 형태로 상세 내역 저장 가능
- 🌍 **글로벌 지원**: 미국, 한국 등 전세계 주식/ETF 지원

## 🚀 라이브 데모

**웹사이트**: [https://dividend-simulator.streamlit.app](https://dividend-simulator.streamlit.app)

## 🛠 로컬 설치 및 실행

### 요구사항
- Python 3.8 이상
- pip

### 설치
```bash
# 저장소 클론
git clone https://github.com/yourusername/dividend-simulator.git
cd dividend-simulator

# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run streamlit_app.py
```

브라우저에서 `http://localhost:8501` 접속

## 📚 사용법

### 1. 기본 사용법
1. **티커 입력**: 종목 코드 입력 (예: JEPQ, SCHD)
2. **기간 설정**: 시뮬레이션 시작/종료 날짜 선택
3. **초기 수량**: 처음 보유할 주식 수 입력
4. **계산 시작**: 버튼 클릭하여 시뮬레이션 실행

### 2. 지원 종목
- **미국 주식/ETF**: `JEPQ`, `SCHD`, `AAPL`, `MSFT` 등
- **한국 주식**: `005930.KS` (삼성전자), `000660.KS` (SK하이닉스) 등
- **한국 ETF**: `284430.KS` (KODEX 200) 등

### 3. 예측 방법
- **실제 데이터**: Yahoo Finance의 과거 배당 기록 사용
- **미래 예측**: 가장 최근 배당금을 매월 반복한다고 가정
- **재투자**: 배당금이 1주 이상 매수 가능할 때 자동 재투자

## 📊 분석 결과

시뮬레이터는 다음 정보를 제공합니다:

- 📈 **보유 주식 수 변화**: 시간에 따른 주식 증가 추이
- 💰 **배당 재투자 효과**: 초기 대비 최종 보유 주식 수
- 📋 **상세 내역**: 각 배당일별 재투자 기록
- 💡 **예측 가정**: 사용된 배당금 및 주가 정보

## 🤝 기여하기

프로젝트 개선을 위한 기여를 환영합니다!

### 개발 환경 설정
```bash
# 개발용 의존성 포함 설치
pip install -r requirements-dev.txt

# 코드 포맷팅
black streamlit_app.py

# 타입 체크
mypy streamlit_app.py
```

### 기여 방법
1. Fork 생성
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시 (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 🐛 이슈 리포트

버그나 기능 요청이 있으시면 [Issues](https://github.com/yourusername/dividend-simulator/issues)에 등록해주세요.

### 버그 리포트 시 포함할 정보
- 사용 중인 브라우저 및 버전
- 입력한 티커 및 설정값
- 오류 메시지 (있는 경우)
- 재현 가능한 단계

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## ⚠️ 주의

이 시뮬레이터는 교육 및 참고 목적으로만 제공됩니다. 실제 투자 결정에 사용하기 전에 반드시 전문가와 상담하시기 바랍니다. 

- 과거 데이터 기반 예측이므로 실제 결과와 다를 수 있습니다
- 배당금 변경, 주가 변동 등은 고려되지 않습니다
- 세금, 수수료 등의 비용은 계산에 포함되지 않습니다

## 🔧 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **Data Source**: Yahoo Finance API (yfinance)
- **Charts**: Plotly
- **Deployment**: Streamlit Community Cloud

## 📈 향후 계획

- [ ] 포트폴리오 분석 (여러 종목 동시)
- [ ] 배당 성장률 고려한 예측
- [ ] 수익률 비교 분석
- [ ] 다국어 지원

## 👨‍💻 개발자

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Email: ss3007@naver.com

## 🙏 감사의 말

- [Yahoo Finance](https://finance.yahoo.com/) - 주식 데이터 제공
- [Streamlit](https://streamlit.io/) - 웹 앱 프레임워크
- [Plotly](https://plotly.com/) - 인터랙티브 차트

---

⭐ 이 프로젝트가 도움이 되셨다면 Star를 눌러주세요!

**Made with ❤️ and Python**
