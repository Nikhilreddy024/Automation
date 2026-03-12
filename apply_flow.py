"""
Dice login and Easy Apply flow (Playwright).
Handles login, finding Apply button, Contract Corp To Corp check, resume replace, and submit.
"""
import os
import re
import random

from playwright.sync_api import Page, TimeoutError as PWTimeoutError

try:
    from playwright._impl._errors import TargetClosedError
except ImportError:
    TargetClosedError = type("TargetClosedError", (Exception,), {})  # fallback if impl changes

from config import (
    APPLY_HOST_SELECTORS,
    CONTRACT_CORP_TO_CORP_TEXT,
    DICE_LOGIN_URL,
    EASY_APPLY_TEXT,
    LOCAL_RESUME,
    PASSWORD,
    USERNAME,
)


def login(page: Page) -> None:
    """Automate login flow for Dice using Playwright."""
    page.goto(DICE_LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector('input[name="email"]', timeout=30_000)
    page.fill('input[name="email"]', USERNAME)
    page.get_by_test_id("sign-in-button").click()

    page.wait_for_selector('input[name="password"]', timeout=60_000)
    page.fill('input[name="password"]', PASSWORD)
    page.get_by_test_id("submit-password").click()

    page.wait_for_load_state("load", timeout=60_000)

    login_success = False
    for _ in range(30):
        try:
            if page.url != DICE_LOGIN_URL and "login" not in page.url.lower():
                for indicator in [
                    page.locator('[data-testid*="dashboard"]'),
                    page.locator('[data-testid*="profile"]'),
                    page.locator('nav'),
                    page.locator('[class*="dashboard"]'),
                ]:
                    if indicator.count() > 0:
                        login_success = True
                        break
                if login_success:
                    break
        except Exception:
            pass
        page.wait_for_timeout(1000)

    if not login_success and page.url != DICE_LOGIN_URL:
        login_success = True

    if login_success:
        print("Logged in successfully.")
    else:
        print("Warning: Login status unclear, but proceeding...")


def _find_apply_button_anywhere(page: Page):
    """Find Easy Apply / Apply Now button anywhere on page (pierces shadow DOM)."""
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
    btn = page.get_by_role("button", name=EASY_APPLY_TEXT)
    if btn.count() > 0:
        try:
            if btn.first.is_visible(timeout=2000):
                return btn.first
        except Exception:
            pass
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
    btn = _find_apply_button_anywhere(page)
    if btn is not None:
        return btn
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
                    if EASY_APPLY_TEXT.search(text) or (text and "apply" in text.lower()):
                        if buttons.nth(i).is_visible(timeout=1000):
                            return buttons.nth(i)
                except Exception:
                    pass
    try:
        clicked = page.evaluate(
            """() => {
            function clickApply(root) {
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


def has_contract_corp_to_corp_in_text(scraped_text: str) -> bool:
    """Return True if the scraped page content contains 'Contract Corp To Corp'."""
    return bool(scraped_text and CONTRACT_CORP_TO_CORP_TEXT.search(scraped_text))


def has_contract_corp_to_corp(page: Page) -> bool:
    """Check whether the job page shows the 'Contract Corp To Corp' div."""
    loc = page.locator(
        'div.font-medium.text-zinc-600.text-xs.leading-none:has-text("Contract Corp To Corp")'
    )
    try:
        return loc.count() > 0 and loc.first.is_visible(timeout=2000)
    except Exception:
        return False


def _replace_resume_via_menu(page: Page, resume_file_path: str) -> bool:
    """
    Find the three-dot menu next to the resume section, click it, choose Replace,
    then upload the resume file. Returns True if upload completed.
    """
    try:
        three_dot_clicked = False
        for label in ["More options", "More", "Options", "Resume options"]:
            btn = page.get_by_role("button", name=re.compile(re.escape(label), re.I))
            if btn.count() > 0:
                try:
                    if btn.first.is_visible(timeout=2000):
                        btn.first.scroll_into_view_if_needed(timeout=3000)
                        page.wait_for_timeout(300)
                        btn.first.click()
                        three_dot_clicked = True
                        break
                except Exception:
                    pass

        if not three_dot_clicked:
            try:
                resume_section = page.locator(
                    "[class*='resume'], [data-testid*='resume'], section, div"
                ).filter(has=page.get_by_text("Resume", exact=False)).first
                if resume_section.count() > 0 and resume_section.is_visible(timeout=3000):
                    menu_btn = resume_section.locator("button").filter(has=page.locator("svg")).first
                    if menu_btn.count() > 0 and menu_btn.is_visible(timeout=2000):
                        menu_btn.scroll_into_view_if_needed(timeout=3000)
                        page.wait_for_timeout(300)
                        menu_btn.click()
                        three_dot_clicked = True
            except Exception:
                pass

        if not three_dot_clicked:
            try:
                menu_btn = page.locator("button:has(svg circle)").first
                if menu_btn.count() > 0 and menu_btn.is_visible(timeout=3000):
                    menu_btn.scroll_into_view_if_needed(timeout=3000)
                    page.wait_for_timeout(300)
                    menu_btn.click()
                    three_dot_clicked = True
            except Exception:
                pass

        clicked_replace_directly = False
        if not three_dot_clicked:
            try:
                replace_btn = page.locator('button.file-remove:has-text("Replace")').first
                if replace_btn.count() > 0 and replace_btn.is_visible(timeout=2000):
                    replace_btn.scroll_into_view_if_needed(timeout=3000)
                    replace_btn.click()
                    three_dot_clicked = True
                    clicked_replace_directly = True
                    page.wait_for_timeout(800)
            except Exception:
                pass

        page.wait_for_timeout(600)

        if three_dot_clicked and not clicked_replace_directly:
            for replace_loc in [
                page.get_by_role("menuitem", name="Replace"),
                page.get_by_role("button", name="Replace"),
                page.locator('[role="menuitem"]:has-text("Replace")'),
                page.get_by_text("Replace", exact=True),
                page.locator('button:has-text("Replace")'),
                page.locator('[class*="menu"]:has-text("Replace")'),
            ]:
                try:
                    if replace_loc.count() > 0 and replace_loc.first.is_visible(timeout=2000):
                        replace_loc.first.click()
                        break
                except Exception:
                    pass
            page.wait_for_timeout(800)

        file_input = None
        for selector in [
            'input#fsp-fileUpload',
            'input[type="file"]',
            'input[accept*="pdf"]',
            'input[accept*="document"]',
        ]:
            try:
                page.wait_for_selector(selector, timeout=6000)
                inp = page.locator(selector).first
                if inp.count() > 0 and inp.is_visible(timeout=2000):
                    file_input = inp
                    break
            except PWTimeoutError:
                continue
        if not file_input or file_input.count() == 0:
            return False

        file_input.set_input_files(resume_file_path)
        page.wait_for_timeout(800)

        for upload_btn in [
            page.locator('span[data-e2e="upload"]'),
            page.get_by_role("button", name=re.compile(r"upload|save", re.I)),
            page.locator('button:has-text("Upload")'),
            page.locator('button:has-text("Save")'),
        ]:
            try:
                if upload_btn.count() > 0 and upload_btn.first.is_visible(timeout=3000):
                    upload_btn.first.click()
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        return True
    except Exception as e:
        print("  Resume replace via menu failed:", e)
        return False


def easy_apply_on_job(
    page: Page,
    job_url: str,
    *,
    already_on_page: bool = False,
    resume_file_path: str | None = None,
) -> bool:
    """Open a job link and complete the Easy Apply process if available."""
    try:
        if not already_on_page:
            page.goto(job_url, wait_until="domcontentloaded")
            page.wait_for_load_state("load", timeout=15_000)
            page.wait_for_timeout(5000)

        if not has_contract_corp_to_corp(page):
            print("  Skipping (Contract Corp To Corp not found on page):", job_url)
            return False

        easy_btn = None
        easy_apply_wait_seconds = 25
        for _ in range(easy_apply_wait_seconds):
            easy_btn = _get_apply_button(page)
            if easy_btn is not None:
                break
            page.wait_for_timeout(1000)
        if not easy_btn:
            print(
                "  Skipping (Easy Apply button did not appear in %ds):" % easy_apply_wait_seconds,
                job_url,
            )
            return False

        def check_form_opened() -> bool:
            for _ in range(12):
                page.wait_for_timeout(1000)
                for check in [
                    page.get_by_role("button", name="Next"),
                    page.get_by_role("button", name="Submit"),
                    page.locator('button:has(span:text-is("Next"))'),
                    page.locator('button:has(span:text-is("Submit"))'),
                    page.locator('button.file-remove'),
                ]:
                    if check.count() > 0 and check.first.is_visible(timeout=500):
                        return True
            return False

        apply_form_opened = False
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                wait_time = random.uniform(5, 10)
                print(f"  Form did not open after first click. Waiting {wait_time:.1f}s before retry...")
                page.wait_for_timeout(int(wait_time * 1000))
                easy_btn = _get_apply_button(page)
                if not easy_btn:
                    print("  Easy Apply button no longer available; skipping.")
                    return False

            print(f"  Clicking Easy apply (attempt {attempt}/{max_attempts}) on:", job_url)
            if easy_btn != "js_clicked":
                try:
                    easy_btn.scroll_into_view_if_needed(timeout=5000)
                    page.wait_for_timeout(500)
                    easy_btn.click(force=True)
                except Exception:
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

            apply_form_opened = check_form_opened()
            if apply_form_opened:
                break

        if not apply_form_opened:
            print("  Easy Apply clicked but application form did not open after retries; skipping.")
            return False

        page.wait_for_timeout(2000)

        resume_path = (resume_file_path or LOCAL_RESUME or "").strip()
        if resume_path and os.path.isfile(resume_path):
            if _replace_resume_via_menu(page, resume_path):
                page.wait_for_timeout(1500)
        else:
            if not resume_path:
                print("  No resume path set; skipping resume upload.")
            else:
                print("  Resume file not found:", resume_path)

        try:
            for next_loc in [
                page.get_by_role("button", name="Next"),
                page.locator('button[type="submit"]:has(span:has-text("Next"))'),
                page.locator('button:has(span:text-is("Next"))'),
                page.locator('button.btn-next:has-text("Next")'),
            ]:
                if next_loc.count() > 0 and next_loc.first.is_visible(timeout=8000):
                    next_loc.first.click()
                    page.wait_for_timeout(2000)
                    break
        except Exception:
            pass

        try:
            page.wait_for_timeout(4000)
            for submit_loc in [
                page.get_by_role("button", name="Submit"),
                page.locator('button[type="button"]:has(span:has-text("Submit"))'),
                page.locator('button:has(span:text-is("Submit"))'),
                page.locator('button.btn-next:has-text("Submit")'),
            ]:
                if submit_loc.count() > 0 and submit_loc.first.is_visible(timeout=15_000):
                    submit_loc.first.click()
                    page.wait_for_timeout(2000)
                    print("  Submitted ✔")
                    return True
        except Exception:
            pass

        for _ in range(6):
            submit_btn = page.locator('button.btn-next:has-text("Submit")')
            if submit_btn.count() > 0 and submit_btn.first.is_visible(timeout=2000):
                submit_btn.first.click()
                page.wait_for_timeout(1200)
                print("  Submitted ✔")
                return True
            next_btn = page.locator('button.btn-next')
            if next_btn.count() > 0 and next_btn.first.is_visible(timeout=2000):
                next_btn.first.click()
                page.wait_for_timeout(1000)
            else:
                break

        try:
            for submit_loc in [
                page.get_by_role("button", name="Submit"),
                page.locator('button:has(span:text-is("Submit"))'),
            ]:
                if submit_loc.count() > 0 and submit_loc.first.is_visible(timeout=5000):
                    submit_loc.first.click()
                    page.wait_for_timeout(2000)
                    print("  Submitted ✔")
                    return True
        except Exception:
            pass

        print("  Could not reach Submit step; skipping.")
        return False

    except PWTimeoutError as te:
        print("  Timeout:", te)
        return False
    except Exception as e:
        print("  Error:", e)
        return False
