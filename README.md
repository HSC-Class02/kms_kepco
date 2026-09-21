# 한국전력공사 DART 재무분석 Agent

DART OpenAPI에서 한국전력공사(종목코드 `015760`, DART 기업 식별용 stock code) 정기보고서와 재무제표를 자동 수집하고, 첨부된 **「재무제표 및 재무비율 실무 가이드」**의 핵심 지표를 계산하여 GitHub Pages용 정적 Dashboard를 생성합니다.

> 대상: 한국전력공사 / DART stock_code `015760`  
> API: OpenDART  
> 자동화: GitHub Actions  
> Dashboard: GitHub Pages (`dashboard/`)

## 포함 기능

- DART 공시검색 API로 사업보고서/분기·반기보고서 목록 자동 수집
- DART 재무제표 API로 최근 5개 연도 주요 계정 자동 수집
- 원천 JSON을 `data/raw/`에 저장
- 표준화된 재무 데이터와 재무비율을 `data/processed/financials.csv`로 생성
- `dashboard/index.html`을 자동 생성하여 GitHub Pages에서 조회
- GitHub Actions가 정기적으로 실행되어 신규 공시/재무수치를 자동 반영
- API Key는 GitHub Secrets에 저장하며 코드에 직접 넣지 않음

## 분석 지표

첨부 가이드의 핵심 수치를 기준으로 다음을 구현합니다.

### 재무상태표
총자산, 현금및현금성자산, 매출채권, 재고자산, 유형자산, 총부채, 이자부차입금, 자본총계

### 손익계산서
매출액, 매출총이익, 판매비와관리비, 영업이익, 세전이익, 당기순이익, 지배주주순이익, EBITDA

### 현금흐름
영업활동현금흐름(CFO), 투자활동현금흐름, 재무활동현금흐름, CAPEX, FCF, 순차입금

### 비율
매출총이익률, 영업이익률, 순이익률, EBITDA 마진, ROA, ROE, 유동비율, 당좌비율, 부채비율, 자기자본비율, 차입금의존도, 이자보상배율, 순차입금/EBITDA, 총자산회전율, DSO, DIO, DPO, CCC, 매출증가율, CFO/순이익

ROIC·PER·PBR·EV/EBITDA는 DART 재무제표만으로는 조정된 투하자본/WACC 또는 주가·시가총액 데이터가 필요하므로 별도 확장 대상으로 표시합니다.

## 1. OpenDART API Key 발급

1. OpenDART에 가입/로그인
2. 인증키 발급
3. GitHub repository의 **Settings → Secrets and variables → Actions → New repository secret**
4. 이름: `DART_API_KEY`
5. 값: 발급받은 40자리 인증키

공개 저장소이므로 API Key를 `.py`, `.yml`, `.json`에 직접 입력하지 마세요.

## 2. GitHub에 업로드

이 ZIP을 풀어 저장소 루트에 파일을 올립니다.

```bash
git add .
git commit -m "Add DART financial analysis agent"
git push origin main
```

## 3. GitHub Pages

Repository → Settings → Pages에서:

- Source: GitHub Actions

또는 `gh-pages` 방식으로 별도 배포하도록 바꿀 수 있습니다. 이 프로젝트의 workflow는 `dashboard/`를 Pages artifact로 배포합니다.

## 4. 자동 업데이트

`.github/workflows/update.yml`은 매일 KST 07:30에 실행되도록 설정되어 있습니다. GitHub Actions의 cron은 UTC 기준으로 동작하므로 `22:30 UTC = 07:30 KST`입니다.

또한 `workflow_dispatch`로 수동 실행할 수 있습니다.

## 5. 로컬 실행

```bash
pip install -r requirements.txt
export DART_API_KEY="발급받은키"
python -m src.main
```

Windows PowerShell:

```powershell
$env:DART_API_KEY="발급받은키"
python -m src.main
```

생성 파일:
- `data/raw/disclosures.json`
- `data/raw/financials_YYYY.json`
- `data/processed/financials.csv`
- `data/processed/financials.json`
- `dashboard/index.html`

## 데이터 해석 주의

첨부 가이드의 원칙에 따라 연결/별도 기준을 섞지 않고, 손익·현금흐름과 재무상태표의 기간/시점 차이를 고려합니다. ROA·ROE·회전율은 가능한 경우 평균 자산/평균 자본을 사용합니다. 또한 전기 이익이 0 또는 음수인 경우 성장률/배수를 무리하게 계산하지 않습니다.

DART 원천자료의 계정명이 보고서별로 달라질 수 있으므로 계정명 매핑은 `src/metrics.py`에서 관리합니다.
