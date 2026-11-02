<!-- KEPCO CI image is linked to the live dashboard. -->
<p align="center">
  <a href="https://hsc-class02.github.io/kms_kepco/" title="한국전력공사 재무분석 대시보드 바로가기">
    <img src="https://www.kepco.co.kr/assets/images/pages/about/policy/signature_04.svg" alt="KEPCO CI — 대시보드 바로가기" width="220">
  </a>
  <br>
  <a href="https://hsc-class02.github.io/kms_kepco/"><strong>🔗 대시보드 바로가기</strong></a>
</p>

# 한국전력공사 DART 재무분석 Agent

한국전력공사(종목코드 **015760**)의 OpenDART 정기보고서 재무제표를 수집하고, 주요 재무지표와 비율을 계산하여 GitHub Pages 대시보드로 제공합니다.

| 항목 | 설정 |
|---|---|
| 분석 기업 | 한국전력공사 (KEPCO) |
| 종목코드 | `015760` |
| 데이터 출처 | 금융감독원 OpenDART |
| 연결 기준 | 연결재무제표(CFS) |
| 수집 범위 | 2015년 이후 제공 가능한 정기보고서 |
| 대시보드 | [https://hsc-class02.github.io/kms_kepco/](https://hsc-class02.github.io/kms_kepco/) |
| 자동 업데이트 | 매월 1일 07:30 (한국시간) |
| 실행 | GitHub Actions + GitHub Pages |

## 대시보드 구성

**상단 Figures**
- 최근 공시 기준 핵심 KPI: 매출액, 영업이익, 당기순이익, 총자산, 총부채, 영업현금흐름
- 매출·영업이익 추이
- 영업·투자·재무 현금흐름 및 FCF
- 수익성 비율과 재무 레버리지·유동성 차트

**하단 Financial Tables**
- **Annual:** 사업보고서 기준 연간 손익·재무상태·현금흐름·재무비율
- **Half-year:** 반기보고서 기준 상반기 누적 실적 및 반기말 재무상태
- **Quarterly:** Q1–Q4 독립 분기 실적 및 분기말 재무상태

금액 데이터는 원천 파일에 원(KRW) 단위로 저장되며 대시보드 표에서는 억원 단위로 표시합니다. 테이블은 가로 스크롤을 지원하여 전체 계정과 비율을 확인할 수 있습니다.

## 분석 지표

| 구분 | 주요 항목 |
|---|---|
| 손익 | 매출액, 매출총이익, 매출원가, 판매비와관리비, 영업이익, 세전이익, 당기순이익, EBITDA |
| 재무상태 | 자산총계, 유동자산, 현금및현금성자산, 매출채권, 재고자산, 유형자산, 유동부채, 매입채무, 부채총계, 자본총계, 이자부차입금, 순차입금 |
| 현금흐름 | 영업활동현금흐름(CFO), 투자활동현금흐름(CFI), 재무활동현금흐름(CFF), CAPEX, FCF |
| 수익성 | 매출총이익률, 영업이익률, 순이익률, EBITDA 마진, ROA, ROE |
| 안정성 | 유동비율, 당좌비율, 부채비율, 자기자본비율, 기타 유동·비유동 금융부채 합계(대용치), 이자보상배율, 순차입금/EBITDA(원천 차입금 분해가 가능한 경우) |
| 효율성 | 총자산회전율, DSO, DIO, DPO, 현금전환주기(CCC), 매출증가율, CFO/순이익 |

## 국내 Peer Firms

전력·가스·집단에너지 유틸리티 기업을 핵심 비교군으로, 전력 인프라 상장사를 인접 비교군으로 정리했습니다.

| 기업 | 종목코드 | 구분 | 비교 근거 |
|---|---:|---|---|
| 한국가스공사 | 036460 | 핵심 유틸리티 | 가스 도입·도매, 에너지 공기업 및 연료비 구조 |
| 한국지역난방공사 | 071320 | 핵심 유틸리티 | 집단에너지·열병합 및 공공 에너지 공급 |
| 삼천리 | 004690 | 핵심 유틸리티 | 도시가스 네트워크 및 지역 에너지 공급 |
| 서울도시가스 | 017390 | 핵심 유틸리티 | 도시가스 공급·배관 네트워크 |
| 대성에너지 | 117580 | 핵심 유틸리티 | 지역 기반 도시가스 공급 |
| 한전KPS | 051600 | 인접 비교군 | 발전설비 정비·유지보수 등 전력 인프라 서비스 |
| 한전기술 | 052690 | 인접 비교군 | 발전·원자력 설계 및 엔지니어링 |

> Peer firms는 국내 에너지 섹터의 벤치마크입니다. 가스·열 공급, 발전설비 정비, 엔지니어링은 한국전력의 전력 판매·송배전과 사업모델이 다르므로 직접 경쟁사 순위나 단순 배수 비교에는 주의가 필요합니다. 비상장 발전 자회사는 상장 Peer 테이블에서 제외했습니다.

## OpenDART API 설정

1. [OpenDART](https://opendart.fss.or.kr/)에서 API 인증키를 발급합니다.
2. 저장소의 **Settings → Secrets and variables → Actions → New repository secret**으로 이동합니다.
3. Secret 이름을 정확히 `DART_API_KEY`로 입력하고 40자리 인증키를 저장합니다.

[GitHub Actions Secrets 설정 바로가기](https://github.com/HSC-Class02/kms_kepco/settings/secrets/actions)

인증키를 Python 파일, Workflow, README 또는 대시보드에 직접 입력하지 않습니다. Workflow는 `${{ secrets.DART_API_KEY }}`를 런타임 환경변수로만 전달합니다.

## 자동 수집 및 배포

워크플로: [`.github/workflows/update.yml`](.github/workflows/update.yml)

- 매월 1일 **07:30 KST** 자동 실행
- 월간 예약 실행 외에 `workflow_dispatch`로 수동 실행 가능
- DART 정기보고서 재무제표 수집 및 재무비율 계산
- 변경된 원천·가공 데이터와 대시보드 HTML을 저장소에 커밋
- GitHub Pages artifact 배포

GitHub Actions cron은 UTC 기준이므로 매월 말일 UTC 실행 후보 중 한국시간 날짜가 1일인 경우에만 수집·배포하도록 시간대 확인 단계를 둡니다.

## 데이터 구조

```text
data/
├── raw/
│   ├── disclosures.json
│   └── financials_YYYY_{Q1|H1|Q3|FY}.json
└── processed/
    ├── company.json
    ├── update_metadata.json
    ├── financials.csv
    ├── financials.json
    ├── financials_annual.csv / .json
    ├── financials_half_year.csv / .json
    └── financials_quarterly.csv / .json

dashboard/
└── index.html
```

## 데이터 범위 및 산출 기준

- OpenDART의 단일회사 전체 재무제표 API는 2015년 이후 사업연도 자료를 제공하므로 본 Agent의 기본 수집 시작연도는 **2015년**입니다.
- 재무 데이터는 연결재무제표(CFS)를 기본으로 수집합니다. 연결·별도 기준을 동일 표 안에 혼합하지 않습니다.
- 반기 및 3분기 손익·현금흐름의 누적 금액을 활용해 Q2·Q3·Q4 독립 분기 금액을 차감 산출합니다. 분기 재무상태표는 각 보고기간 말 잔액을 사용합니다.
- 중간기간 ROA·ROE·총자산회전율은 기간 일수 기준으로 연환산합니다.
- 원천 계정 누락, 0인 분모, 또는 비교 가능한 계정 부재 시 비율은 공란으로 둡니다. 한국전력의 일부 차입·사채 항목은 공시상 기타 유동·비유동 금융부채로 묶여 있으므로, 해당 합계는 금융부채 대용치로 별도 표시하며 순수 이자부차입금으로 단정하지 않습니다. 차입금의존도·순차입금/EBITDA는 원천 차입금 계정이 식별되는 경우에만 계산합니다. DPO·CCC 등도 관련 계정이 확보되는 경우에만 산출합니다.
- PER·PBR·EV/EBITDA 등 시장가치 기반 지표는 주가·시가총액 자료가 필요하므로 이 DART 재무제표 Agent의 기본 산출 범위에 포함하지 않습니다.

공식 참고:
- [OpenDART 단일회사 전체 재무제표 API](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020)
- [한국전력공사 공식 CI](https://www.kepco.co.kr/home/about/introduce/ci/conts.do)
