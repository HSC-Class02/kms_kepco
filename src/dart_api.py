import io
import json
import zipfile
from pathlib import Path
import requests
from .config import API_KEY, BASE_URL

TIMEOUT = 60

def get_json(endpoint, params):
    p = dict(params)
    p["crtfc_key"] = API_KEY
    r = requests.get(f"{BASE_URL}/{endpoint}.json", params=p, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if str(data.get("status")) != "000":
        raise RuntimeError(f"DART API error {data.get('status')}: {data.get('message')}")
    return data

def company(corp_code):
    return get_json("company", {"corp_code": corp_code})

def find_corp_code(stock_code):
    # DART's corpCode.xml is a ZIP containing CORPCODE.xml.
    url = f"{BASE_URL}/corpCode.xml"
    r = requests.get(url, params={"crtfc_key": API_KEY}, timeout=TIMEOUT)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        xml = z.read("CORPCODE.xml").decode("utf-8")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    for item in root.findall("list"):
        if (item.findtext("stock_code") or "").strip() == stock_code:
            return (item.findtext("corp_code") or "").strip()
    raise RuntimeError(f"stock_code={stock_code}에 해당하는 corp_code를 찾지 못했습니다.")

def disclosures(corp_code, bgn_de, end_de):
    params = {
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "last_reprt_at": "Y",
        "pblntf_ty": "A",
        "sort": "date",
        "sort_mth": "desc",
        "page_no": "1",
        "page_count": "100",
    }
    return get_json("list", params)

def financials(corp_code, year, reprt_code="11011", fs_div="CFS"):
    params = {
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": reprt_code,
        "fs_div": fs_div,
    }
    return get_json("fnlttSinglAcntAll", params)
