"""Repository configuration. Secrets are read only at runtime."""
import os

CORP_STOCK_CODE = "015760"
CORP_NAME = "한국전력공사"
BASE_URL = "https://opendart.fss.or.kr/api"
API_KEY = os.getenv("DART_API_KEY", "").strip()
START_YEAR = 2015  # OpenDART periodic financial-statement API coverage starts in 2015.
REPORT_CODES = {
    "Q1": "11013",
    "H1": "11012",
    "Q3": "11014",
    "FY": "11011",
}
REPORT_NAMES = {
    "Q1": "1분기",
    "H1": "반기",
    "Q3": "3분기",
    "FY": "사업연도",
}
FS_DIV = os.getenv("DART_FS_DIV", "CFS").upper()
