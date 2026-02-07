import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

from helper import API_KEY, RESUME_PATH, load_resume_text, should_apply_to_job

# Load resume text once from file (RESUME_PATH in helper.py)
RESUME_TEXT = load_resume_text(RESUME_PATH.strip()) if RESUME_PATH.strip() else ""
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeoutError
import time
import random

# ------------ Search configuration ------------
BASE_URL = (
    "https://www.dice.com/jobs"
    "?filters.easyApply=true"
    "&filters.postedDate=ONE"
    "&filters.employmentType=CONTRACTS%7CTHIRD_PARTY"
    "&q=%E2%80%9CAI%E2%80%9D+OR+%E2%80%9CMachine+Learning%E2%80%9D+OR+%E2%80%9CData+Scientist%E2%80%9D+OR+%E2%80%9CGEN+AI%E2%80%9D+OR+%E2%80%9CGenerative+AI%E2%80%9D+OR+%E2%80%9CLLM%E2%80%9D+OR+%E2%80%9CLarge+Language+Model%E2%80%9D"
    "&page="
)
# 💡 Tip: Modify this BASE_URL to match your search preferences —
# e.g. change 'postedDate', 'radius', 'employmentType', 'countryCode', 'q' (keywords), or location filters 
# to target specific roles, timeframes, or regions.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )
}

# ------------ Login & automation settings ------------
DICE_LOGIN_URL = "https://www.dice.com/dashboard/login"

# ⚠️ Replace these placeholders with your own credentials before running
USERNAME = ""
PASSWORD = ""
LOCAL_RESUME = r""

# Wait time (in seconds) between job applications to mimic human behavior
PER_JOB_WAIT_SECONDS = 3

# Wait time (in seconds) between loading each result page when scraping job listings
# Increase if pages are slow to load
PAGE_TO_PAGE_WAIT_SECONDS = (2.5, 5.0)  # random range (min, max)

# ------------ File to track already processed jobs ------------
SEEN_FILE = "seen_links.txt"


def load_seen_links(path: str = SEEN_FILE) -> set[str]:
    """Load previously applied job links from file to avoid duplicates."""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def append_seen_link(link: str, path: str = SEEN_FILE) -> None:
    """Append a processed job link to the tracking file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(link + "\n")


# ------------ Scraping logic ------------
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


def scrape_job_listings() -> list[dict]:
    """Scrape all job listings matching the search criteria."""
    jobs: list[dict] = []
    try:
        first_res = requests.get(BASE_URL + "1", headers=HEADERS, timeout=15)
        first_res.raise_for_status()
        first_page = first_res.text
    except Exception:
        first_page = ""

    total_pages = get_total_pages(first_page)
    print(f"Detected {total_pages} pages.")

    for p in range(1, total_pages + 1):
        url = BASE_URL + str(p)
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

        # Pause between pages so they have time to load before next request
        time.sleep(random.uniform(*PAGE_TO_PAGE_WAIT_SECONDS))

    # De-duplicate job links
    seen = set()
    deduped = []
    for j in jobs:
        if j["Job Link"] in seen:
            continue
        seen.add(j["Job Link"])
        deduped.append(j)
    print(f"Found {len(deduped)} unique jobs.")
    return deduped


# ------------ Playwright helpers ------------
def login(page: Page):
    """Automate login flow for Dice using Playwright."""
    page.goto(DICE_LOGIN_URL)
    page.fill('input[name="email"]', USERNAME)
    page.get_by_test_id("sign-in-button").click()

    # Wait for password field
    page.wait_for_selector('input[name="password"]', timeout=60_000)
    page.fill('input[name="password"]', PASSWORD)
    page.get_by_test_id("submit-password").click()

    # Wait until fully logged in
    page.wait_for_load_state("networkidle", timeout=120_000)
    print("Logged in successfully.")


# Dice uses a web component for apply; name and button text can vary by page (search vs job-detail)
APPLY_HOST_SELECTORS = ["apply-button-wc", "dhi-wc-apply-button"]
EASY_APPLY_TEXT = re.compile(r"easy\s*apply|apply\s*now", re.I)


def _find_apply_button_anywhere(page: Page):
    """Find Easy Apply / Apply Now button anywhere on page (pierces shadow DOM)."""
    # Strategy 0: Dice's real Easy Apply is an <a> with data-testid="apply-button" (links to /job-applications/.../wizard)
    for link_loc in [
        page.get_by_test_id("apply-button"),
        page.locator('a[data-testid="apply-button"]'),
        page.locator('a[href*="/job-applications/"][href*="wizard"]').filter(has_text=EASY_APPLY_TEXT),
    ]:
        try:
            if link_loc.count() > 0 and link_loc.first.is_visible(timeout=1500):
                text = link_loc.first.inner_text(timeout=1000).strip()
                if EASY_APPLY_TEXT.search(text) or "easy" in text.lower():
                    return link_loc.first
        except Exception:
            pass
    # Strategy 1: By text — prefer the clickable link/button that contains "Easy Apply", not just the span
    for text_loc in [
        page.get_by_role("link", name=EASY_APPLY_TEXT),
        page.locator('a:has(span:has-text("Easy Apply"))'),
        page.get_by_text("Easy Apply", exact=True),
        page.get_by_text(EASY_APPLY_TEXT),
        page.locator("span:has-text('Easy Apply')"),
        page.locator("[class*='flex']:has-text('Easy Apply')"),
    ]:
        try:
            if text_loc.count() > 0 and text_loc.first.is_visible(timeout=1500):
                return text_loc.first
        except Exception:
            pass
    # Strategy 2: Playwright's role-based locator (pierces shadow DOM)
    btn = page.get_by_role("button", name=EASY_APPLY_TEXT)
    if btn.count() > 0:
        try:
            if btn.first.is_visible(timeout=2000):
                return btn.first
        except Exception:
            pass
    # Strategy 3: Any button whose text matches (pierces shadow DOM)
    for loc in [
        page.locator("button").filter(has_text=EASY_APPLY_TEXT),
        page.locator("button").filter(has_text=re.compile(r"apply", re.I)),
    ]:
        if loc.count() > 0:
            for i in range(loc.count()):
                try:
                    if loc.nth(i).is_visible(timeout=1000):
                        text = loc.nth(i).inner_text(timeout=1000).strip()
                        if EASY_APPLY_TEXT.search(text) or (
                            "apply" in text.lower() and "login" not in text.lower()
                        ):
                            return loc.nth(i)
                except Exception:
                    pass
    return None


def _get_apply_button(page: Page):
    """Find the Easy Apply / Apply Now button (try whole-page first, then web component)."""
    # Job-detail pages may use different structure; try whole-page first
    btn = _find_apply_button_anywhere(page)
    if btn is not None:
        return btn
    # Fallback: look inside known apply web components
    for host_selector in APPLY_HOST_SELECTORS:
        try:
            page.wait_for_selector(host_selector, timeout=5_000)
        except PWTimeoutError:
            continue
        page.wait_for_timeout(600)
        host = page.locator(host_selector)
        for btn_selector in ["button.btn-primary", "button"]:
            buttons = host.locator(btn_selector)
            for i in range(buttons.count()):
                try:
                    text = buttons.nth(i).inner_text(timeout=1500).strip()
                    if EASY_APPLY_TEXT.search(text) or (
                        text and "apply" in text.lower()
                    ):
                        if buttons.nth(i).is_visible(timeout=1000):
                            return buttons.nth(i)
                except Exception:
                    pass
    # Last resort: JS walk shadow roots — find button OR any element with "Easy Apply" text (e.g. span)
    try:
        clicked = page.evaluate(
            """() => {
            function clickApply(root) {
                // First: any element whose text is exactly "Easy Apply" or matches (span, div, button)
                const all = root.querySelectorAll('button, a, span, div');
                for (const el of all) {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (/^easy\\s*apply$/i.test(t) || /^apply\\s*now$/i.test(t)) {
                        el.click();
                        return true;
                    }
                }
                const buttons = root.querySelectorAll('button');
                for (const b of buttons) {
                    const t = (b.innerText || b.textContent || '').trim();
                    if (t && t.toLowerCase().includes('apply') && !t.toLowerCase().includes('login')) {
                        b.click();
                        return true;
                    }
                }
                for (const el of root.querySelectorAll('*')) {
                    if (el.shadowRoot && clickApply(el.shadowRoot)) return true;
                }
                return false;
            }
            return clickApply(document);
        }"""
        )
        if clicked:
            return "js_clicked"
    except Exception:
        pass
    return None


def has_easy_apply(page: Page) -> bool:
    """Check whether a job listing supports Easy Apply."""
    return _get_apply_button(page) is not None


# ------------ Contract Corp To Corp check (apply only when this exists) ------------
CONTRACT_CORP_TO_CORP_TEXT = re.compile(r"contract\s+corp\s+to\s+corp", re.I)


def has_contract_corp_to_corp_in_text(scraped_text: str) -> bool:
    """Return True if the scraped page content contains 'Contract Corp To Corp' (apply only when this exists)."""
    return bool(scraped_text and CONTRACT_CORP_TO_CORP_TEXT.search(scraped_text))


def has_contract_corp_to_corp(page: Page) -> bool:
    """Check whether the job page shows the 'Contract Corp To Corp' div (apply only when this exists)."""
    loc = page.locator(
        'div.font-medium.text-zinc-600.text-xs.leading-none:has-text("Contract Corp To Corp")'
    )
    try:
        return loc.count() > 0 and loc.first.is_visible(timeout=2000)
    except Exception:
        return False


# ------------ Job description scraping ------------
def scrape_job_description(page: Page, job_url: str) -> tuple[str, str, str]:
    """Navigate to job URL and extract job title, job description, and full scraped text. Returns (title, description, full_content)."""
    try:
        page.goto(job_url, wait_until="domcontentloaded", timeout=30_000)
        # Use "load" not "networkidle" — Dice often has ongoing requests so networkidle may timeout
        page.wait_for_load_state("load", timeout=30_000)

        # Extract job title from h1 (e.g. "Lead GenAI Engineer")
        job_title = ""
        try:
            h1 = page.locator("h1").first
            if h1.count() > 0 and h1.is_visible(timeout=2000):
                job_title = (h1.inner_text(timeout=2000) or "").strip()
        except Exception:
            pass

        # Priority selectors - more specific first
        selectors = [
            '[class*="jobDescription"]',  # Catches Dice's dynamic class names
            '[class*="job-description"]',
            '[itemprop="description"]',
            '[data-cy="job-description"]',
            '[data-testid="job-description"]',
            '#jobDescription',
            '.job-description',
            'article [class*="description"]',
            'main [class*="description"]',
        ]
        
        for sel in selectors:
            try:
                elements = page.locator(sel).all()
                for elem in elements:
                    if elem.is_visible():
                        text = elem.inner_text(timeout=3000)
                        # Clean and validate
                        cleaned = text.strip()
                        if len(cleaned) > 100:
                            # Remove common footer noise
                            if "Dice Id:" in cleaned:
                                cleaned = cleaned.split("Dice Id:")[0].strip()
                            full_content = _get_full_scraped_content(page)
                            return (job_title, cleaned, full_content)
            except Exception:
                continue

        # Fallback: Extract from main, but filter out noise
        try:
            main = page.locator("main").first
            if main.count() > 0:
                text = main.inner_text(timeout=3000).strip()
                # Remove metadata footer
                if "Dice Id:" in text:
                    text = text.split("Dice Id:")[0].strip()
                full_content = _get_full_scraped_content(page)
                return (job_title, text, full_content)
        except Exception:
            pass

        full_content = _get_full_scraped_content(page)
        return (job_title, "", full_content)
    except Exception as e:
        print(f"  Failed to scrape {job_url}: {e}")
        return ("", "", "")


def _get_full_scraped_content(page: Page) -> str:
    """Get whole scraped text content of the page (main or body) so 'Contract Corp To Corp' can be detected."""
    try:
        main = page.locator("main").first
        if main.count() > 0:
            return (main.inner_text(timeout=3000) or "").strip()
    except Exception:
        pass
    try:
        return (page.locator("body").inner_text(timeout=3000) or "").strip()
    except Exception:
        return ""


def easy_apply_on_job(page: Page, job_url: str, already_on_page: bool = False) -> bool:
    """Open a job link and complete the Easy Apply process if available."""
    try:
        if not already_on_page:
            page.goto(job_url, wait_until="domcontentloaded")
            # Use "load" not "networkidle" — Dice often has ongoing requests so networkidle never fires
            page.wait_for_load_state("load", timeout=15_000)
            # Give the page 5 seconds to finish rendering (JS, dynamic content, Easy Apply widget)
            page.wait_for_timeout(5000)

        # Apply only when "Contract Corp To Corp" is present on the page (exact div text)
        if not has_contract_corp_to_corp(page):
            print("  Skipping (Contract Corp To Corp not found on page):", job_url)
            return False

        # Easy Apply button can appear late (JS/widget); wait for it with a generous timeout
        easy_btn = None
        easy_apply_wait_seconds = 25
        for _ in range(easy_apply_wait_seconds):
            easy_btn = _get_apply_button(page)
            if easy_btn is not None:
                break
            page.wait_for_timeout(1000)
        if not easy_btn:
            print("  Skipping (Easy Apply button did not appear in %ds):" % easy_apply_wait_seconds, job_url)
            return False

        print("  Clicking Easy apply on:", job_url)
        if easy_btn != "js_clicked":
            try:
                easy_btn.scroll_into_view_if_needed(timeout=5000)
                page.wait_for_timeout(500)
                easy_btn.click(force=True)
            except Exception:
                # Fallback: click via shadow root (Dice often uses shadow DOM)
                for host_selector in APPLY_HOST_SELECTORS:
                    host = page.locator(host_selector)
                    if host.count() > 0:
                        page.evaluate(
                            """(selector) => {
                                const el = document.querySelector(selector);
                                if (el && el.shadowRoot) {
                                    const btn = el.shadowRoot.querySelector('button');
                                    if (btn) btn.click();
                                }
                            }""",
                            host_selector,
                        )
                        break
                page.wait_for_timeout(1000)
        else:
            page.wait_for_timeout(1200)

        # Verify the application flow actually opened (modal/Next/Submit). If not, the click likely failed.
        apply_form_opened = False
        for _ in range(12):  # up to ~12 seconds
            page.wait_for_timeout(1000)
            for check in [
                page.get_by_role("button", name="Next"),
                page.get_by_role("button", name="Submit"),
                page.locator('button:has(span:text-is("Next"))'),
                page.locator('button:has(span:text-is("Submit"))'),
                page.locator('button.file-remove'),
            ]:
                if check.count() > 0 and check.first.is_visible(timeout=500):
                    apply_form_opened = True
                    break
            if apply_form_opened:
                break
        if not apply_form_opened:
            print("  Easy Apply clicked but application form did not open; skipping.")
            return False

        # After Easy Apply, first step often has a "Next" button — click it to reach resume step
        try:
            page.wait_for_timeout(2000)  # allow step/modal to settle
            for next_loc in [
                page.get_by_role("button", name="Next"),
                page.locator('button[type="submit"]:has(span:has-text("Next"))'),
                page.locator('button:has(span:text-is("Next"))'),
            ]:
                if next_loc.count() > 0 and next_loc.first.is_visible(timeout=12_000):
                    next_loc.first.click()
                    page.wait_for_timeout(2000)
                    break
        except Exception:
            pass

        # After Next, a step page may show Submit — click it to proceed (or finish)
        try:
            page.wait_for_timeout(4000)  # allow time for next step to load
            for submit_loc in [
                page.get_by_role("button", name="Submit"),
                page.locator('button[type="button"]:has(span:has-text("Submit"))'),
                page.locator('button:has(span:text-is("Submit"))'),
            ]:
                if submit_loc.count() > 0 and submit_loc.first.is_visible(timeout=15_000):
                    submit_loc.first.click()
                    page.wait_for_timeout(2000)
                    print("  Submitted ✔")
                    return True
        except Exception:
            pass

        # Replace resume (only if this job's flow has file upload; some go straight to Next → Submit)
        try:
            page.wait_for_selector('button.file-remove', timeout=12_000)
        except PWTimeoutError:
            # No resume step — try to complete with Next/Submit if visible
            try:
                for submit_loc in [
                    page.get_by_role("button", name="Submit"),
                    page.locator('button[type="button"]:has(span:has-text("Submit"))'),
                    page.locator('button:has(span:text-is("Submit"))'),
                ]:
                    if submit_loc.count() > 0 and submit_loc.first.is_visible(timeout=5000):
                        submit_loc.first.click()
                        page.wait_for_timeout(2000)
                        print("  Submitted ✔ (no resume step)")
                        return True
            except Exception:
                pass
            print("  No resume step and no Submit found; skipping.")
            return False

        page.click('button.file-remove:has-text("Replace")')
        page.wait_for_selector('input#fsp-fileUpload', timeout=10_000)
        page.set_input_files('input#fsp-fileUpload', LOCAL_RESUME)
        page.wait_for_timeout(1200)

        # Upload the file
        page.wait_for_selector('span[data-e2e="upload"]', timeout=10_000)
        page.click('span[data-e2e="upload"]')
        page.wait_for_timeout(1200)

        # Navigate through steps until submission
        for _ in range(6):
            submit_btn = page.locator('button.btn-next:has-text("Submit")')
            if submit_btn.is_visible():
                submit_btn.click()
                page.wait_for_timeout(1200)
                print("  Submitted ✔")
                return True
            next_btn = page.locator('button.btn-next')
            if next_btn.is_visible():
                next_btn.click()
                page.wait_for_timeout(1000)
            else:
                break

        print("  Could not reach Submit step; skipping.")
        return False

    except PWTimeoutError as te:
        print("  Timeout:", te)
        return False
    except Exception as e:
        print("  Error:", e)
        return False


# ------------ Main orchestrator ------------
def main():
    """Entry point for the automation."""
    jobs = scrape_job_listings()
    links = [j["Job Link"] for j in jobs]

    seen_links = load_seen_links()
    new_links = [lnk for lnk in links if lnk not in seen_links]
    print(f"{len(new_links)} new links to process; {len(seen_links)} already seen.")

    if not new_links:
        print("Nothing new. Exiting.")
        return

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()

        login(page)

        submitted = 0
        for i, link in enumerate(new_links, start=1):
            print(f"\n[{i}/{len(new_links)}] {link}")

            # Scrape job title, description, and full page content
            job_title, job_description, full_scraped_text = scrape_job_description(page, link)
            if not job_description:
                print("  Skipping (could not extract job description)")
                append_seen_link(link)
                seen_links.add(link)
                time.sleep(PER_JOB_WAIT_SECONDS)
                continue

            # 1) Apply only when "Contract Corp To Corp" exists in the whole scraped content
            if not has_contract_corp_to_corp_in_text(full_scraped_text or ""):
                print("  Skipping (Contract Corp To Corp not in scraped content)")
                append_seen_link(link)
                seen_links.add(link)
                time.sleep(PER_JOB_WAIT_SECONDS)
                continue

            # 2) Single API evaluation: seniority + resume match → YES/NO
            if not should_apply_to_job(API_KEY, RESUME_TEXT, job_title or "", job_description):
                print("  Skipping (API decision: NO)")
                append_seen_link(link)
                seen_links.add(link)
                time.sleep(PER_JOB_WAIT_SECONDS)
                continue

            # API said YES: proceed with application (already on job page)
            applied = easy_apply_on_job(page, link, already_on_page=True)

            append_seen_link(link)
            seen_links.add(link)

            if applied:
                submitted += 1

            time.sleep(PER_JOB_WAIT_SECONDS)

        print(f"\nDone. Submitted: {submitted} / Attempted: {len(new_links)}")
        page.wait_for_timeout(2000)
        browser.close()


if __name__ == "__main__":
    main()
