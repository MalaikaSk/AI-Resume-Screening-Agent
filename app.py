
# Placeholder: Due to response size limits, this generated file contains
# the scaffold for Version 2. Continue by merging your existing analysis
# section and adding the prompts below.
import os
import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from streamlit_echarts import st_echarts
import json,re

st.set_page_config(page_title="AI Career Copilot",page_icon="🚀",layout="wide")

st.markdown("""
<style>

.stButton>button{

    width:100%;

    height:60px;

    font-size:22px;

    font-weight:bold;

    border-radius:15px;

}

</style>
""", unsafe_allow_html=True)

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

llm=ChatGroq(model="llama-3.3-70b-versatile",temperature=0)

st.markdown(
    """
    <h1 style='text-align:center;'>
        🚀 AI Career Copilot
    </h1>

    <p style='text-align:center;
              color:gray;
              font-size:18px;'>
        Resume Analysis • Interview Prep • Salary Estimate • Cover Letter
    </p>
    """,
    unsafe_allow_html=True
)

resume=st.file_uploader("Upload Resume",type="pdf")
jd=st.text_area("Paste Job Description",height=220)

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


def ask(prompt):
    return llm.invoke(prompt).content

if resume and jd and st.button("Analyze"):
    reader=PdfReader(resume)
    resume_text=""
    for p in reader.pages:
        t=p.extract_text()
        if t:
            resume_text+=t

    tab1,tab2,tab3,tab4=st.tabs([
        "📊 Analysis",
        "🎯 Interview Q&A",
        "💰 Salary",
        "✉️ Cover Letter"
    ])

    with tab1:
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
{jd}
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

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                show_score_gauge(score)

            with col2:
                st.metric("✅ Matching Skills", len(data["matching_skills"]))

            with col3:
                st.metric("❌ Missing Skills", len(data["missing_skills"]))

            with col4:
                st.metric("📌 Recommendation", data["recommendation"])

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
                st.success(f"Strong Match - {data['recommendation']}")
            elif score >= 60:
                st.warning(f"Potential Match - {data['recommendation']}")
            else:
                st.error(f"Weak Match - {data['recommendation']}")

        except Exception as e:
            st.error("Could not parse AI response")
            st.write(response.content)
            st.write(e)

    with tab2:
        with st.spinner("Generating interview questions..."):
            interview_prompt=f"""
You are a Senior Technical Interviewer.

Using the resume and JD generate exactly 10 interview questions.

Return in markdown.

For EACH question include:

Question
Ideal Answer
What interviewer expects
Difficulty

Resume:
{resume_text}

JD:
{jd}
"""
            st.markdown(ask(interview_prompt))

    with tab3:
        with st.spinner("Estimating salary..."):
            salary_prompt=f"""
Estimate salary based on resume and JD.

Return:

Minimum Salary
Expected Salary
Stretch Salary
Reasoning
Skills increasing salary
Missing skills affecting salary

Resume:
{resume_text}

JD:
{jd}
"""
            st.markdown(ask(salary_prompt))

    with tab4:
        with st.spinner("Generating cover letter..."):
            cover_prompt=f"""
Write a professional ATS-friendly cover letter.

Use the resume and JD.

Keep it below 300 words.

Resume:
{resume_text}

JD:
{jd}
"""
            cover=ask(cover_prompt)
            st.markdown(cover)
            st.download_button(
                "📥 Download Cover Letter",
                cover,
                file_name="Cover_Letter.txt"
            )
            
            
            
st.markdown("---")
st.markdown(
"""
<center>

Built with ❤️ using Streamlit + Groq + Llama 3.3

© 2026 Malaika Shaikh

</center>
""",
unsafe_allow_html=True
)

