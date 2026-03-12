"""
Scrape Dice job listing pages (HTTP + BeautifulSoup).
Returns a list of job dicts with Job Title and Job Link.
"""
import random
import time

import requests
from bs4 import BeautifulSoup

from config import BASE_URLS, HEADERS, PAGE_TO_PAGE_WAIT_SECONDS


def get_total_pages(html_text: str) -> int:
    """Extract total page count from the first result page."""
    soup = BeautifulSoup(html_text, "html.parser")
    sec = soup.find("section", {"aria-label": lambda lbl: lbl and "Page" in lbl})
    if not sec:
        return 1
    label = sec.get("aria-label", "")
    try:
        _, total = [int(n) for n in label.replace("Page", "").replace("of", "").split()]
    except ValueError:
        total = 1
    return total


def scrape_job_listings(base_url: str) -> list[dict]:
    """Scrape all job listings for one search URL (base_url must end with '&page=')."""
    jobs: list[dict] = []
    try:
        first_res = requests.get(base_url + "1", headers=HEADERS, timeout=15)
        first_res.raise_for_status()
        first_page = first_res.text
    except Exception:
        first_page = ""

    total_pages = get_total_pages(first_page)
    print(f"Detected {total_pages} pages.")

    for p in range(1, total_pages + 1):
        url = base_url + str(p)
        print(f"Scraping job list (page {p}/{total_pages})...")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"  ⚠️ Failed to load page {p} (status {resp.status_code})")
                continue
        except Exception as e:
            print(f"  ⚠️ Failed to load page {p}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", {"data-testid": "job-search-job-detail-link"})
        for a in links:
            title = a.get_text(strip=True)
            href = a.get("href")
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.dice.com" + href
            jobs.append({"Job Title": title, "Job Link": href})

        time.sleep(random.uniform(*PAGE_TO_PAGE_WAIT_SECONDS))

    seen = set()
    deduped = []
    for j in jobs:
        if j["Job Link"] in seen:
            continue
        seen.add(j["Job Link"])
        deduped.append(j)
    print(f"Found {len(deduped)} unique jobs.")
    return deduped
