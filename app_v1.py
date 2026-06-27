import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from streamlit_echarts import st_echarts
import json
import re

# -------------------------
# PAGE CONFIG
# -------------------------

st.set_page_config(
    page_title="AI Resume Screening Agent",
    page_icon="🚀",
    layout="wide"
)

# -------------------------
# CUSTOM CSS
# -------------------------

st.markdown("""
<style>

.main {
    background-color: #0E1117;
}

.block-container {
    padding-top: 2rem;
}

</style>
""", unsafe_allow_html=True)

# -------------------------
# LOAD ENV
# -------------------------

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

# -------------------------
# GAUGE FUNCTION
# -------------------------

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

# -------------------------
# HEADER
# -------------------------

st.title("🚀 AI Resume Screening Agent")

st.markdown(
    "Upload a resume and compare it against a Job Description"
)

# -------------------------
# INPUTS
# -------------------------

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader(
        "📄 Upload Resume PDF",
        type=["pdf"]
    )

with col2:
    job_description = st.text_area(
        "💼 Paste Job Description",
        height=250
    )

# -------------------------
# PROCESS
# -------------------------

if uploaded_file:

    reader = PdfReader(uploaded_file)

    resume_text = ""

    for page in reader.pages:

        text = page.extract_text()

        if text:
            resume_text += text

    st.success("✅ Resume Uploaded Successfully")

    if st.button("🔍 Analyze Resume"):

        if not job_description.strip():
            st.warning("Please enter Job Description")
            st.stop()

        with st.spinner("Analyzing Resume..."):

            prompt = f"""
You are an expert recruiter.

Compare the resume against the job description.

Return ONLY JSON.

Format:

{{
"match_score": 80,
"matching_skills": ["Python","SQL"],
"missing_skills": ["Docker","AWS"],
"strengths": ["Strong automation background"],
"improvements": ["Learn Docker"],
"recommendation": "Recommended"
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

            response = llm.invoke(prompt)

            try:

                content = response.content

                json_match = re.search(
                    r"\{.*\}",
                    content,
                    re.DOTALL
                )

                data = json.loads(
                    json_match.group()
                )

                score = int(data["match_score"])

                st.divider()

                # -------------------------
                # TOP DASHBOARD
                # -------------------------

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

                # -------------------------
                # SKILLS
                # -------------------------

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

                # -------------------------
                # STRENGTHS / IMPROVEMENTS
                # -------------------------

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

                # -------------------------
                # FINAL RECOMMENDATION
                # -------------------------

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

            except Exception as e:

                st.error(
                    "Could not parse AI response"
                )

                st.write(response.content)

                st.write(e)