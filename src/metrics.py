"""Financial-statement extraction and ratio calculations for KEPCO.

Amounts remain in KRW in the data files. The dashboard converts monetary amounts
to KRW 100 million (억원) only for display.
"""
import re
import pandas as pd


FLOW_KEYS = (
    "revenue", "gross_profit", "cost_of_sales", "sga", "operating_income",
    "pretax_income", "net_income", "controlling_net_income", "interest_expense",
    "depreciation", "cfo", "cfi", "cff", "capex_ppe", "capex_intangible",
)
BS_KEYS = (
    "assets", "cash", "receivables", "inventory", "ppe", "current_assets",
    "current_liabilities", "liabilities", "equity", "payables",
    "short_borrowings", "long_borrowings",
)


def clean_num(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace(" ", "")
    if not text or text in {"-", "–", "－", "N/A"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return -number if negative else number


def _norm(value):
    return re.sub(r"[\s·ㆍ()（）\[\]{}]", "", str(value or "")).lower()


def pick(rows, names, sj_div=None):
    """Prefer exact XBRL labels, then the most specific substring match."""
    allowed = {sj_div} if isinstance(sj_div, str) else set(sj_div or [])
    candidates = [
        row for row in rows
        if not allowed or row.get("sj_div") in allowed
    ]
    aliases = [_norm(name) for name in names]
    for alias in aliases:
        for row in candidates:
            if _norm(row.get("account_nm")) == alias:
                return row
    for alias in sorted(aliases, key=len, reverse=True):
        for row in candidates:
            if alias and alias in _norm(row.get("account_nm")):
                return row
    return None


def amount(row, cumulative=False):
    if not row:
        return None
    keys = ("thstrm_add_amount", "thstrm_amount") if cumulative else ("thstrm_amount",)
    for key in keys:
        value = clean_num(row.get(key))
        if value is not None:
            return value
    return None


def _value(rows, labels, statement, cumulative=False):
    row = pick(rows, labels, statement)
    return amount(row, cumulative=cumulative)


def _sum_available(values):
    valid = [value for value in values if value is not None]
    return sum(valid) if valid else None


def _sum_account_rows(rows, keywords, excluded=()):
    matches = []
    for row in rows:
        if row.get("sj_div") != "BS":
            continue
        name = _norm(row.get("account_nm"))
        if any(_norm(word) in name for word in keywords) and not any(
            _norm(word) in name for word in excluded
        ):
            value = amount(row)
            if value is not None:
                matches.append(value)
    return _sum_available(matches)


def extract_report(rows, year, period):
    """Extract one DART report. BS is a point-in-time value; IS/CF are YTD flows."""
    bs = {
        "assets": _value(rows, ["자산총계", "총자산"], "BS"),
        "cash": _value(rows, ["현금및현금성자산", "현금및현금성자산및단기금융상품"], "BS"),
        "receivables": _value(
            rows, ["매출채권및기타채권", "매출채권및계약자산", "매출채권"], "BS"
        ),
        "inventory": _value(rows, ["재고자산"], "BS"),
        "ppe": _value(rows, ["유형자산"], "BS"),
        "current_assets": _value(rows, ["유동자산"], "BS"),
        "current_liabilities": _value(rows, ["유동부채"], "BS"),
        "liabilities": _value(rows, ["부채총계", "총부채"], "BS"),
        "equity": _value(rows, ["자본총계"], "BS"),
        "payables": _value(
            rows, ["매입채무및기타채무", "매입채무", "미지급금및기타채무"], "BS"
        ),
        "short_borrowings": _sum_account_rows(
            rows,
            ["단기차입금", "유동성장기차입금", "유동성사채", "유동성장기부채",
             "단기리스부채", "유동성리스부채"],
        ),
        "long_borrowings": _sum_account_rows(
            rows,
            ["장기차입금", "장기금융부채", "비유동사채", "비유동리스부채"],
            excluded=["유동성", "단기"],
        ),
    }

    # Income statement amounts use the accumulated (YTD) value for interim reports.
    income_statements = ("IS", "CIS")
    pl = {
        "revenue": _value(
            rows, ["매출액", "수익(매출액)", "영업수익", "영업수익(매출액)"],
            income_statements, cumulative=True
        ),
        "gross_profit": _value(
            rows, ["매출총이익", "매출총이익(손실)"],
            income_statements, cumulative=True
        ),
        "cost_of_sales": _value(
            rows, ["매출원가", "영업비용"], income_statements, cumulative=True
        ),
        "sga": _value(
            rows, ["판매비와관리비", "판매비및관리비", "판매비와관리비(손실)"],
            income_statements, cumulative=True
        ),
        "operating_income": _value(
            rows, ["영업이익(손실)", "영업이익", "영업손실"],
            income_statements, cumulative=True
        ),
        "pretax_income": _value(
            rows,
            ["법인세비용차감전순이익(손실)", "법인세비용차감전순이익",
             "세전이익", "법인세비용차감전계속사업이익"],
            income_statements, cumulative=True
        ),
        "net_income": _value(
            rows, ["당기순이익(손실)", "당기순이익", "당기순손실"],
            income_statements, cumulative=True
        ),
        "controlling_net_income": _value(
            rows,
            ["지배기업의 소유주에게 귀속되는 당기순이익(손실)",
             "지배기업의 소유주에게 귀속되는 당기순이익",
             "지배기업소유주지분순이익"],
            income_statements, cumulative=True
        ),
        "interest_expense": _value(
            rows, ["이자비용", "금융원가"], income_statements, cumulative=True
        ),
        "depreciation": _value(
            rows,
            ["감가상각비및무형자산상각비", "감가상각비와무형자산상각비", "감가상각비"],
            ("CF",) + income_statements, cumulative=True
        ),
    }

    cf = {
        "cfo": _value(
            rows, ["영업활동현금흐름", "영업활동으로 인한 현금흐름",
                   "영업활동으로부터의 순현금흐름"], "CF", cumulative=True
        ),
        "cfi": _value(
            rows, ["투자활동현금흐름", "투자활동으로 인한 현금흐름",
                   "투자활동으로부터의 순현금흐름"], "CF", cumulative=True
        ),
        "cff": _value(
            rows, ["재무활동현금흐름", "재무활동으로 인한 현금흐름",
                   "재무활동으로부터의 순현금흐름"], "CF", cumulative=True
        ),
        "capex_ppe": _value(
            rows, ["유형자산의 취득", "유형자산 취득"], "CF", cumulative=True
        ),
        "capex_intangible": _value(
            rows, ["무형자산의 취득", "무형자산 취득"], "CF", cumulative=True
        ),
    }

    if pl["gross_profit"] is None and pl["revenue"] is not None and pl["cost_of_sales"] is not None:
        pl["gross_profit"] = pl["revenue"] - pl["cost_of_sales"]

    capex_items = [cf["capex_ppe"], cf["capex_intangible"]]
    capex = _sum_available([abs(value) for value in capex_items if value is not None])
    debt = _sum_available([bs["short_borrowings"], bs["long_borrowings"]])
    net_debt = None if debt is None or bs["cash"] is None else debt - bs["cash"]
    ebitda = (
        None if pl["operating_income"] is None
        else pl["operating_income"] + (pl["depreciation"] or 0)
    )
    fcf = None if cf["cfo"] is None or capex is None else cf["cfo"] - capex

    return {
        **bs, **pl, **cf,
        "year": int(year),
        "period": period,
        "period_label": {
            "Q1": "1분기", "H1": "반기", "Q3": "3분기", "FY": "연간"
        }.get(period, period),
        "capex": capex,
        "interest_bearing_debt": debt,
        "net_debt": net_debt,
        "ebitda": ebitda,
        "fcf": fcf,
    }


def _div(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _ratio_pct(numerator, denominator):
    value = _div(numerator, denominator)
    return None if value is None else value * 100


def _average(current, previous, key):
    a = current.get(key)
    b = previous.get(key) if previous else None
    if a is None:
        return b
    if b is None:
        return a
    return (a + b) / 2


def calculate(current, previous=None, period_days=365, prior_comparable=None):
    """Calculate ratios using matched statement periods and average balance-sheet values."""
    data = dict(current)
    revenue = data.get("revenue")
    gross_profit = data.get("gross_profit")
    operating_income = data.get("operating_income")
    net_income = data.get("net_income")
    assets_avg = _average(data, previous, "assets")
    equity_avg = _average(data, previous, "equity")
    inventory_avg = _average(data, previous, "inventory")
    receivables_avg = _average(data, previous, "receivables")
    payables_avg = _average(data, previous, "payables")
    annualizer = 365 / period_days if period_days else 1

    data["gross_margin_pct"] = _ratio_pct(gross_profit, revenue)
    data["operating_margin_pct"] = _ratio_pct(operating_income, revenue)
    data["net_margin_pct"] = _ratio_pct(net_income, revenue)
    data["ebitda_margin_pct"] = _ratio_pct(data.get("ebitda"), revenue)
    data["current_ratio_pct"] = _ratio_pct(data.get("current_assets"), data.get("current_liabilities"))
    quick_assets = (
        None if data.get("current_assets") is None or data.get("inventory") is None
        else data["current_assets"] - data["inventory"]
    )
    data["quick_assets"] = quick_assets
    data["quick_ratio_pct"] = _ratio_pct(quick_assets, data.get("current_liabilities"))
    data["debt_to_equity_pct"] = _ratio_pct(data.get("liabilities"), data.get("equity"))
    data["equity_ratio_pct"] = _ratio_pct(data.get("equity"), data.get("assets"))
    data["debt_dependency_pct"] = _ratio_pct(data.get("interest_bearing_debt"), data.get("assets"))
    interest = data.get("interest_expense")
    data["interest_coverage"] = _div(operating_income, abs(interest) if interest is not None else None)
    data["net_debt_to_ebitda"] = _div(data.get("net_debt"), data.get("ebitda"))

    data["avg_assets"] = assets_avg
    data["avg_equity"] = equity_avg
    data["avg_inventory"] = inventory_avg
    data["avg_receivables"] = receivables_avg
    data["avg_payables"] = payables_avg
    data["roa_pct"] = None if _ratio_pct(net_income, assets_avg) is None else _ratio_pct(net_income, assets_avg) * annualizer
    data["roe_pct"] = None if _ratio_pct(net_income, equity_avg) is None else _ratio_pct(net_income, equity_avg) * annualizer
    data["asset_turnover"] = None if _div(revenue, assets_avg) is None else _div(revenue, assets_avg) * annualizer

    days = period_days or 365
    cogs = data.get("cost_of_sales")
    data["dso_days"] = None if _div(receivables_avg, revenue) is None else days * _div(receivables_avg, revenue)
    data["dio_days"] = None if _div(inventory_avg, cogs) is None else days * _div(inventory_avg, cogs)
    data["dpo_days"] = None if _div(payables_avg, cogs) is None else days * _div(payables_avg, cogs)
    if all(data.get(key) is not None for key in ("dso_days", "dio_days", "dpo_days")):
        data["ccc_days"] = data["dso_days"] + data["dio_days"] - data["dpo_days"]
    else:
        data["ccc_days"] = None

    comparable_revenue = prior_comparable.get("revenue") if prior_comparable else None
    data["revenue_growth_pct"] = (
        _ratio_pct(revenue - comparable_revenue, comparable_revenue)
        if revenue is not None and comparable_revenue not in (None, 0) else None
    )
    data["cfo_to_net_income"] = _div(data.get("cfo"), net_income)
    return data


def to_frame(records):
    df = pd.DataFrame(records)
    if df.empty:
        return df
    columns = [
        "year", "period", "period_label",
        "revenue", "gross_profit", "cost_of_sales", "sga", "operating_income",
        "pretax_income", "net_income", "controlling_net_income",
        "assets", "current_assets", "cash", "receivables", "inventory", "ppe",
        "current_liabilities", "payables", "liabilities", "equity",
        "interest_bearing_debt", "net_debt",
        "cfo", "cfi", "cff", "capex", "fcf", "ebitda",
        "gross_margin_pct", "operating_margin_pct", "net_margin_pct",
        "ebitda_margin_pct", "roa_pct", "roe_pct", "current_ratio_pct",
        "quick_ratio_pct", "debt_to_equity_pct", "equity_ratio_pct",
        "debt_dependency_pct", "interest_coverage", "net_debt_to_ebitda",
        "asset_turnover", "dso_days", "dio_days", "dpo_days", "ccc_days",
        "revenue_growth_pct", "cfo_to_net_income",
    ]
    return df[[column for column in columns if column in df.columns]]
