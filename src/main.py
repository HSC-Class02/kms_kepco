import json, os, datetime as dt
from pathlib import Path
import pandas as pd
from .config import CORP_STOCK_CODE, CORP_NAME, YEARS_BACK
from .dart_api import find_corp_code, disclosures, financials
from .metrics import extract_year, calculate, to_frame

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/raw"; PROC=ROOT/"data/processed"; DASH=ROOT/"dashboard"
for p in (RAW,PROC,DASH): p.mkdir(parents=True,exist_ok=True)

def main():
    corp_code=find_corp_code(CORP_STOCK_CODE)
    (PROC/"company.json").write_text(json.dumps({
        "corp_name":CORP_NAME,"stock_code":CORP_STOCK_CODE,"corp_code":corp_code,
        "updated_at":dt.datetime.now(dt.timezone.utc).isoformat()
    },ensure_ascii=False,indent=2),encoding="utf-8")

    today=dt.date.today()
    start=(today-dt.timedelta(days=365*6)).strftime("%Y%m%d")
    end=today.strftime("%Y%m%d")
    disc=disclosures(corp_code,start,end)
    (RAW/"disclosures.json").write_text(json.dumps(disc,ensure_ascii=False,indent=2),encoding="utf-8")

    years=list(range(today.year-YEARS_BACK+1,today.year+1))
    rows=[]
    for year in years:
        try:
            data=financials(corp_code,year,"11011","CFS")
            (RAW/f"financials_{year}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
            cur=extract_year(data.get("list",[]))
            cur["year"]=year; cur["period"]="FY"
            rows.append(cur)
        except Exception as e:
            print(f"[WARN] {year}: {e}")

    rows=sorted(rows,key=lambda x:x["year"])
    calculated=[]
    for i,r in enumerate(rows):
        calculated.append(calculate(r, rows[i-1] if i else None))
    df=to_frame(calculated)
    df.to_csv(PROC/"financials.csv",index=False,encoding="utf-8-sig")
    (PROC/"financials.json").write_text(df.to_json(orient="records",force_ascii=False,indent=2),encoding="utf-8")
    generate_dashboard(df,disc)
    print(df.to_string(index=False))

def fmt(v):
    if v is None or pd.isna(v): return "-"
    return f"{v:,.1f}"

def generate_dashboard(df,disc):
    records=df.to_dict(orient="records")
    latest=records[-1] if records else {}
    labels=[str(r["year"]) for r in records]
    def series(k): return [None if r.get(k) is None else round(float(r[k]),3) for r in records]
    disclosures_list=disc.get("list",[])[:20]
    cards=[
      ("매출액", latest.get("revenue"), "원"),
      ("영업이익", latest.get("operating_income"), "원"),
      ("당기순이익", latest.get("net_income"), "원"),
      ("영업현금흐름", latest.get("cfo"), "원"),
      ("총부채", latest.get("liabilities"), "원"),
      ("순차입금", latest.get("net_debt"), "원"),
    ]
    card_html="".join(f'<div class="card"><div class="label">{a}</div><div class="value">{fmt(b)}</div><div class="unit">{c}</div></div>' for a,b,c in cards)
    disc_html="".join(f'<tr><td>{x.get("rcept_dt","")}</td><td>{x.get("report_nm","")}</td><td><a target="_blank" href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo={x.get("rcept_no","")}">DART</a></td></tr>' for x in disclosures_list)
    html=f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{CORP_NAME} DART 재무 Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f7fb;margin:0;color:#172033}}
.wrap{{max-width:1200px;margin:auto;padding:28px}} h1{{margin-bottom:4px}} .muted{{color:#667085}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:24px 0}}
.card,.panel{{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.04)}}
.label{{font-size:13px;color:#667085}} .value{{font-size:22px;font-weight:700;margin-top:8px;word-break:break-all}} .unit{{font-size:11px;color:#98a2b3;margin-top:4px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .panel{{margin-top:16px}} canvas{{max-height:340px}}
table{{width:100%;border-collapse:collapse}} th,td{{padding:9px;border-bottom:1px solid #eee;text-align:left;font-size:13px}} th{{color:#667085}}
@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
.badge{{display:inline-block;padding:4px 8px;border-radius:99px;background:#eef2ff;color:#3730a3;font-size:12px}}
</style></head><body><div class="wrap">
<h1>한국전력공사 DART 재무 Dashboard</h1>
<div class="muted">OpenDART 자동 수집 · 최근 {len(records)}개 사업연도 · 최종 업데이트 {dt.datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
<div class="cards">{card_html}</div>
<div class="grid">
<div class="panel"><h3>매출 · 영업이익</h3><canvas id="profit"></canvas></div>
<div class="panel"><h3>현금흐름 · FCF</h3><canvas id="cash"></canvas></div>
<div class="panel"><h3>수익성 비율</h3><canvas id="margin"></canvas></div>
<div class="panel"><h3>재무안정성</h3><canvas id="stability"></canvas></div>
</div>
<div class="panel"><h3>최근 DART 정기공시</h3><table><thead><tr><th>접수일</th><th>보고서</th><th>원문</th></tr></thead><tbody>{disc_html}</tbody></table></div>
<div class="panel"><h3>분석 기준</h3><p>첨부된 「재무제표 및 재무비율 실무 가이드」의 분석 순서인 매출 성장 → 이익률 → 현금흐름 → 차입 부담 → 투자수익률 → 주가 수준을 바탕으로 구성했습니다. 연결/별도 기준과 기간을 통일하고, 단일 비율보다 지표 간 연결을 확인하도록 설계했습니다.</p>
<p class="muted">DPO, ROIC, WACC, PER, PBR, EV/EBITDA는 DART 재무제표 데이터만으로 신뢰성 있게 산출하기 어려운 항목을 별도 확장 대상으로 남겨두었습니다.</p></div>
</div>
<script>
const labels={json.dumps(labels,ensure_ascii=False)};
const common={{responsive:true,plugins:{{legend:{{position:"bottom"}}}}}};
new Chart(document.getElementById("profit"),{{type:"line",data:{{labels,datasets:[
{{label:"매출액",data:{json.dumps(series("revenue"))},tension:.25}},
{{label:"영업이익",data:{json.dumps(series("operating_income"))},tension:.25}}
]}},options:common}});
new Chart(document.getElementById("cash"),{{type:"bar",data:{{labels,datasets:[
{{label:"CFO",data:{json.dumps(series("cfo"))}}},{{label:"FCF",data:{json.dumps(series("fcf"))}}}
]}},options:common}});
new Chart(document.getElementById("margin"),{{type:"line",data:{{labels,datasets:[
{{label:"매출총이익률 %",data:{json.dumps(series("gross_margin_pct"))},tension:.25}},
{{label:"영업이익률 %",data:{json.dumps(series("operating_margin_pct"))},tension:.25}},
{{label:"순이익률 %",data:{json.dumps(series("net_margin_pct"))},tension:.25}},
{{label:"ROE %",data:{json.dumps(series("roe_pct"))},tension:.25}}
]}},options:common}});
new Chart(document.getElementById("stability"),{{type:"line",data:{{labels,datasets:[
{{label:"부채비율 %",data:{json.dumps(series("debt_to_equity_pct"))},tension:.25}},
{{label:"자기자본비율 %",data:{json.dumps(series("equity_ratio_pct"))},tension:.25}},
{{label:"이자보상배율",data:{json.dumps(series("interest_coverage"))},tension:.25}}
]}},options:common}});
</script></body></html>"""
    (DASH/"index.html").write_text(html,encoding="utf-8")

if __name__=="__main__":
    main()
