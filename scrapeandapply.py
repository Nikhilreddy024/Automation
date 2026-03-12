"""
Dice job search & Easy Apply automation — main entry point.
Orchestrates: scrape listings → filter → API decide → Easy Apply.
"""
import os
import time

from playwright.sync_api import sync_playwright

from apply_flow import (
    TargetClosedError,
    easy_apply_on_job,
    has_contract_corp_to_corp_in_text,
    login,
)
from config import BASE_URLS, LOCAL_RESUME, PER_JOB_WAIT_SECONDS
from helper import (
    API_KEY,
    RESUME_PATH,
    RESUMES,
    AllApiKeysFailedError,
    get_default_resume_path,
    get_resume_path_by_id,
    load_resume_text,
    select_best_resume,
    should_apply_to_job,
)
from job_page import scrape_job_description
from list_scraper import scrape_job_listings
from seen_links import append_seen_link, load_seen_links

# Load default resume text for the "should we apply?" API call
_default_path = get_default_resume_path() or RESUME_PATH.strip()
RESUME_TEXT = (
    load_resume_text(_default_path)
    if _default_path and os.path.isfile(_default_path)
    else ""
)


def main() -> None:
    """Entry point: for each search URL, scrape job list, filter, run API checks, then Easy Apply (one URL after another)."""
    seen_links = load_seen_links()
    total_submitted = 0
    total_attempted = 0

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page()
            login(page)

            api_unavailable = False

            for url_index, base_url in enumerate(BASE_URLS, start=1):
                print(f"\n{'='*60}\nSearch URL [{url_index}/{len(BASE_URLS)}]: {base_url.split('&q=')[1].split('&')[0] if '&q=' in base_url else base_url}\n{'='*60}")
                jobs = scrape_job_listings(base_url)
                links = [j["Job Link"] for j in jobs]

                new_links = [lnk for lnk in links if lnk not in seen_links]
                print(f"{len(new_links)} new links to process; {len(seen_links)} already seen.")

                if not new_links:
                    print("Nothing new for this URL. Continuing to next.")
                    continue

                submitted = 0
                for i, link in enumerate(new_links, start=1):
                    print(f"\n[{i}/{len(new_links)}] {link}")

                    job_title, job_description, full_scraped_text = scrape_job_description(page, link)
                    if not job_description:
                        print("  Skipping (could not extract job description)")
                        append_seen_link(link)
                        seen_links.add(link)
                        time.sleep(PER_JOB_WAIT_SECONDS)
                        continue

                    if not has_contract_corp_to_corp_in_text(full_scraped_text or ""):
                        print("  Skipping (Contract Corp To Corp not in scraped content)")
                        append_seen_link(link)
                        seen_links.add(link)
                        time.sleep(PER_JOB_WAIT_SECONDS)
                        continue

                    try:
                        apply_decision = should_apply_to_job(
                            API_KEY, RESUME_TEXT, job_title or "", job_description
                        )
                    except AllApiKeysFailedError as e:
                        print("  All Groq API keys failed while deciding whether to apply.")
                        print("  Details:", e)
                        print("  Stopping further API-based decisions for this run.")
                        api_unavailable = True
                        break

                    if not apply_decision:
                        print("  Skipping (API decision: NO)")
                        print("  Job title:", job_title or "(no title)")
                        print("  Job description:\n", job_description)
                        append_seen_link(link)
                        seen_links.add(link)
                        time.sleep(PER_JOB_WAIT_SECONDS)
                        continue

                    selected_resume_path = None
                    if RESUMES and len(RESUMES) > 1 and not api_unavailable:
                        try:
                            chosen_id = select_best_resume(
                                API_KEY,
                                job_description,
                                [
                                    {"id": r.get("id"), "description": r.get("description", "")}
                                    for r in RESUMES
                                ],
                            )
                            if chosen_id:
                                selected_resume_path = get_resume_path_by_id(chosen_id)
                                if selected_resume_path:
                                    print(f"  Selected resume: {chosen_id}")
                        except AllApiKeysFailedError as e:
                            print("  All Groq API keys failed while selecting best resume.")
                            print("  Details:", e)
                            print("  Falling back to default resume and stopping further API calls.")
                            api_unavailable = True
                    if not selected_resume_path:
                        selected_resume_path = get_default_resume_path() or LOCAL_RESUME or RESUME_PATH

                    applied = easy_apply_on_job(
                        page, link, already_on_page=True, resume_file_path=selected_resume_path
                    )

                    append_seen_link(link)
                    seen_links.add(link)

                    if applied:
                        submitted += 1

                    time.sleep(PER_JOB_WAIT_SECONDS)

                if api_unavailable:
                    print("\nAll Groq API keys failed; ending run early to avoid extra failed calls.")
                    break

                total_submitted += submitted
                total_attempted += len(new_links)
                print(f"\nURL done. Submitted: {submitted} / Attempted: {len(new_links)}")

            print(f"\nDone. Total submitted: {total_submitted} / Total attempted: {total_attempted}")
            page.wait_for_timeout(2000)
            browser.close()
    except TargetClosedError:
        print("Browser or tab was closed. Exiting.")
        return


if __name__ == "__main__":
    main()
