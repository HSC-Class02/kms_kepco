import os

CORP_STOCK_CODE = "015760"  # 한국전력공사
CORP_NAME = "한국전력공사"
BASE_URL = "https://opendart.fss.or.kr/api"
API_KEY = os.getenv("DART_API_KEY", "")
REPORT_CODES = {
    "Q1": "11013",
    "H1": "11012",
    "Q3": "11014",
    "FY": "11011",
}
YEARS_BACK = 5

if not API_KEY:
    raise RuntimeError("DART_API_KEY 환경변수를 설정하세요.")
