import os
from pathlib import Path

from groq import Groq, RateLimitError


# Provide your API keys, path to resume (.doc or .docx), and job description here (or use env vars)
# PRIMARY_API_KEY keeps backward compatibility with the original single-key setup.
PRIMARY_API_KEY = os.environ.get(
    "GROQ_API_KEY", "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"
)

# Optional additional keys. You can either:
# - Set them via env vars GROQ_API_KEY_2..GROQ_API_KEY_5, or
# - Replace the os.environ.get(...) calls with your literal keys.
ADDITIONAL_API_KEYS = [
    os.environ.get("GROQ_API_KEY_2", "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").strip(),
    os.environ.get("GROQ_API_KEY_3", "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").strip(),
    os.environ.get("GROQ_API_KEY_4", "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").strip(),
    os.environ.get("GROQ_API_KEY_5", "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").strip(),
]

API_KEYS = [k for k in [PRIMARY_API_KEY, *ADDITIONAL_API_KEYS] if k]

# Backwards compatible name (still used by other modules, but actual rotation
# happens inside helper functions using API_KEYS).
API_KEY = PRIMARY_API_KEY


class AllApiKeysFailedError(Exception):
    """Raised when all configured Groq API keys fail during this run."""


_FAILED_GROQ_KEYS: set[str] = set()

# Legacy single-resume path (used as fallback if RESUMES is empty or for backward compatibility)
RESUME_PATH = r"C:\Users\nikhi\Desktop\realistic\Nikhil_R_Resume_.docx"

# Character limits for "should we apply?" API call (reduces tokens/cost).
# Resume excerpt: ~6000–8000 chars; job description up to ~10k chars so the model
# can better understand whether AI/GenAI/DS/MLOps is the main focus.
SHOULD_APPLY_RESUME_CHARS = 8000
SHOULD_APPLY_JOB_DESC_CHARS = 6000

# Multi-resume configuration: list of dicts with id, path, and description.
# The "default" resume is used for the initial "should we apply?" API call.
# Add your five resumes here with paths and brief descriptions of skill emphasis.
RESUMES = [
    {
        "id": "default",
        "path": r"C:\Users\nikhi\Desktop\realistic\Nikhil_R_Resume.docx",
        "description": "General AI/ML resume with broad technology coverage.",
    },
    # Add your five resumes below. Example entries:
    {"id": "Backend & AI Infrastructure Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume__.docx", "description": "This resume positions the candidate as a Senior Data Scientist and AI Engineer specializing in backend infrastructure and scalable ML systems. It is strictly optimized for roles focusing on server-side development, MLOps, and the engineering of autonomous AI agents. Key highlights include deep expertise in Python (FastAPI, Flask), distributed systems, and designing event-driven architectures with Apache Kafka and Redis. It emphasizes the construction of robust RAG pipelines, vector search infrastructure, and high-performance data pipelines processing terabytes of data. Select this version if the job description prioritizes backend engineering, API design, model deployment, cloud infrastructure (AWS/Azure), or algorithmic complexity. It is the ideal choice for titles like AI Engineer, Backend Engineer, Machine Learning Engineer, or Data Architect, where the primary value add is the engine driving the application rather than the frontend presentation layer."},

    {"id": "Full Stack AI Developer Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume--.docx", "description": "This resume positions the candidate as a Full Stack AI Developer who bridges the gap between advanced AI capabilities and modern web application interfaces. It is specifically tailored for roles requiring end-to-end solution development, combining strong backend Python skills with frontend expertise in React, Next.js, TypeScript, and Node.js. The experience highlights integrating Generative AI (OpenAI, Anthropic) directly into responsive user interfaces, developing real-time streaming chat applications, and creating interactive analytics dashboards. Select this version if the job description mentions Full Stack, Product Engineering, or explicitly lists frontend frameworks (React, Angular, Vue) alongside AI requirements. It is the best choice when the role involves delivering complete, user-facing products and requires knowledge of connecting complex ML models to intuitive, polished web experiences using the modern JavaScript ecosystem."},

    {"id": "Strategic Data Science & Analytics Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume_Data Scientist.docx", "description": "This resume positions the candidate as a Senior Data Scientist focused on enterprise-scale predictive analytics, statistical modeling, and business optimization. It is optimized for roles that prioritize driving measurable business value (ROI) through hypothesis testing, A/B testing, and causal inference over purely engineering tasks. The profile highlights deep expertise in Azure Databricks and AWS SageMaker for building distributed data pipelines and MLOps workflows. It showcases success in demand forecasting, customer segmentation, and churn prediction using ensemble methods (XGBoost, LightGBM) and deep learning. Select this version for job descriptions requiring a Data Scientist to solve operational problems in logistics, marketing, or finance using Python, SQL, and statistical analysis."},

    {"id": "Conversational AI & Dialogflow Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume-D.docx", "description": "This resume is strictly optimized for Conversational AI and Agentic System roles. It positions the candidate as an expert in building production-grade dialog systems using Google Dialogflow CX, Python ADK, and Generative AI. The experience emphasizes architecting deterministic conversation flows blended with LLM-driven agents (GPT-4, Claude) for contact center automation and customer interaction. Key differentiators include strong backend engineering for orchestration services, vector search (RAG) implementation, and real-time inference. Select this version if the job description asks for a Conversational AI Engineer, Dialogflow Developer, or AI Agent Architect, specifically where the core responsibility involves designing chatbots, voicebots, or intelligent virtual assistants."},

    {"id": "GenAI & GPU Optimization Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume-G.docx", "description": "This resume positions the candidate as a GenAI & LLM Engineer specializing in inference optimization and hardware acceleration. It is strictly optimized for roles requiring deep technical expertise in serving Large Language Models (LLMs) efficiently, rather than just using APIs. Key differentiators include GPU kernel optimization using Triton and CUDA, model quantization (4-bit/8-bit), and vLLM deployment to minimize latency. It highlights the fine-tuning of Small Language Models (SLMs) using LoRA/QLoRA and architecting high-performance RAG pipelines. Select this version if the job description focuses on model serving, latency engineering, LLM infrastructure, or requires low-level optimization skills with PyTorch and NVIDIA stacks. It is ideal for titles like GenAI Engineer, LLM Engineer, or AI Performance Engineer where the primary goal is optimizing the cost, speed, and throughput of AI systems."},

    {"id": "MLOps & AI Infrastructure Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume_M.docx", "description": "This resume positions the candidate as an MLOps Engineer and AI Infrastructure Architect focused on the operational lifecycle of AI models. It is tailored for roles prioritizing automation, governance, and scalability over experimental model development. The profile emphasizes building CI/CD/CT pipelines, GitOps workflows, and Infrastructure as Code (Terraform, CloudFormation) on AWS. It specifically highlights expertise with Dataiku for enterprise governance and AWS Bedrock/SageMaker for orchestrating multi-agent systems. Select this version for job descriptions asking for an MLOps Engineer, AI Platform Engineer, or DevOps Engineer for AI, specifically those requiring experience with deployment strategies (blue-green, canary), observability (Prometheus, Grafana), and ensuring the reliability, security, and compliance of production AI environments."},

    {"id": "AWS Native & Bedrock AI Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume_.docx", "description": "This resume is strictly optimized for AWS-native roles, positioning the candidate as an expert in the Amazon Web Services ecosystem. It highlights specialized experience with Amazon Bedrock for Generative AI, AWS Lambda for serverless orchestration, and Amazon Kendra for semantic search. Unlike generalist profiles, this version emphasizes AWS-specific patterns such as DynamoDB access design, EventBridge architectures, and Step Functions for workflow automation. It also showcases deep DevSecOps knowledge within AWS, including IAM, KMS, and CloudTrail governance. Select this version for job descriptions that explicitly mention AWS services (e.g., AWS AI Engineer, Bedrock Developer, AWS Data Architect) or require building compliant, cloud-native solutions strictly within the Amazon cloud environment."},

    {"id": "GCP Native & Vertex AI Resume", "path": r"C:\Users\nikhi\Downloads\resumes\Nikhil_R_Resume-.docx", "description": "This resume is strictly optimized for GCP-native roles, positioning the candidate as a specialist in the Google Cloud ecosystem. It highlights deep expertise with Vertex AI for end-to-end MLOps, Gemini/PaLM 2 for Generative AI, and BigQuery for petabyte-scale data warehousing. The profile differentiates itself by showcasing serverless AI architectures using Cloud Run and Cloud Functions, along with distributed training on GKE. It also emphasizes document processing with Document AI and Google Cloud Vision API. Select this version for job descriptions that explicitly mention GCP, Vertex AI, BigQuery, or TensorFlow, or for roles that require building AI solutions specifically within the Google Cloud infrastructure."},
]

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


def should_apply_to_job(
    api_key: str, resume_text: str, job_title: str, job_description: str
) -> bool:
    """
    Single consolidated API call: evaluates seniority (lead/architect/manager) and
    resume–job match, then returns a binary decision.
    Returns True (YES → proceed with application) or False (NO → skip).
    """
    title = (job_title or "").strip()
    desc = (job_description or "").strip()
    if not (title or desc):
        return False

    prompt = f"""You are a job application advisor. Output exactly one word: YES or NO.

**Candidate:** AI/ML engineer (Gen AI, LLMs, MLOps, data science, Python, backend/full-stack with AI). Only apply to engineering/technical IC roles that match this profile.

**Say YES only when ALL are true:**
1. **Job level:** Individual contributor—NOT Lead, Architect, or Manager (e.g. no "Lead Engineer", "Tech Lead", "Solutions Architect", "Engineering/Product/Project Manager", "Development Manager", "Solution Engineer").
2. **Job type:** Engineering or data role—title/description must be clearly for an **Engineer**, **Developer**, **Scientist**, or **Researcher** in AI/ML/data/software. NOT for Designer, UX/UI, content, marketing, sales, recruiting, or HR.
3. **Domain fit (MAIN focus on AI/ML/DS/MLOps):**
   - The primary responsibilities are building or operating AI/ML/GenAI/LLM/data systems (e.g. AI Engineer, GenAI Engineer, Data Scientist, ML Engineer, MLOps Engineer, LLM Engineer, AI-focused Full Stack/Backend/Platform Engineer).
   - It is OK if the title is generic (e.g. "Software Engineer", "Full Stack Engineer", "Backend Engineer") **as long as** the description clearly states that a core/primary part of the job is building AI/GenAI/ML/LLM features or data-driven systems.
   - Do **NOT** say YES when AI is only mentioned tangentially (e.g. "design AI-inspired UX", "work on UI for AI tools") and the main role is UI/UX, design, or non-engineering.
4. Resume should reasonably align with key skills asked (Python, ML, GenAI, data, MLOps, backend, etc.). Do not require a perfect match; a solid overlap is enough.

**Say NO when any of these apply:**
- Title or level is Lead, Architect, Manager, Director, VP, Principal, Staff (as job level), Head of, Scrum Master.
- Role is design or non-engineering: UX Designer, UI Designer, Product Designer, Visual/Content Designer, UX Researcher, Content Writer, Copywriter, Marketing, Sales, Recruiter, HR.
- Role has no real AI/ML/data component (e.g. generic front-end, generic DevOps/SRE with no ML, generic product engineering with only a passing mention of AI, Cortex developer with no AI focus, etc.).
- PhD required/mandatory, or mandatory in-person/on-site interview.
- Clearly different domain (e.g. clinician, legal, non-tech) with no AI/ML.

Use the **job title** as the main signal for role type:
- If the title explicitly contains **AI**, **Artificial Intelligence**, **ML**, **Machine Learning**, **GenAI**, **LLM**, **Data Scientist**, **MLOps**, or similar and it is not clearly a Manager/Lead/Architect or non-engineering title (e.g. "AI Product Manager", "AI UX Designer"), then **lean YES** when the responsibilities match the candidate profile. This includes titles like "Gen AI Integration Engineer", "AI Integration Engineer", "AI Platform Engineer", etc.
- If the title is a generic engineering title like **Software Engineer**, **Full Stack Engineer**, **Backend Engineer**, **Platform Engineer**, **Data Engineer**, etc., but the description clearly emphasizes building or operating AI/GenAI/ML/LLM/data systems as a core responsibility, **lean YES**.
- If the title is Designer/Manager/Marketing/Sales/Recruiting/HR or clearly non-engineering, say NO even if the description mentions AI.

When the role is borderline but there is substantial evidence that the **main focus** is AI/GenAI/data science/MLOps engineering and the skills largely align, prefer **YES**. Only say NO when it is clearly non-engineering, non-AI-focused, or obviously mismatched.

Job title: {title or "(not provided)"}

Job description (excerpt):
{(job_description or "")[:SHOULD_APPLY_JOB_DESC_CHARS]}

Resume (excerpt):
{(resume_text or "")[:SHOULD_APPLY_RESUME_CHARS]}

Output ONLY one word: YES or NO. No explanation."""

    last_error: Exception | None = None

    for key in API_KEYS:
        if key in _FAILED_GROQ_KEYS:
            continue

        client = Groq(api_key=key)
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=16,
            )
            raw_content = completion.choices[0].message.content
            print("  API raw decision response:", repr(raw_content))
            response = (raw_content or "").strip().upper()
            return response.startswith("YES")
        except RateLimitError as e:
            print(
                "  API rate limit in should_apply_to_job for key:",
                f"...{key[-6:]}",
                repr(e),
            )
            _FAILED_GROQ_KEYS.add(key)
            last_error = e
            continue
        except Exception as e:
            print(
                "  API error in should_apply_to_job for key:",
                f"...{key[-6:]}",
                repr(e),
            )
            _FAILED_GROQ_KEYS.add(key)
            last_error = e
            continue

    # If we get here, all keys failed for this run.
    msg = f"All Groq API keys failed in should_apply_to_job. Last error: {repr(last_error)}"
    print(" ", msg)
    raise AllApiKeysFailedError(msg)


def select_best_resume(
    api_key: str,
    job_description: str,
    resume_entries: list[dict],
) -> str | None:
    """
    Given a job description and a list of resume entries (each with 'id' and 'description'),
    uses the API to select the best-fitting resume.
    Returns the id of the selected resume, or None if selection fails.
    """
    if not resume_entries or not job_description.strip():
        return None
    # If only one resume, return its id
    if len(resume_entries) == 1:
        return resume_entries[0].get("id")
    entries_text = "\n\n".join(
        f"- **{e.get('id', 'unknown')}**: {e.get('description', '')}"
        for e in resume_entries
    )
    ids_list = ", ".join(repr(e.get("id", "")) for e in resume_entries)

    prompt = f"""You are a resume selection expert. Given a job description and several resume variants (each with an id and a brief description of its skill emphasis), choose which resume to use.

**Goal:** Do **not** always default to the "default" resume. Use the specialized resumes whenever there is a **reasonable or moderate match**, not only when the match is extremely strong.

Guidance and examples:
- Job emphasizes AWS/Bedrock/Kendra or is clearly AWS‑native → prefer "AWS Native & Bedrock AI Resume"
- Job emphasizes GCP/Vertex AI/BigQuery or is clearly GCP‑native → prefer "GCP Native & Vertex AI Resume"
- Job emphasizes Conversational AI/Dialogflow/chatbots/virtual agents → prefer "Conversational AI & Dialogflow Resume"
- Job emphasizes GenAI inference, GPU work, vLLM/throughput/latency → prefer "GenAI & GPU Optimization Resume"
- Job emphasizes MLOps, CI/CD, platform/infra, observability → prefer "MLOps & AI Infrastructure Resume"
- Job emphasizes Full Stack, React/Next.js/frontend + AI product work → prefer "Full Stack AI Developer Resume"
- Job emphasizes backend, infrastructure, Kafka, scalable services → prefer "Backend & AI Infrastructure Resume"
- Job emphasizes analytics, experimentation, forecasting, A/B testing → prefer "Strategic Data Science & Analytics Resume"

For **very generic** AI/ML/Data Scientist/Software roles where no resume clearly stands out, or when the match is truly unclear, fall back to **default**.

Job description:
{job_description[:6000]}

Resume variants:
{entries_text}

Output ONLY the exact id of the resume to use. Prefer a specialized resume whenever you see a reasonable alignment; otherwise use "default". Valid ids: {ids_list}."""

    last_error: Exception | None = None

    for key in API_KEYS:
        if key in _FAILED_GROQ_KEYS:
            continue

        client = Groq(api_key=key)
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=64,
            )
            response = (completion.choices[0].message.content or "").strip()
            # Normalize: remove quotes, whitespace
            chosen = response.strip("'\"").strip()
            valid_ids = {str(e.get("id", "")) for e in resume_entries}
            if chosen in valid_ids:
                return chosen
            # Try partial match
            for rid in valid_ids:
                if rid.lower() in chosen.lower() or chosen.lower() in rid.lower():
                    return rid
            return list(resume_entries)[0].get("id")  # fallback to first
        except RateLimitError as e:
            print(
                "  API rate limit in select_best_resume for key:",
                f"...{key[-6:]}",
                repr(e),
            )
            _FAILED_GROQ_KEYS.add(key)
            last_error = e
            continue
        except Exception as e:
            print(
                "  API error in select_best_resume for key:",
                f"...{key[-6:]}",
                repr(e),
            )
            _FAILED_GROQ_KEYS.add(key)
            last_error = e
            continue

    msg = f"All Groq API keys failed in select_best_resume. Last error: {repr(last_error)}"
    print(" ", msg)
    raise AllApiKeysFailedError(msg)


def get_default_resume_path() -> str:
    """Return the path of the default resume (first entry in RESUMES, or RESUME_PATH)."""
    if RESUMES:
        for r in RESUMES:
            if r.get("id") == "default":
                return (r.get("path") or "").strip()
        return (RESUMES[0].get("path") or "").strip()
    return (RESUME_PATH or "").strip()


def get_resume_path_by_id(resume_id: str) -> str | None:
    """Return the file path for a resume by id, or None if not found."""
    for r in RESUMES:
        if str(r.get("id", "")) == str(resume_id):
            return (r.get("path") or "").strip() or None
    return None

