import os
import re
import json
import time

import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from groq import RateLimitError
from streamlit_echarts import st_echarts


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Career Copilot",
    page_icon="🚀",
    layout="wide"
)


# ============================================================
# SIMPLE UI STYLING
# ============================================================

st.markdown("""
<style>
.stButton>button {
    width: 100%;
    height: 50px;
    font-size: 18px;
    font-weight: bold;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# ENVIRONMENT / GROQ
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except Exception:
        GROQ_API_KEY = None

if not GROQ_API_KEY:
    st.error(
        "GROQ_API_KEY was not found. Please add it to your .env file."
    )
    st.stop()


# GPT-OSS 120B is the current model we are using.
# Keep temperature at 0 for consistent screening results.
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=GROQ_API_KEY
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <h1 style='text-align:center;'>
        🚀 AI Career Copilot
    </h1>

    <p style='text-align:center;color:gray;font-size:18px;'>
        Resume Analysis • Interview Prep • Salary Estimate • Cover Letter
    </p>
    """,
    unsafe_allow_html=True
)


# ============================================================
# INPUTS
# ============================================================

resume = st.file_uploader(
    "Upload Resume",
    type="pdf"
)

jd = st.text_area(
    "Paste Job Description",
    height=220
)


# ============================================================
# GAUGE
# ============================================================

def show_score_gauge(score):
    option = {
        "series": [
            {
                "type": "gauge",
                "startAngle": 90,
                "endAngle": -270,
                "pointer": {
                    "show": False
                },
                "progress": {
                    "show": True,
                    "roundCap": True,
                    "width": 18,
                    "itemStyle": {
                        "color": "#00FF99"
                    }
                },
                "axisLine": {
                    "lineStyle": {
                        "width": 18
                    }
                },
                "axisTick": {
                    "show": False
                },
                "splitLine": {
                    "show": False
                },
                "axisLabel": {
                    "show": False
                },
                "detail": {
                    "fontSize": 30,
                    "formatter": "{value}%"
                },
                "data": [
                    {
                        "value": score
                    }
                ]
            }
        ]
    }

    st_echarts(
        options=option,
        height="300px"
    )


# ============================================================
# AI CALL WITH RATE-LIMIT PROTECTION
# ============================================================

def ask(prompt, max_retries=3):
    """
    Call Groq and gracefully handle temporary rate limits.

    We deliberately keep retries here instead of allowing a
    429 error to crash the Streamlit application.
    """
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            return response.content

        except RateLimitError:
            if attempt == max_retries - 1:
                return (
                    "RATE_LIMIT_ERROR: Groq is temporarily rate limited. "
                    "Please wait about 15-30 seconds and try again."
                )

            wait_time = 15
            time.sleep(wait_time)

    return "AI request failed."


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_response(content):
    """
    Extract JSON even if the model wraps it in ```json ... ```.
    """
    if not content:
        raise ValueError("Empty AI response.")

    cleaned = content.strip()

    # Remove markdown code fences if present.
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first JSON object.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)

    if not match:
        raise ValueError("No JSON object found in AI response.")

    return json.loads(match.group())


# ============================================================
# SESSION STATE
# ============================================================

if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

if "current_jd" not in st.session_state:
    st.session_state.current_jd = ""

if "interview_result" not in st.session_state:
    st.session_state.interview_result = None

if "salary_result" not in st.session_state:
    st.session_state.salary_result = None

if "cover_result" not in st.session_state:
    st.session_state.cover_result = None


# ============================================================
# ANALYZE BUTTON
# IMPORTANT: Only the core analysis runs here.
# Other AI features run ONLY when their own buttons are clicked.
# ============================================================

if resume and jd and st.button("Analyze", type="primary"):

    with st.spinner("Reading resume and analyzing candidate..."):

        reader = PdfReader(resume)

        resume_text = ""

        for page in reader.pages:
            text = page.extract_text()

            if text:
                resume_text += text + "\n"

        # Keep the extracted data for the other features.
        st.session_state.resume_text = resume_text
        st.session_state.current_jd = jd

        analysis_prompt = f"""
You are an expert technical recruiter.

Compare the resume against the job description.

Return ONLY valid JSON.
Do not use markdown.
Do not add explanations outside the JSON.

Use exactly this structure:

{{
  "match_score": 80,
  "matching_skills": ["Python", "SQL"],
  "missing_skills": ["Docker", "AWS"],
  "strengths": ["Strong automation background"],
  "improvements": ["Learn Docker"],
  "recommendation": "Recommended"
}}

Rules:
- match_score must be an integer from 0 to 100.
- matching_skills must contain skills actually supported by the resume.
- missing_skills must contain relevant JD requirements that are not clearly demonstrated.
- Do not invent experience.
- recommendation should be one of:
  "Strongly Recommended",
  "Recommended",
  "Potential Match",
  "Not Recommended".

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd}
"""

        content = ask(analysis_prompt, max_retries=3)

        if content.startswith("RATE_LIMIT_ERROR:"):
            st.error(content)
        else:
            try:
                data = parse_json_response(content)

                # Basic validation / safe defaults.
                data["match_score"] = max(
                    0,
                    min(100, int(data.get("match_score", 0)))
                )

                data["matching_skills"] = data.get("matching_skills", [])
                data["missing_skills"] = data.get("missing_skills", [])
                data["strengths"] = data.get("strengths", [])
                data["improvements"] = data.get("improvements", [])
                data["recommendation"] = data.get(
                    "recommendation",
                    "Potential Match"
                )

                st.session_state.analysis_data = data

                # Clear old generated outputs when a new candidate is analyzed.
                st.session_state.interview_result = None
                st.session_state.salary_result = None
                st.session_state.cover_result = None

            except Exception as e:
                st.error("Could not parse AI response.")
                st.write(content)
                st.write(e)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Analysis",
    "🎯 Interview Q&A",
    "💰 Salary",
    "✉️ Cover Letter"
])


# ============================================================
# TAB 1 — ANALYSIS
# ============================================================

with tab1:

    data = st.session_state.analysis_data

    if data:

        score = data["match_score"]

        st.divider()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            show_score_gauge(score)

        with col2:
            st.metric(
                "✅ Matching Skills",
                len(data["matching_skills"])
            )

        with col3:
            st.metric(
                "❌ Missing Skills",
                len(data["missing_skills"])
            )

        with col4:
            st.metric(
                "📌 Recommendation",
                data["recommendation"]
            )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("✅ Matching Skills")

            for skill in data["matching_skills"]:
                st.success(skill)

        with col2:
            st.subheader("❌ Missing Skills")

            for skill in data["missing_skills"]:
                st.error(skill)

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏆 Candidate Strengths")

            for item in data["strengths"]:
                st.info(item)

        with col2:
            st.subheader("📈 Areas of Improvement")

            for item in data["improvements"]:
                st.warning(item)

        st.divider()

        st.subheader("🤖 Hiring Recommendation")

        if score >= 80:
            st.success(
                f"Strong Match - {data['recommendation']}"
            )
        elif score >= 60:
            st.warning(
                f"Potential Match - {data['recommendation']}"
            )
        else:
            st.error(
                f"Weak Match - {data['recommendation']}"
            )

    else:
        st.info(
            "Upload a resume, paste a job description, "
            "and click Analyze to begin."
        )


# ============================================================
# ============================================================
# TAB 2 — INTERVIEW Q&A
# ============================================================

with tab2:

    if not st.session_state.resume_text:
        st.info("Run Analysis first.")
    else:

        st.write(
            "Generate interview questions only when you need them. "
            "This prevents unnecessary AI calls."
        )

        if st.button(
            "🎯 Generate Interview Questions",
            key="generate_interview"
        ):

            with st.spinner("Generating interview questions..."):

                interview_prompt = f"""
You are a Senior Technical Interviewer.

Using the resume and job description, generate exactly 10 relevant
interview questions.

IMPORTANT OUTPUT FORMAT:
Do NOT use a table.
Do NOT use HTML.
Do NOT use <br>, <br/>, or <br /> tags.

For EACH question, use exactly this structure:

### Q1. <Short question title>

**Question:** <the interview question>

**Candidate should explain:**
- <point 1>
- <point 2>
- <point 3>

**Interviewer expects:**
- <point 1>
- <point 2>
- <point 3>

**Difficulty:** Easy / Medium / Hard

Then continue with Q2, Q3, ... up to Q10.

Focus on the candidate's actual experience and the requirements
of the job description.

Do not invent employers, projects, technologies, achievements,
certifications, degrees, or experience that are not supported
by the resume.

RESUME:
{st.session_state.resume_text}

JOB DESCRIPTION:
{st.session_state.current_jd}
"""

                result = ask(
                    interview_prompt,
                    max_retries=3
                )

                # Clean accidental HTML tags if the model ignores
                # the formatting instruction.
                result = result.replace("<br>", "\n")
                result = result.replace("<br/>", "\n")
                result = result.replace("<br />", "\n")

                st.session_state.interview_result = result

        if st.session_state.interview_result:

            if st.session_state.interview_result.startswith(
                "RATE_LIMIT_ERROR:"
            ):
                st.error(st.session_state.interview_result)
            else:
                st.markdown(st.session_state.interview_result)


# TAB 3 — SALARY
# ============================================================

with tab3:

    if not st.session_state.resume_text:
        st.info("Run Analysis first.")
    else:

        st.write(
            "Generate the salary estimate when needed."
        )

        if st.button(
            "💰 Estimate Salary",
            key="generate_salary"
        ):

            with st.spinner("Estimating salary..."):

                salary_prompt = f"""
Estimate the candidate's salary range based on the resume
and job description.

Return:

Minimum Salary
Expected Salary
Stretch Salary
Reasoning
Skills increasing salary
Missing skills affecting salary

Be realistic and clearly state that the estimate is an
AI-generated market estimate, not a guaranteed offer.

RESUME:
{st.session_state.resume_text}

JOB DESCRIPTION:
{st.session_state.current_jd}
"""

                result = ask(
                    salary_prompt,
                    max_retries=3
                )

                st.session_state.salary_result = result

        if st.session_state.salary_result:
            if st.session_state.salary_result.startswith(
                "RATE_LIMIT_ERROR:"
            ):
                st.error(st.session_state.salary_result)
            else:
                st.markdown(st.session_state.salary_result)


# ============================================================
# TAB 4 — COVER LETTER
# ============================================================

with tab4:

    if not st.session_state.resume_text:
        st.info("Run Analysis first.")
    else:

        st.write(
            "Generate the cover letter when needed."
        )

        if st.button(
            "✉️ Generate Cover Letter",
            key="generate_cover"
        ):

            with st.spinner("Generating cover letter..."):

                cover_prompt = f"""
Write a professional, ready-to-use ATS-friendly cover letter.

IMPORTANT FORMAT RULES:
- Do NOT put the candidate's name, email, phone number, address,
  LinkedIn, or other contact details at the beginning.
- Start directly with:
  Hiring Manager
  Company Name
  Dear Hiring Manager,
- Write the main cover-letter paragraphs normally.
- End the letter with:
  Sincerely,

  [Candidate's Full Name]
  [Email]
  [Phone]
  [Location]
  [LinkedIn, only if present in the resume]
- The candidate's contact details MUST appear at the END,
  below the signature, not at the top.
- Do not include placeholders such as "[Candidate's Full Name]"
  if the actual information is available in the resume.
- If a company name or hiring manager name is clearly available
  from the job description, use it. Otherwise use "Hiring Manager"
  and the company name from the JD if available.
- Do not add a separate heading such as "Cover Letter".
- Keep it below 300 words.
- Return ONLY the finished cover letter in clean Markdown.
- Do not use HTML tags.

CONTENT RULES:
- Use ONLY information supported by the resume and job description.
- Do not invent qualifications, employers, degrees, certifications,
  projects, achievements, or experience.
- Tailor the letter specifically to the role and company.

RESUME:
{st.session_state.resume_text}

JOB DESCRIPTION:
{st.session_state.current_jd}
"""

                result = ask(
                    cover_prompt,
                    max_retries=3
                )

                st.session_state.cover_result = result

        if st.session_state.cover_result:

            if st.session_state.cover_result.startswith(
                "RATE_LIMIT_ERROR:"
            ):
                st.error(st.session_state.cover_result)
            else:
                st.markdown(st.session_state.cover_result)

                st.download_button(
                    "📥 Download Cover Letter",
                    st.session_state.cover_result,
                    file_name="Cover_Letter.txt",
                    mime="text/plain"
                )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.markdown(
    """
    <center>
    Built with ❤️ using Streamlit + Groq + GPT-OSS 120B
    <br>
    © 2026 Malaika Shaikh
    </center>
    """,
    unsafe_allow_html=True
)
