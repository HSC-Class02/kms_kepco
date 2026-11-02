"""Small, defensive OpenDART client."""
import io
import zipfile
import xml.etree.ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import API_KEY, BASE_URL

TIMEOUT = 60
_SESSION = requests.Session()
_RETRY = Retry(
    total=4,
    connect=4,
    read=3,
    backoff_factor=1.0,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET"]),
)
_SESSION.mount("https://", HTTPAdapter(max_retries=_RETRY))
_SESSION.headers.update({"User-Agent": "kms-kepco-financial-dashboard/1.0"})


def _check_api_key():
    if len(API_KEY) != 40:
        raise RuntimeError(
            "DART_API_KEY가 없거나 형식이 올바르지 않습니다. "
            "GitHub Settings > Secrets and variables > Actions에 "
            "DART_API_KEY 이름으로 40자리 인증키를 등록하세요."
        )


def get_json(endpoint, params):
    _check_api_key()
    query = dict(params)
    query["crtfc_key"] = API_KEY
    response = _SESSION.get(f"{BASE_URL}/{endpoint}.json", params=query, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    status = str(data.get("status", ""))
    if status == "013":
        return {**data, "list": []}
    if status != "000":
        raise RuntimeError(
            f"OpenDART API 오류 ({status}): {data.get('message', '알 수 없는 오류')}"
        )
    return data


def company(corp_code):
    return get_json("company", {"corp_code": corp_code})


def find_corp_code(stock_code):
    """Resolve the six-digit KRX code through the official DART company registry."""
    _check_api_key()
    response = _SESSION.get(
        f"{BASE_URL}/corpCode.xml",
        params={"crtfc_key": API_KEY},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        xml_name = next(
            (name for name in archive.namelist() if name.upper().endswith("CORPCODE.XML")),
            None,
        )
        if not xml_name:
            raise RuntimeError("corpCode.xml ZIP 내부에서 CORPCODE.xml 파일을 찾지 못했습니다.")
        root = ET.fromstring(archive.read(xml_name).decode("utf-8"))
    for item in root.findall("list"):
        if (item.findtext("stock_code") or "").strip() == stock_code:
            corp_code = (item.findtext("corp_code") or "").strip()
            if corp_code:
                return corp_code
    raise RuntimeError(f"종목코드 {stock_code}에 해당하는 DART corp_code를 찾지 못했습니다.")


def disclosures(corp_code, bgn_de, end_de):
    """Read all pages of regular filings in the requested date range."""
    collected = []
    page_no = 1
    while True:
        data = get_json(
            "list",
            {
                "corp_code": corp_code,
                "bgn_de": bgn_de,
                "end_de": end_de,
                "last_reprt_at": "Y",
                "pblntf_ty": "A",
                "sort": "date",
                "sort_mth": "desc",
                "page_no": str(page_no),
                "page_count": "100",
            },
        )
        collected.extend(data.get("list", []))
        total_page = int(data.get("total_page", 1) or 1)
        if page_no >= total_page or not data.get("list"):
            break
        page_no += 1
    return {"status": "000", "list": collected, "total_count": len(collected)}


def financials(corp_code, year, reprt_code, fs_div="CFS"):
    return get_json(
        "fnlttSinglAcntAll",
        {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        },
    )
