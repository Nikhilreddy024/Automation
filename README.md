# 🎯 Dice Job Auto Apply Bot

This Python project automates job searches and easy applications on [Dice.com](https://www.dice.com). It scrapes job listings related to related roles, detects “Easy Apply” opportunities, and automatically submits your resume through a browser automation flow.

## 🚀 Features

* Scrapes new job listings daily from Dice (configurable filters)
* Detects unique job links and avoids duplicates
* Automates login and “Easy Apply” submission using Playwright
* Tracks already-applied jobs in a persistent file
* Custom wait times between submissions to mimic natural activity

## 🧩 Tech Stack

* **Python 3.10+**
* **Requests** & **BeautifulSoup** for scraping
* **Playwright** for browser automation
* **Pandas** for lightweight data handling

## ⚙️ Setup Instructions

1. **Clone this repo**

   ```bash
   git clone https://github.com/KrishnaYalamarthi/Dice-Automation.git
   cd scrapeandapply
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   playwright install
   ```

3. **Configure credentials**
   Update your login info and resume path in `scrapeandapply.py`:

   ```python
   USERNAME = "your_email@example.com"
   PASSWORD = "your_password"
   LOCAL_RESUME = "path/to/your_resume.docx"
   ```

4. **Run the script**

   ```bash
   python scrapeandapply.py
   ```

## 🛡️ Safety & Ethics

Use responsibly. This script automates interactions with Dice for educational and personal productivity purposes.
Do not spam or violate site terms of service. Always review and update your applications before submission.

## 🧠 Future Enhancements

•	Integrate AI to analyze each job posting and extract key skill requirements.

•	Automatically tailor application content using your existing resume data.

•	Optimize keyword alignment to improve ATS (Applicant Tracking System) scores.

•	Preserve original resume formatting while dynamically customizing content.

•	Provide real-time feedback on resume-job match quality before submission.



