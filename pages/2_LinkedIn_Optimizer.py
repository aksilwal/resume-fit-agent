import io
import json
import os

import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document

st.set_page_config(page_title="LinkedIn Optimizer", page_icon="💼", layout="wide")


def read_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages).strip()


def read_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extract_profile_text(uploaded_file) -> str:
    file_bytes = uploaded_file.getvalue()
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return read_pdf(file_bytes)
    if name.endswith(".docx"):
        return read_docx(file_bytes)
    if name.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")

    raise ValueError("Unsupported file type. Please upload PDF, DOCX, or TXT.")


def build_linkedin_prompt(profile_text: str, linkedin_url: str, target_role: str) -> str:
    return f"""
You are a strict LinkedIn profile optimizer.

Analyze the LinkedIn profile content and improve it for recruiter visibility, keyword matching, clarity, personal branding, and job search effectiveness.

Rules:
- Do not fabricate experience.
- Do not recommend lying.
- Keep everything truthful and professional.
- Improve wording, structure, and keyword relevance.
- Generate polished content that sounds strong but realistic.

Return valid JSON only with this schema:
{{
  "linkedin_score": 0,
  "summary": "",
  "strengths": [""],
  "headline_current_assessment": "",
  "headline_improved": "",
  "about_improved": "",
  "experience_improvements": [""],
  "keywords_missing": [""],
  "profile_branding_tips": [""],
  "final_linkedin_profile_text": ""
}}

LinkedIn URL:
{linkedin_url}

Target Role:
{target_role}

LinkedIn Profile Content:
{profile_text}
"""


def call_gemini_linkedin(profile_text: str, linkedin_url: str, target_role: str) -> dict:
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Add it to Streamlit secrets or your environment.")

    client = genai.Client(api_key=api_key)
    prompt = build_linkedin_prompt(profile_text, linkedin_url, target_role)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = (response.text or "").strip()
    if not text:
        raise ValueError("Model returned an empty response.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError("Could not parse model output as JSON.")


st.title("💼 LinkedIn Optimizer")
st.caption("Paste your LinkedIn URL and upload your LinkedIn profile PDF or text for improvement suggestions.")

with st.sidebar:
    st.header("How to use")
    st.write("1. Paste your LinkedIn profile URL")
    st.write("2. Upload LinkedIn profile PDF, DOCX, or TXT")
    st.write("3. Optionally add your target role")
    st.write("4. Click Analyze")

linkedin_url = st.text_input("LinkedIn profile URL", placeholder="https://www.linkedin.com/in/yourprofile")
target_role = st.text_input("Target role", placeholder="e.g. IT Support Technician")
uploaded_profile = st.file_uploader("Upload LinkedIn profile content", type=["pdf", "docx", "txt"])

analyze = st.button("Analyze LinkedIn Profile", type="primary", use_container_width=True)

if analyze:
    if not linkedin_url.strip():
        st.error("Please paste your LinkedIn profile URL.")
        st.stop()

    if not uploaded_profile:
        st.error("Please upload your LinkedIn profile PDF, DOCX, or TXT file.")
        st.stop()

    uploaded_file_bytes = uploaded_profile.getvalue()

    try:
        with st.spinner("Analyzing LinkedIn profile..."):
            profile_text = extract_profile_text(uploaded_profile)
            result = call_gemini_linkedin(profile_text, linkedin_url, target_role)

        st.success("LinkedIn analysis complete.")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.metric("LinkedIn Score", f"{result.get('linkedin_score', 'N/A')}/100")

        with col2:
            st.subheader("Summary")
            st.write(result.get("summary", "No summary returned."))

        tabs = st.tabs([
            "Strengths",
            "Headline",
            "About",
            "Experience",
            "Keywords",
            "Branding Tips",
            "Raw JSON"
        ])

        with tabs[0]:
            strengths = result.get("strengths", [])
            if not strengths:
                st.info("No strengths returned.")
            for item in strengths:
                st.write(f"- {item}")

        with tabs[1]:
            st.write("**Current Headline Assessment**")
            st.write(result.get("headline_current_assessment", "No assessment returned."))
            st.write("**Improved Headline**")
            st.code(result.get("headline_improved", ""))

        with tabs[2]:
            st.write("**Improved About Section**")
            st.text_area("About", result.get("about_improved", ""), height=220)

        with tabs[3]:
            improvements = result.get("experience_improvements", [])
            if not improvements:
                st.info("No experience improvements returned.")
            for item in improvements:
                st.write(f"- {item}")

        with tabs[4]:
            keywords = result.get("keywords_missing", [])
            if not keywords:
                st.info("No missing keywords returned.")
            for item in keywords:
                st.write(f"- {item}")

        with tabs[5]:
            tips = result.get("profile_branding_tips", [])
            if not tips:
                st.info("No branding tips returned.")
            for item in tips:
                st.write(f"- {item}")

        with tabs[6]:
            st.json(result)

        st.divider()
        st.subheader("LinkedIn Comparison")

        left_col, right_col = st.columns(2)

        with left_col:
            st.markdown("### Current LinkedIn Content")
            if uploaded_profile.name.lower().endswith(".pdf"):
                try:
                    st.pdf(uploaded_file_bytes)
                except Exception:
                    st.text_area("Extracted LinkedIn Text", profile_text, height=700)
            else:
                st.text_area("Extracted LinkedIn Text", profile_text, height=700)

        with right_col:
            st.markdown("### Optimized LinkedIn Profile")
            st.text_area(
                "Improved LinkedIn Profile",
                result.get("final_linkedin_profile_text", ""),
                height=700
            )

    except Exception as e:
        st.error(f"Error: {e}")
