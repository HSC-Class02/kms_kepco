"""Collect KEPCO financial statements, calculate ratios, and render the dashboard."""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .config import (
    API_KEY, CORP_NAME, CORP_STOCK_CODE, FS_DIV, REPORT_CODES, START_YEAR,
)
from .dart_api import company, disclosures, financials, find_corp_code
from .metrics import FLOW_KEYS, calculate, extract_report, to_frame
from .dashboard import generate_dashboard

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
DASH = ROOT / "dashboard"
for folder in (RAW, PROC, DASH):
    folder.mkdir(parents=True, exist_ok=True)


def _write_json(path, payload):
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def _period_days(year, period):
    starts = {
        "Q1": dt.date(year, 1, 1),
        "Q2": dt.date(year, 4, 1),
        "Q3": dt.date(year, 7, 1),
        "Q4": dt.date(year, 10, 1),
        "H1": dt.date(year, 1, 1),
        "FY": dt.date(year, 1, 1),
    }
    ends = {
        "Q1": dt.date(year, 4, 1),
        "Q2": dt.date(year, 7, 1),
        "Q3": dt.date(year, 10, 1),
        "Q4": dt.date(year + 1, 1, 1),
        "H1": dt.date(year, 7, 1),
        "FY": dt.date(year + 1, 1, 1),
    }
    return (ends[period] - starts[period]).days


def _make_standalone_quarter(current, previous_cumulative, year, quarter):
    """Convert YTD IS/CF figures into a standalone quarter; retain closing BS balances."""
    row = dict(current)
    row["year"] = year
    row["period"] = quarter
    row["period_label"] = {
        "Q1": "1분기", "Q2": "2분기", "Q3": "3분기", "Q4": "4분기"
    }[quarter]
    if previous_cumulative is not None:
        for key in FLOW_KEYS:
            current_value = current.get(key)
            previous_value = previous_cumulative.get(key)
            if current_value is None or previous_value is None:
                row[key] = None
            else:
                row[key] = current_value - previous_value

    capex_values = [row.get("capex_ppe"), row.get("capex_intangible")]
    capex_values = [abs(value) for value in capex_values if value is not None]
    row["capex"] = sum(capex_values) if capex_values else None

    debt_values = [row.get("short_borrowings"), row.get("long_borrowings")]
    debt_values = [value for value in debt_values if value is not None]
    row["interest_bearing_debt"] = sum(debt_values) if debt_values else None
    row["net_debt"] = (
        None if row["interest_bearing_debt"] is None or row.get("cash") is None
        else row["interest_bearing_debt"] - row["cash"]
    )
    row["ebitda"] = (
        None if row.get("operating_income") is None
        else row["operating_income"] + (row.get("depreciation") or 0)
    )
    row["fcf"] = (
        None if row.get("cfo") is None or row.get("capex") is None
        else row["cfo"] - row["capex"]
    )
    return row


def _index_by_year(records):
    return {int(row["year"]): row for row in records}


def main():
    if len(API_KEY) != 40:
        raise RuntimeError(
            "DART_API_KEY가 없거나 형식이 올바르지 않습니다. "
            "저장소 Secrets에 DART_API_KEY를 40자리 인증키로 등록하세요."
        )
    if FS_DIV not in {"CFS", "OFS"}:
        raise RuntimeError("DART_FS_DIV는 CFS 또는 OFS여야 합니다.")

    now = dt.datetime.now(ZoneInfo("Asia/Seoul"))
    today = now.date()
    corp_code = find_corp_code(CORP_STOCK_CODE)
    company_info = company(corp_code)
    _write_json(PROC / "company.json", {
        "corp_name": CORP_NAME,
        "stock_code": CORP_STOCK_CODE,
        "corp_code": corp_code,
        "fs_div": FS_DIV,
        "company": company_info,
        "updated_at": now.isoformat(),
    })

    disclosures_data = disclosures(
        corp_code,
        f"{START_YEAR}0101",
        today.strftime("%Y%m%d"),
    )
    _write_json(RAW / "disclosures.json", disclosures_data)

    cumulative = {}
    request_count = 0
    available_count = 0
    for year in range(START_YEAR, today.year + 1):
        for period, report_code in REPORT_CODES.items():
            request_count += 1
            try:
                payload = financials(corp_code, year, report_code, FS_DIV)
                _write_json(RAW / f"financials_{year}_{period}.json", payload)
                rows = payload.get("list", [])
                if not rows:
                    print(f"[INFO] {year} {period}: DART 보고서 데이터 없음")
                    continue
                cumulative[(year, period)] = extract_report(rows, year, period)
                available_count += 1
            except Exception as error:
                print(f"[WARN] {year} {period}: {error}")

    if not cumulative:
        raise RuntimeError(
            "수집된 재무제표가 없습니다. DART_API_KEY, 종목코드, API 사용 상태를 확인하세요."
        )

    # Annual table: one row per available business year.
    annual_raw = [
        cumulative[(year, "FY")]
        for year in range(START_YEAR, today.year + 1)
        if (year, "FY") in cumulative
    ]
    annual_by_year = _index_by_year(annual_raw)
    annual = []
    for raw in annual_raw:
        year = int(raw["year"])
        previous = annual_by_year.get(year - 1)
        annual.append(calculate(
            raw,
            previous=previous,
            period_days=_period_days(year, "FY"),
            prior_comparable=previous,
        ))

    # Half-year table: H1 report figures are year-to-date, not standalone Q2 figures.
    half_raw = [
        cumulative[(year, "H1")]
        for year in range(START_YEAR, today.year + 1)
        if (year, "H1") in cumulative
    ]
    half_by_year = _index_by_year(half_raw)
    half_year = []
    for raw in half_raw:
        year = int(raw["year"])
        half_year.append(calculate(
            raw,
            previous=annual_by_year.get(year - 1),
            period_days=_period_days(year, "H1"),
            prior_comparable=half_by_year.get(year - 1),
        ))

    # Standalone quarterly table. Q2/Q3/Q4 are derived from successive YTD reports.
    quarter_raw = []
    prior_quarter_balance = None
    for year in range(START_YEAR, today.year + 1):
        specifications = [
            ("Q1", "Q1", None),
            ("Q2", "H1", "Q1"),
            ("Q3", "Q3", "H1"),
            ("Q4", "FY", "Q3"),
        ]
        for quarter, source_period, prior_period in specifications:
            source = cumulative.get((year, source_period))
            if source is None:
                continue
            previous_cumulative = (
                cumulative.get((year, prior_period)) if prior_period else None
            )
            if prior_period and previous_cumulative is None:
                print(
                    f"[INFO] {year} {quarter}: 선행 누적 보고서({prior_period})가 없어 "
                    "독립 분기 산출을 건너뜁니다."
                )
                continue
            row = _make_standalone_quarter(
                source, previous_cumulative, year, quarter
            )
            quarter_raw.append(row)

    quarter_raw.sort(key=lambda row: (int(row["year"]), row["period"]))
    quarter_lookup = {
        (int(row["year"]), row["period"]): row for row in quarter_raw
    }
    quarterly = []
    for row in quarter_raw:
        year = int(row["year"])
        quarter = row["period"]
        previous = quarterly[-1] if quarterly else annual_by_year.get(year - 1)
        prior_comparable = quarter_lookup.get((year - 1, quarter))
        quarterly.append(calculate(
            row,
            previous=previous,
            period_days=_period_days(year, quarter),
            prior_comparable=prior_comparable,
        ))

    # Save both separated period files and the combined dataset used by analysts.
    frames = {
        "annual": to_frame(annual),
        "half_year": to_frame(half_year),
        "quarterly": to_frame(quarterly),
    }
    all_records = annual + half_year + quarterly
    for name, frame in frames.items():
        frame.to_csv(
            PROC / f"financials_{name}.csv",
            index=False,
            encoding="utf-8-sig",
        )
        _write_json(PROC / f"financials_{name}.json", frame.where(pd.notna(frame), None).to_dict(orient="records"))

    combined = to_frame(all_records)
    combined.to_csv(PROC / "financials.csv", index=False, encoding="utf-8-sig")
    _write_json(
        PROC / "financials.json",
        combined.astype(object).where(pd.notna(combined), None).to_dict(orient="records"),
    )

    metadata = {
        "corp_name": CORP_NAME,
        "stock_code": CORP_STOCK_CODE,
        "fs_div": FS_DIV,
        "start_year": START_YEAR,
        "end_year": today.year,
        "updated_at": now.isoformat(timespec="minutes"),
        "requested_reports": request_count,
        "available_reports": available_count,
        "annual_records": len(annual),
        "half_year_records": len(half_year),
        "quarterly_records": len(quarterly),
        "data_source": "OpenDART fnlttSinglAcntAll",
        "quarterly_method": "standalone IS/CF values derived from sequential YTD report differences",
    }
    _write_json(PROC / "update_metadata.json", metadata)
    generate_dashboard(
        annual,
        half_year,
        quarterly,
        disclosures_data,
        metadata,
        DASH / "index.html",
    )
    print(
        f"[DONE] {CORP_NAME}: annual={len(annual)}, "
        f"half-year={len(half_year)}, quarterly={len(quarterly)}"
    )


if __name__ == "__main__":
    main()
