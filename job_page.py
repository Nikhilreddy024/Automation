"""
Scrape job detail page (title, description, full content) using Playwright.
"""
from playwright.sync_api import Page


def _get_full_scraped_content(page: Page) -> str:
    """Get whole scraped text content of the page (main or body) for Contract Corp To Corp detection."""
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


def scrape_job_description(page: Page, job_url: str) -> tuple[str, str, str]:
    """
    Navigate to job URL and extract job title, job description, and full scraped text.
    Returns (title, description, full_content).
    """
    try:
        page.goto(job_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_load_state("load", timeout=30_000)

        job_title = ""
        try:
            h1 = page.locator("h1").first
            if h1.count() > 0 and h1.is_visible(timeout=2000):
                job_title = (h1.inner_text(timeout=2000) or "").strip()
        except Exception:
            pass

        selectors = [
            '[class*="jobDescription"]',
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
                        cleaned = text.strip()
                        if len(cleaned) > 100:
                            if "Dice Id:" in cleaned:
                                cleaned = cleaned.split("Dice Id:")[0].strip()
                            full_content = _get_full_scraped_content(page)
                            return (job_title, cleaned, full_content)
            except Exception:
                continue

        try:
            main = page.locator("main").first
            if main.count() > 0:
                text = main.inner_text(timeout=3000).strip()
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
