import math
import re
import pandas as pd

def clean_num(x):
    if x is None or x == "":
        return None
    s = str(x).replace(",", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None

def pick(rows, names, sj_div=None):
    names = [n.lower() if isinstance(n, str) else str(n).lower() for n in names]
    candidates = []
    for r in rows:
        if sj_div and r.get("sj_div") != sj_div:
            continue
        nm = str(r.get("account_nm") or "").lower()
        if any(n in nm for n in names):
            candidates.append(r)
    # Prefer exact account name matches.
    for r in candidates:
        if str(r.get("account_nm") or "").lower() in names:
            return r
    return candidates[0] if candidates else None

def amount(row):
    if not row:
        return None
    for k in ("thstrm_amount", "thstrm_add_amount"):
        v = clean_num(row.get(k))
        if v is not None:
            return v
    return None

def avg(a,b):
    if a is None or b is None:
        return None
    return (a+b)/2

def div(a,b):
    if a is None or b in (None,0):
        return None
    return a/b

def ratio_pct(a,b):
    v=div(a,b)
    return None if v is None else v*100

def extract_year(rows):
    # DART data is reported in KRW; amounts are kept as published.
    bs = {k: amount(pick(rows, names, "BS")) for k,names in {
        "assets":["자산총계","총자산"],
        "cash":["현금및현금성자산"],
        "receivables":["매출채권","매출채권및기타채권","매출채권및계약자산"],
        "inventory":["재고자산"],
        "ppe":["유형자산"],
        "current_assets":["유동자산"],
        "current_liabilities":["유동부채"],
        "liabilities":["부채총계","총부채"],
        "equity":["자본총계"],
        "short_borrowings":["단기차입금","단기금융부채","유동성장기차입금","유동성사채"],
        "long_borrowings":["장기차입금","장기금융부채","사채"],
    }.items()}
    pl = {k: amount(pick(rows, names, "IS")) for k,names in {
        "revenue":["매출액","영업수익"],
        "gross_profit":["매출총이익"],
        "sga":["판매비와관리비","판매비및관리비"],
        "operating_income":["영업이익","영업이익(손실)"],
        "pretax_income":["법인세비용차감전순이익","세전이익","법인세비용차감전계속사업이익"],
        "net_income":["당기순이익","당기순이익(손실)"],
        "controlling_net_income":["지배기업의 소유주에게 귀속되는 당기순이익","지배기업소유주지분순이익"],
        "interest_expense":["이자비용","금융비용"],
        "depreciation":["감가상각비","감가상각비및무형자산상각비","감가상각비와무형자산상각비"],
    }.items()}
    cf = {k: amount(pick(rows, names, "CF")) for k,names in {
        "cfo":["영업활동현금흐름","영업활동으로 인한 현금흐름"],
        "cfi":["투자활동현금흐름","투자활동으로 인한 현금흐름"],
        "cff":["재무활동현금흐름","재무활동으로 인한 현금흐름"],
        "capex_ppe":["유형자산의 취득","유형자산 취득"],
        "capex_intangible":["무형자산의 취득","무형자산 취득"],
    }.items()}

    # Some cashflow accounts are presented as negative cash outflows.
    capex = sum(abs(x) for x in [cf["capex_ppe"], cf["capex_intangible"]] if x is not None) or None
    debt = sum(x for x in [bs["short_borrowings"], bs["long_borrowings"]] if x is not None) or None
    net_debt = None if debt is None or bs["cash"] is None else debt-bs["cash"]
    ebitda = None if pl["operating_income"] is None else pl["operating_income"] + (pl["depreciation"] or 0)
    fcf = None if cf["cfo"] is None or capex is None else cf["cfo"]-capex

    out = {**bs, **pl, **cf, "capex":capex, "interest_bearing_debt":debt,
           "net_debt":net_debt, "ebitda":ebitda, "fcf":fcf}
    return out

def calculate(current, previous=None, prev_prev=None):
    d=dict(current)
    a=current.get("assets")
    e=current.get("equity")
    ca=current.get("current_assets")
    cl=current.get("current_liabilities")
    rev=current.get("revenue")
    gp=current.get("gross_profit")
    oi=current.get("operating_income")
    ni=current.get("net_income")
    debt=current.get("interest_bearing_debt")
    ebitda=current.get("ebitda")
    d["gross_margin_pct"]=ratio_pct(gp,rev)
    d["operating_margin_pct"]=ratio_pct(oi,rev)
    d["net_margin_pct"]=ratio_pct(ni,rev)
    d["ebitda_margin_pct"]=ratio_pct(ebitda,rev)
    d["current_ratio_pct"]=ratio_pct(ca,cl)
    d["quick_assets"]=None if ca is None or current.get("inventory") is None else ca-current["inventory"]
    d["quick_ratio_pct"]=ratio_pct(d["quick_assets"],cl)
    d["debt_to_equity_pct"]=ratio_pct(current.get("liabilities"),e)
    d["equity_ratio_pct"]=ratio_pct(e,a)
    d["debt_dependency_pct"]=ratio_pct(debt,a)
    d["interest_coverage"]=div(oi, abs(current.get("interest_expense")) if current.get("interest_expense") is not None else None)
    d["net_debt_to_ebitda"]=div(current.get("net_debt"),ebitda)
    if previous:
        d["avg_assets"]=avg(a,previous.get("assets"))
        d["avg_equity"]=avg(e,previous.get("equity"))
        d["avg_inventory"]=avg(current.get("inventory"),previous.get("inventory"))
        d["avg_receivables"]=avg(current.get("receivables"),previous.get("receivables"))
    else:
        d["avg_assets"]=a
        d["avg_equity"]=e
        d["avg_inventory"]=current.get("inventory")
        d["avg_receivables"]=current.get("receivables")
    d["roa_pct"]=ratio_pct(ni,d["avg_assets"])
    d["roe_pct"]=ratio_pct(ni,d["avg_equity"])
    d["asset_turnover"]=div(rev,d["avg_assets"])
    d["dso_days"]=None
    d["dio_days"]=None
    if rev and d["avg_receivables"] is not None:
        d["dso_days"]=365*div(d["avg_receivables"],rev)
    # DIO needs COGS; use revenue - gross profit where available.
    cogs = None if rev is None or gp is None else rev-gp
    if cogs and d["avg_inventory"] is not None:
        d["dio_days"]=365*div(d["avg_inventory"],cogs)
    # DPO requires credit purchases, unavailable reliably from this API mapping.
    d["dpo_days"]=None
    d["ccc_days"]=None if d["dso_days"] is None or d["dio_days"] is None else d["dso_days"]+d["dio_days"]
    if previous and previous.get("revenue") not in (None,0):
        d["revenue_growth_pct"]=ratio_pct(rev-previous["revenue"],previous["revenue"])
    else:
        d["revenue_growth_pct"]=None
    d["cfo_to_net_income"]=div(current.get("cfo"),ni)
    return d

def to_frame(records):
    df=pd.DataFrame(records)
    if df.empty: return df
    cols=["year","period","revenue","gross_profit","operating_income","net_income","assets","cash",
          "receivables","inventory","ppe","liabilities","equity","interest_bearing_debt",
          "cfo","cfi","cff","capex","fcf","net_debt","ebitda","gross_margin_pct",
          "operating_margin_pct","net_margin_pct","ebitda_margin_pct","roa_pct","roe_pct",
          "current_ratio_pct","quick_ratio_pct","debt_to_equity_pct","equity_ratio_pct",
          "debt_dependency_pct","interest_coverage","net_debt_to_ebitda","asset_turnover",
          "dso_days","dio_days","dpo_days","ccc_days","revenue_growth_pct","cfo_to_net_income"]
    return df[[c for c in cols if c in df.columns]]
