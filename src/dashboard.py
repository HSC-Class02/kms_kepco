"""Static, self-contained KEPCO dashboard generator."""
import html
import json
import math
from pathlib import Path

PEERS = [
    ("한국가스공사", "036460", "가스 도입·도매 유틸리티", "연료 조달·요금 구조 및 에너지 공기업 비교"),
    ("한국지역난방공사", "071320", "집단에너지·열병합", "공공 에너지 공급 및 발전·열 사업 비교"),
    ("삼천리", "004690", "도시가스·에너지", "규제형 에너지 네트워크와 안정적 공급 사업 비교"),
    ("서울도시가스", "017390", "도시가스 공급", "도시가스 소매·배관 네트워크 사업 비교"),
    ("대성에너지", "117580", "도시가스 공급", "지역 기반 에너지 유틸리티 사업 비교"),
    ("한전KPS", "051600", "발전설비 정비", "전력산업 밸류체인의 상장 인프라 기업; 인접 비교군"),
    ("한전기술", "052690", "전력·원자력 엔지니어링", "전력 인프라 설계·엔지니어링 기업; 인접 비교군"),
]

COLUMNS = [
    ("year", "연도", "year"),
    ("period_label", "기간", "text"),
    ("revenue", "매출액", "money"),
    ("gross_profit", "매출총이익", "money"),
    ("operating_income", "영업이익", "money"),
    ("pretax_income", "세전이익", "money"),
    ("net_income", "당기순이익", "money"),
    ("ebitda", "EBITDA", "money"),
    ("assets", "자산총계", "money"),
    ("current_assets", "유동자산", "money"),
    ("cash", "현금성자산", "money"),
    ("receivables", "매출채권", "money"),
    ("inventory", "재고자산", "money"),
    ("ppe", "유형자산", "money"),
    ("current_liabilities", "유동부채", "money"),
    ("payables", "매입채무", "money"),
    ("liabilities", "부채총계", "money"),
    ("equity", "자본총계", "money"),
    ("interest_bearing_debt", "이자부차입금", "money"),
    ("net_debt", "순차입금", "money"),
    ("cfo", "영업현금흐름", "money"),
    ("cfi", "투자현금흐름", "money"),
    ("cff", "재무현금흐름", "money"),
    ("capex", "CAPEX", "money"),
    ("fcf", "FCF", "money"),
    ("gross_margin_pct", "매출총이익률", "pct"),
    ("operating_margin_pct", "영업이익률", "pct"),
    ("net_margin_pct", "순이익률", "pct"),
    ("roa_pct", "ROA", "pct"),
    ("roe_pct", "ROE", "pct"),
    ("current_ratio_pct", "유동비율", "pct"),
    ("quick_ratio_pct", "당좌비율", "pct"),
    ("debt_to_equity_pct", "부채비율", "pct"),
    ("equity_ratio_pct", "자기자본비율", "pct"),
    ("debt_dependency_pct", "차입금의존도", "pct"),
    ("interest_coverage", "이자보상배율", "multiple"),
    ("net_debt_to_ebitda", "순차입금/EBITDA", "multiple"),
    ("asset_turnover", "총자산회전율", "multiple"),
    ("dso_days", "DSO(일)", "days"),
    ("dio_days", "DIO(일)", "days"),
    ("dpo_days", "DPO(일)", "days"),
    ("ccc_days", "현금전환주기(일)", "days"),
    ("revenue_growth_pct", "매출증가율", "pct"),
    ("cfo_to_net_income", "CFO/순이익", "multiple"),
]


def _safe_records(records):
    safe = []
    for record in records or []:
        row = {}
        for key, value in record.items():
            if value is None:
                row[key] = None
                continue
            try:
                if isinstance(value, float) and not math.isfinite(value):
                    row[key] = None
                elif hasattr(value, "item"):
                    row[key] = value.item()
                else:
                    row[key] = value
            except (TypeError, ValueError):
                row[key] = None
        safe.append(row)
    return safe


def _fmt(value, kind):
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if not math.isfinite(number):
        return "—"
    if kind == "money":
        return f"{number / 100_000_000:,.1f}"
    if kind == "pct":
        return f"{number:,.1f}%"
    if kind == "multiple":
        return f"{number:,.2f}x"
    if kind == "days":
        return f"{number:,.1f}"
    if kind == "year":
        return str(int(number))
    return html.escape(str(value))


def _table(records, title):
    rows = sorted(records, key=lambda item: (item.get("year", 0), item.get("period", "")), reverse=True)
    if not rows:
        return (
            f'<div class="table-empty">{html.escape(title)} 데이터가 아직 없습니다. '
            "DART API 인증키를 확인하고 Actions 워크플로를 실행해 주세요.</div>"
        )
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label, _ in COLUMNS)
    body_rows = []
    for row in rows:
        cells = []
        for key, _, kind in COLUMNS:
            value = row.get(key)
            cell = _fmt(value, kind)
            cells.append(f'<td class="num">{cell}</td>' if kind not in {"year", "text"} else f"<td>{cell}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-scroll"><table class="financial-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def generate_dashboard(annual, half_year, quarterly, disclosures, metadata, output_path):
    annual = _safe_records(annual)
    half_year = _safe_records(half_year)
    quarterly = _safe_records(quarterly)
    disclosures = (disclosures or {}).get("list", [])

    latest = quarterly[-1] if quarterly else (half_year[-1] if half_year else (annual[-1] if annual else {}))
    latest_period = f'{latest.get("year", "—")} {latest.get("period_label", "")}'.strip()
    kpis = [
        ("매출액", latest.get("revenue"), "억원"),
        ("영업이익", latest.get("operating_income"), "억원"),
        ("당기순이익", latest.get("net_income"), "억원"),
        ("총자산", latest.get("assets"), "억원"),
        ("총부채", latest.get("liabilities"), "억원"),
        ("영업현금흐름", latest.get("cfo"), "억원"),
    ]
    kpi_html = "".join(
        '<article class="kpi"><div class="kpi-label">' + html.escape(label) + '</div>'
        '<div class="kpi-value">' + ("—" if value is None else f"{float(value)/100_000_000:,.1f}") +
        '</div><div class="kpi-unit">' + unit + " · " + html.escape(latest_period) + "</div></article>"
        for label, value, unit in kpis
    )

    disc_rows = []
    for item in disclosures[:15]:
        rcept_no = html.escape(str(item.get("rcept_no", "")))
        date = html.escape(str(item.get("rcept_dt", "")))
        name = html.escape(str(item.get("report_nm", "")))
        href = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
        disc_rows.append(
            f'<tr><td>{date}</td><td>{name}</td>'
            f'<td><a href="{href}" target="_blank" rel="noopener">공시 원문 ↗</a></td></tr>'
        )
    if not disc_rows:
        disc_rows = ['<tr><td colspan="3" class="center">공시 데이터가 없습니다.</td></tr>']

    peer_rows = []
    for name, ticker, segment, note in PEERS:
        peer_rows.append(
            "<tr>"
            f'<td><strong>{html.escape(name)}</strong></td>'
            f'<td class="ticker">{ticker}</td>'
            f'<td>{html.escape(segment)}</td>'
            f'<td>{html.escape(note)}</td>'
            "</tr>"
        )

    annual_json = json.dumps(annual, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    half_json = json.dumps(half_year, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    quarter_json = json.dumps(quarterly, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    updated_at = html.escape(str(metadata.get("updated_at", "—")))
    source_period = f'데이터 범위 {metadata.get("start_year", "2015")}–{metadata.get("end_year", "—")} · 연결재무제표'
    html_doc = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="한국전력공사 DART 재무 데이터 및 재무비율 분석 대시보드">
<title>한국전력공사 | Financial Intelligence Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root{--navy:#142b50;--blue:#2257a5;--red:#e31b36;--ink:#1a2940;--muted:#728096;--line:#e5eaf1;--paper:#f4f7fb;--white:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,"Pretendard","Noto Sans KR",system-ui,-apple-system,sans-serif}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}.shell{max-width:1480px;margin:auto;padding:30px 28px 54px}
.hero{background:linear-gradient(115deg,#112a50 0%,#1c477e 70%,#2257a5 100%);color:#fff;border-radius:22px;padding:30px 34px;position:relative;overflow:hidden}
.hero:after{content:"";position:absolute;width:340px;height:340px;border:1px solid rgba(255,255,255,.12);border-radius:50%;right:-70px;top:-140px;box-shadow:0 0 0 34px rgba(255,255,255,.035),0 0 0 72px rgba(255,255,255,.025)}
.hero-top{display:flex;align-items:center;gap:18px;position:relative;z-index:1}.logo{width:138px;max-height:52px;object-fit:contain;background:#fff;border-radius:9px;padding:7px 10px}.eyebrow{font-size:11px;letter-spacing:.18em;font-weight:800;color:#c7d7ef;text-transform:uppercase}.hero h1{font-size:clamp(24px,3vw,36px);margin:5px 0 7px;letter-spacing:-.04em}.hero p{margin:0;color:#d9e4f3;font-size:13px;line-height:1.7;max-width:820px}.hero-meta{display:flex;flex-wrap:wrap;gap:9px;margin-top:20px;position:relative;z-index:1}.chip{font-size:11px;color:#eaf1fa;border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:6px 10px;background:rgba(255,255,255,.08)}
.section-heading{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin:30px 2px 14px}.section-heading h2{font-size:20px;margin:0;letter-spacing:-.035em;color:var(--navy)}.section-heading p{margin:5px 0 0;color:var(--muted);font-size:12px}.muted{color:var(--muted)}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin-top:18px}.kpi,.panel,.table-panel,.peer-panel{background:var(--white);border:1px solid var(--line);border-radius:15px;box-shadow:0 4px 16px rgba(21,43,80,.045)}
.kpi{padding:16px 17px}.kpi-label{font-size:12px;color:var(--muted);font-weight:650}.kpi-value{font-variant-numeric:tabular-nums;font-size:21px;font-weight:800;letter-spacing:-.035em;margin:9px 0 4px;color:var(--navy);overflow-wrap:anywhere}.kpi-unit{font-size:10px;color:#98a3b3}
.chart-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.panel{padding:19px 20px;min-width:0}.panel h3{margin:0 0 4px;font-size:14px;color:var(--navy)}.panel .sub{font-size:11px;color:var(--muted);margin-bottom:12px}.chart-wrap{height:260px;position:relative}.chart-note{font-size:10px;color:#8793a4;margin:10px 0 0}
.analysis-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}.insight{padding:16px 18px;background:#fff;border:1px solid var(--line);border-radius:13px}.insight b{display:block;font-size:12px;color:var(--navy);margin-bottom:6px}.insight span{font-size:11px;line-height:1.7;color:var(--muted)}
.table-panel{padding:18px 18px 12px;margin-bottom:14px}.table-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.table-top h3{font-size:15px;margin:0;color:var(--navy)}.table-top span{font-size:10px;color:var(--muted)}.table-scroll{overflow:auto;border:1px solid var(--line);border-radius:10px;max-width:100%}
.financial-table{border-collapse:separate;border-spacing:0;white-space:nowrap;min-width:100%;font-variant-numeric:tabular-nums;font-size:11px}.financial-table th{background:#f1f4f8;color:#65748a;font-weight:750;padding:10px 11px;text-align:right;border-bottom:1px solid var(--line);position:sticky;top:0}.financial-table th:first-child,.financial-table th:nth-child(2),.financial-table td:first-child,.financial-table td:nth-child(2){text-align:left}.financial-table td{padding:9px 11px;text-align:right;border-bottom:1px solid #edf0f4;color:#26364d}.financial-table tbody tr:nth-child(even){background:#fbfcfe}.financial-table tbody tr:hover{background:#f3f7fd}.financial-table tbody tr:last-child td{border-bottom:0}.table-empty{padding:28px;text-align:center;color:var(--muted);background:#f8fafc;border:1px dashed #d6deea;border-radius:10px;font-size:12px}
.data-note{font-size:11px;line-height:1.8;color:var(--muted);margin:14px 3px 24px}.peer-panel{padding:18px;margin-top:16px}.simple-table{width:100%;border-collapse:collapse;font-size:12px}.simple-table th{text-align:left;background:#f1f4f8;color:#65748a;padding:11px 12px;font-weight:750}.simple-table td{padding:11px 12px;border-bottom:1px solid #edf0f4;line-height:1.5}.simple-table tr:last-child td{border-bottom:0}.ticker{font-family:ui-monospace,monospace;font-weight:700;color:var(--blue)}.center{text-align:center}.disclosures{margin-top:16px}.footer{margin-top:26px;border-top:1px solid #dfe5ee;padding-top:16px;color:#8793a4;font-size:10px;line-height:1.7}
@media(max-width:1100px){.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:760px){.shell{padding:16px 12px 36px}.hero{padding:23px 20px}.hero-top{align-items:flex-start;flex-direction:column}.chart-grid{grid-template-columns:1fr}.analysis-strip{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.section-heading{align-items:flex-start;flex-direction:column}.chart-wrap{height:230px}}
</style>
</head>
<body>
<div class="shell">
<header class="hero">
 <div class="hero-top">
  <img class="logo" src="https://www.kepco.co.kr/assets/images/pages/about/policy/signature_04.svg" alt="KEPCO corporate identity">
  <div><div class="eyebrow">Financial Intelligence · DART Data</div>
   <h1>한국전력공사 기업 분석</h1>
   <p>전력 판매·송배전 및 에너지 인프라 사업의 실적, 재무구조, 현금창출력을 연결재무제표 기준으로 추적합니다.</p>
  </div>
 </div>
 <div class="hero-meta">
  <span class="chip">KOSPI · 015760</span><span class="chip">OpenDART · Consolidated</span>
  <span class="chip">__DATA_PERIOD__</span><span class="chip">Updated · __UPDATED_AT__</span>
 </div>
</header>

<div class="section-heading"><div><h2>01 · 핵심 재무 지표</h2><p>가장 최근 수집된 보고기간 기준 · 금액 단위: 억원</p></div></div>
<section class="kpis">__KPI_CARDS__</section>

<div class="section-heading"><div><h2>02 · Financial Overview</h2><p>주요 실적 추세와 재무 안정성을 시각적으로 비교합니다.</p></div></div>
<section class="chart-grid">
 <article class="panel"><h3>매출 및 영업이익 추이</h3><div class="sub">연간 재무성과 · 억원</div><div class="chart-wrap"><canvas id="profitChart"></canvas></div></article>
 <article class="panel"><h3>영업·투자·재무 현금흐름</h3><div class="sub">현금흐름 및 잉여현금흐름 · 억원</div><div class="chart-wrap"><canvas id="cashChart"></canvas></div></article>
 <article class="panel"><h3>수익성 지표</h3><div class="sub">매출총이익률 · 영업이익률 · 순이익률 · %</div><div class="chart-wrap"><canvas id="marginChart"></canvas></div></article>
 <article class="panel"><h3>재무 레버리지와 유동성</h3><div class="sub">부채비율 · 자기자본비율 · 유동비율 · %</div><div class="chart-wrap"><canvas id="balanceChart"></canvas></div></article>
</section>
<section class="analysis-strip">
 <div class="insight"><b>수익성 분석</b><span>전력 판매수익과 연료·구입전력비 등 원가 요인의 변화를 함께 확인합니다. 매출 성장만으로 수익성 개선을 판단하지 않습니다.</span></div>
 <div class="insight"><b>재무 안정성</b><span>부채비율, 차입금의존도, 유동비율과 순차입금/EBITDA를 함께 비교해 자본구조와 상환 부담을 점검합니다.</span></div>
 <div class="insight"><b>현금흐름 분석</b><span>영업현금흐름에서 CAPEX를 차감한 FCF를 확인하고, 회계상 이익과 현금창출력의 차이를 추적합니다.</span></div>
</section>

<div class="section-heading"><div><h2>03 · 재무 데이터 테이블</h2><p>원천 데이터는 원(KRW) 단위로 저장하며, 아래 표는 억원 및 비율 기준으로 표시합니다.</p></div></div>
<section class="table-panel"><div class="table-top"><h3>Annual · 연간</h3><span>사업보고서 · FY</span></div>__ANNUAL_TABLE__</section>
<section class="table-panel"><div class="table-top"><h3>Half-year · 반기</h3><span>반기보고서 · H1 누적</span></div>__HALF_TABLE__</section>
<section class="table-panel"><div class="table-top"><h3>Quarterly · 분기</h3><span>Q1–Q4 독립 분기 기준</span></div>__QUARTER_TABLE__</section>

<div class="data-note">
 <strong>데이터 해석 및 범위</strong><br>
 • OpenDART 전체 재무제표 API가 제공하는 2015년 이후 자료를 수집합니다. 연결재무제표(CFS)를 기본으로 하며 개별재무제표와 혼합하지 않습니다.<br>
 • 반기 및 3분기 보고서의 손익·현금흐름 누적 금액을 전분기 누적치와 차감하여 Q2·Q3·Q4 독립 분기 수치를 산출합니다. 분기 재무상태표는 각 보고기간 말 잔액입니다.<br>
 • 중간기간 ROA·ROE·총자산회전율은 기간 일수로 연환산합니다. 일부 비율은 원천 계정이 없거나 분모가 0인 경우 표시하지 않습니다. DPO·CCC 등은 관련 계정 확보 여부에 따라 공란일 수 있습니다.
</div>

<section class="peer-panel">
 <div class="table-top"><h3>04 · Domestic Peer Firms</h3><span>국내 상장 에너지·전력 인프라 비교기업</span></div>
 <div class="table-scroll"><table class="simple-table"><thead><tr><th>기업명</th><th>종목코드</th><th>사업영역</th><th>비교 관점</th></tr></thead><tbody>__PEER_ROWS__</tbody></table></div>
 <p class="data-note">Peer group은 전력·가스·집단에너지 유틸리티와 전력 인프라 관련 상장사를 포함합니다. 한전과 사업구조가 완전히 동일하지 않으므로 직접 경쟁사 순위가 아닌 국내 에너지 섹터 벤치마크로 활용해야 합니다. 발전 자회사 등 비상장사는 상장 Peer 분석에서 제외했습니다.</p>
</section>

<section class="table-panel disclosures"><div class="table-top"><h3>05 · 최근 DART 정기공시</h3><span>OpenDART · 정기공시</span></div>
 <div class="table-scroll"><table class="simple-table"><thead><tr><th>접수일</th><th>보고서명</th><th>원문</th></tr></thead><tbody>__DISCLOSURE_ROWS__</tbody></table></div>
</section>

<footer class="footer">
 Source: 금융감독원 전자공시시스템 OpenDART · 연결재무제표 · 종목코드 015760<br>
 Automated collection: GitHub Actions · Monthly refresh on the 1st (Korea Standard Time) · Repository: HSC-Class02/kms_kepco
</footer>
</div>

<script>
const annualData = __ANNUAL_JSON__;
const halfData = __HALF_JSON__;
const quarterData = __QUARTER_JSON__;
const chartFont = {family:'Inter, Pretendard, sans-serif'};
const commonOptions = {
 responsive:true, maintainAspectRatio:false,
 interaction:{mode:'index',intersect:false},
 plugins:{legend:{position:'bottom',labels:{usePointStyle:true,boxWidth:7,font:{size:10,family:chartFont.family}}}},
 scales:{x:{grid:{display:false},ticks:{font:{size:10}}},y:{grid:{color:'#edf1f6'},ticks:{font:{size:10},callback:v=>Number(v).toLocaleString('ko-KR')}}}
};
function amountSeries(key){return annualData.map(r=>r[key]==null?null:Number(r[key])/100000000)}
function drawChart(id,type,labels,datasets,percent=false){
 const canvas=document.getElementById(id); if(!canvas || !labels.length) return;
 const options=JSON.parse(JSON.stringify(commonOptions));
 if(percent) options.scales.y.ticks.callback=(v)=>v+'%';
 new Chart(canvas,{type,data:{labels,datasets},options});
}
const years=annualData.map(r=>String(r.year));
drawChart('profitChart','line',years,[
 {label:'매출액',data:amountSeries('revenue'),borderColor:'#2257a5',backgroundColor:'rgba(34,87,165,.08)',fill:true,tension:.28,borderWidth:2.5,pointRadius:2},
 {label:'영업이익',data:amountSeries('operating_income'),borderColor:'#e31b36',tension:.28,borderWidth:2.2,pointRadius:2}
]);
drawChart('cashChart','bar',years,[
 {label:'CFO',data:amountSeries('cfo'),backgroundColor:'#2257a5'},
 {label:'CFI',data:amountSeries('cfi'),backgroundColor:'#8fa7c8'},
 {label:'CFF',data:amountSeries('cff'),backgroundColor:'#d6a34b'},
 {label:'FCF',data:amountSeries('fcf'),backgroundColor:'#e31b36'}
]);
drawChart('marginChart','line',years,[
 {label:'매출총이익률',data:annualData.map(r=>r.gross_margin_pct),borderColor:'#2257a5',tension:.28,borderWidth:2,pointRadius:2},
 {label:'영업이익률',data:annualData.map(r=>r.operating_margin_pct),borderColor:'#e31b36',tension:.28,borderWidth:2,pointRadius:2},
 {label:'순이익률',data:annualData.map(r=>r.net_margin_pct),borderColor:'#4d9b82',tension:.28,borderWidth:2,pointRadius:2}
],true);
drawChart('balanceChart','line',years,[
 {label:'부채비율',data:annualData.map(r=>r.debt_to_equity_pct),borderColor:'#e31b36',tension:.28,borderWidth:2,pointRadius:2},
 {label:'자기자본비율',data:annualData.map(r=>r.equity_ratio_pct),borderColor:'#2257a5',tension:.28,borderWidth:2,pointRadius:2},
 {label:'유동비율',data:annualData.map(r=>r.current_ratio_pct),borderColor:'#4d9b82',tension:.28,borderWidth:2,pointRadius:2}
],true);
</script>
</body></html>"""
    replacements = {
        "__DATA_PERIOD__": html.escape(source_period),
        "__UPDATED_AT__": updated_at,
        "__KPI_CARDS__": kpi_html,
        "__ANNUAL_TABLE__": _table(annual, "연간"),
        "__HALF_TABLE__": _table(half_year, "반기"),
        "__QUARTER_TABLE__": _table(quarterly, "분기"),
        "__PEER_ROWS__": "".join(peer_rows),
        "__DISCLOSURE_ROWS__": "".join(disc_rows),
        "__ANNUAL_JSON__": annual_json,
        "__HALF_JSON__": half_json,
        "__QUARTER_JSON__": quarter_json,
    }
    for marker, value in replacements.items():
        html_doc = html_doc.replace(marker, value)
    Path(output_path).write_text(html_doc, encoding="utf-8")
