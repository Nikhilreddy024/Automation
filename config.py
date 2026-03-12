"""
Dice automation configuration.
Central place for URLs, credentials, timeouts, and selectors.
"""
import re

# ------------ Search configuration ------------
# Each URL is run once in sequence (no merging). Add or remove entries as needed.
_BASE = (
    "https://www.dice.com/jobs"
    "?filters.easyApply=true"
    "&filters.postedDate=ONE"
    "&filters.employmentType=CONTRACTS%7CTHIRD_PARTY"
)
BASE_URLS = [
    _BASE + "&q=Gen+AI&page=",
    _BASE + "&q=AI&page=",
    _BASE + "&q=Machine+Learning&page=",
    _BASE + "&q=Data+Scientist&page=",
    _BASE + "&q=%E2%80%9CAI%E2%80%9D+OR+%E2%80%9CMachine+Learning%E2%80%9D+OR+%E2%80%9CData+Scientist%E2%80%9D+OR+%E2%80%9CGEN+AI%E2%80%9D+OR+%E2%80%9CGenerative+AI%E2%80%9D+OR+%E2%80%9CLLM%E2%80%9D+OR+%E2%80%9CLarge+Language+Model%E2%80%9D&page=",
]



HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

# ------------ Login & automation ------------
DICE_LOGIN_URL = "https://www.dice.com/dashboard/login"
USERNAME = "Nikhilreddyx86@gmail.com"
PASSWORD = "Nikhil@86"
LOCAL_RESUME = r"C:\Users\nikhi\Desktop\realistic\Nikhil_R_Resume.docx"

PER_JOB_WAIT_SECONDS = 3
PAGE_TO_PAGE_WAIT_SECONDS = (2.5, 5.0)  # random range (min, max)
SEEN_FILE = "seen_links.txt"

# ------------ Apply button & Contract Corp To Corp ------------
APPLY_HOST_SELECTORS = ["apply-button-wc", "dhi-wc-apply-button"]
EASY_APPLY_TEXT = re.compile(r"easy\s*apply|apply\s*now", re.I)
CONTRACT_CORP_TO_CORP_TEXT = re.compile(r"contract\s+corp\s+to\s+corp", re.I)
