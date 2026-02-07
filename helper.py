import os
import re
from pathlib import Path

from groq import Groq

# Provide your API key, path to resume (.doc or .docx), and job description here (or use env vars)
API_KEY = os.environ.get("GROQ_API_KEY", "")
RESUME_PATH = r""
JOB_DESCRIPTION = """

"""


def load_resume_text(path: str) -> str:
    """Load resume text from a .doc or .docx file. Returns the full text as a string."""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Resume file not found: {path}")

    ext = Path(path).suffix.lower()
    if ext == ".docx":
        try:
            import docx
        except ImportError:
            raise ImportError("python-docx is required for .docx files. Install with: pip install python-docx")
        doc = docx.Document(path)
        return "\n\n".join(p.text for p in doc.paragraphs).strip()
    if ext == ".doc":
        try:
            import win32com.client
        except ImportError:
            raise ImportError("pywin32 is required for .doc files. Install with: pip install pywin32")
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(path)
            text = doc.Content.Text
            doc.Close(False)
            return (text or "").strip()
        finally:
            word.Quit()
    raise ValueError(f"Unsupported resume format: {ext}. Use .doc or .docx.")


def get_matching_score(api_key: str, resume_text: str, job_description: str) -> int:
    """Returns a matching score from 0 to 100."""
    client = Groq(api_key=api_key)
    prompt = f"""You are a resume–job matching expert. Compare the following resume and job description and output ONLY a single integer from 0 to 100 representing the match score (100 = perfect match).

Resume:
{resume_text}

Job description:
{job_description}

Output ONLY the number, nothing else. No explanation, no punctuation. Example: 75"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=16,
    )
    response = completion.choices[0].message.content or ""
    # Extract first number in range 0–100
    match = re.search(r"\b(100|[1-9]?\d)\b", response.strip())
    if match:
        return int(match.group(1))
    return -1  # parse failed


def is_lead_architect_or_manager_role(api_key: str, job_title: str, job_description: str) -> bool:
    """
    Returns True if we should SKIP this job (it is a Lead / Architect / Manager role).
    Uses the API to distinguish real roles from phrases like 'lead the initiative' or 'architect the solution'.
    """
    if not job_title.strip() and not job_description.strip():
        return False
    client = Groq(api_key=api_key)
    prompt = f"""You are a job classification expert. Given a job title and job description, determine whether this position is a **Lead**, **Architect**, or **Manager** role (i.e. the job title/level is lead, architect, or manager).

**Skip only when the POSITION is:**
- A Lead role: e.g. "Lead Engineer", "Team Lead", "Tech Lead", "Lead Developer"
- An Architect role: e.g. "Solutions Architect", "System Architect", "Software Architect", "Enterprise Architect"
- A Manager role: e.g. "Engineering Manager", "Product Manager", "Project Manager", "Development Manager"

**Do NOT skip when the description only uses these words as verbs or in passing**, for example:
- "lead the initiative", "lead projects", "lead technical discussions" (individual contributor who leads initiatives)
- "architect the solution", "architect systems" (engineer who designs systems, not the job title Architect)
- "manage deliverables", "manage your workload" (managing tasks, not a Manager position)

Job title: {job_title or "(not provided)"}

Job description (excerpt):
{(job_description or "")[:6000]}

Output ONLY one word: SKIP or APPLY. SKIP if the position is a Lead/Architect/Manager role. APPLY if it is an individual contributor or the words appear only in passing."""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=16,
        )
        response = (completion.choices[0].message.content or "").strip().upper()
        return "SKIP" in response
    except Exception:
        return False  # on API error, don't skip


def should_apply_to_job(
    api_key: str, resume_text: str, job_title: str, job_description: str
) -> bool:
    """
    Single consolidated API call: evaluates seniority (lead/architect/manager) and
    resume–job match, then returns a binary decision.
    Returns True (YES → proceed with application) or False (NO → skip).
    """
    if not (job_title.strip() or job_description.strip()):
        return False
    client = Groq(api_key=api_key)
    prompt = f"""You are a job application advisor. Your task is to output a single word: YES or NO.

**Output YES only if ALL of the following are true:**
1. **Seniority:** The position is NOT a Lead/Architect/Manager *role*. Treat as the job *level*, not verbs in the description.
   - SKIP (output NO) for: Lead Engineer, Team Lead, Tech Lead, Solutions Architect, System Architect, Software Architect, Engineering Manager, Product Manager, Project Manager, Development Manager.
   - APPLY (can be YES if match is good) for: individual contributor roles, or when "lead"/"architect"/"manage" appear only as verbs (e.g. "lead initiatives", "architect solutions", "manage deliverables").
2. **Role relevance:** The position must be relevant to GEN AI, Machine Learning, AI, or Data Scientist. Say NO to any other position that is not in this focus.
   - Data engineering: say YES only if it is clearly closer to data science with AI in it and the *main* focus is data science and AI; say NO if AI/data science is just a side thing or secondary.
   - MLOps is acceptable (you may say YES if other criteria match).
3. **Resume match:** The job description is a reasonable fit for the candidate's resume (skills, experience level, domain). The match should be strong enough to justify applying.

**Output NO if:**
- The position is clearly a Lead, Architect, or Manager *title/role*, OR
- The role is not relevant to GEN AI, ML, AI, or Data Scientist (or data engineering with AI/DS as main focus), OR
- The job description does not match the resume well (wrong level, unrelated skills, or poor fit).

Job title: {job_title or "(not provided)"}

Job description (excerpt):
{(job_description or "")[:6000]}

Resume (excerpt):
{(resume_text or "")[:4000]}

Output ONLY one word: YES or NO. No explanation."""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=16,
        )
        response = (completion.choices[0].message.content or "").strip().upper()
        return response.startswith("YES")
    except Exception:
        return False  # on API error, don't apply


if __name__ == "__main__":
    if not RESUME_PATH.strip():
        raise SystemExit("Set RESUME_PATH to the path of your resume (.doc or .docx) at the top of this file.")
    resume_text = load_resume_text(RESUME_PATH.strip())
    score = get_matching_score(API_KEY, resume_text, JOB_DESCRIPTION.strip())
    print(score)
