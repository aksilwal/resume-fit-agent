import io
import json
import os

import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document

st.set_page_config(page_title="Resume Fit Agent", page_icon="📄", layout="wide")


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


def extract_resume_text(uploaded_file) -> str:
    file_bytes = uploaded_file.getvalue()
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return read_pdf(file_bytes)
    if name.endswith(".docx"):
        return read_docx(file_bytes)
    if name.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")

    raise ValueError("Unsupported file type. Please upload PDF, DOCX, or TXT.")


def build_prompt(resume_text: str, job_description: str) -> str:
    return f"""
You are a strict resume-job fit evaluator.

Analyze the candidate resume against the job description.

Rules:
- Do not fabricate experience.
- Do not recommend lying.
- Keep suggestions truthful and ATS-friendly.
- Highlight what is missing, weak, or vague.
- Rewrite bullets only based on the existing resume content.
- Be direct and practical.
- Also generate a full improved resume draft based only on the existing resume content.
- You must always return a non-empty "tailored_resume_text" field containing the full updated resume draft.

Return valid JSON only with this schema:
{{
  "fit_score": 0,
  "summary": "",
  "strengths": [""],
  "must_fix_gaps": [""],
  "nice_to_have_gaps": [""],
  "ats_keywords_to_add": [""],
  "bullet_rewrites": [
    {{
      "original": "",
      "improved": "",
      "reason": ""
    }}
  ],
  "section_suggestions": [""],
  "red_flags": [""],
  "final_verdict": "",
  "tailored_resume_text": ""
}}

Resume:
{resume_text}

Job Description:
{job_description}
"""


def call_gemini(resume_text: str, job_description: str) -> dict:
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Add it to Streamlit secrets or your environment.")

    client = genai.Client(api_key=api_key)
    prompt = build_prompt(resume_text, job_description)

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


st.title("📄 Resume Fit Agent")
st.caption("Upload your resume, paste a job description, and get fit analysis plus resume improvement suggestions.")

with st.sidebar:
    st.header("How to use")
    st.write("1. Upload your resume")
    st.write("2. Paste the job description from Indeed")
    st.write("3. Click Analyze")
    st.write("4. Review gaps, keywords, bullet rewrites, and resume comparison")

uploaded_resume = st.file_uploader("Upload resume", type=["pdf", "docx", "txt"])
job_description = st.text_area(
    "Paste the job description here",
    height=300,
    placeholder="Paste the full Indeed job description here...",
)

analyze = st.button("Analyze fit", type="primary", use_container_width=True)

if analyze:
    if not uploaded_resume:
        st.error("Please upload a resume first.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste the job description.")
        st.stop()

    uploaded_file_bytes = uploaded_resume.getvalue()

    try:
        with st.spinner("Reading resume and analyzing fit..."):
            resume_text = extract_resume_text(uploaded_resume)
            result = call_gemini(resume_text, job_description)

        st.success("Analysis complete.")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Fit score", f"{result.get('fit_score', 'N/A')}/100")
            st.subheader("Final verdict")
            st.write(result.get("final_verdict", "No verdict returned."))

        with col2:
            st.subheader("Summary")
            st.write(result.get("summary", "No summary returned."))

        tabs = st.tabs([
            "Strengths",
            "Must fix",
            "Nice to have",
            "ATS keywords",
            "Bullet rewrites",
            "Sections",
            "Red flags",
            "Raw JSON",
        ])

        with tabs[0]:
            strengths = result.get("strengths", [])
            if not strengths:
                st.info("No strengths returned.")
            for item in strengths:
                st.write(f"- {item}")

        with tabs[1]:
            must_fix = result.get("must_fix_gaps", [])
            if not must_fix:
                st.info("No must-fix gaps returned.")
            for item in must_fix:
                st.write(f"- {item}")

        with tabs[2]:
            nice_to_have = result.get("nice_to_have_gaps", [])
            if not nice_to_have:
                st.info("No nice-to-have gaps returned.")
            for item in nice_to_have:
                st.write(f"- {item}")

        with tabs[3]:
            keywords = result.get("ats_keywords_to_add", [])
            if not keywords:
                st.info("No ATS keywords returned.")
            for item in keywords:
                st.write(f"- {item}")

        with tabs[4]:
            rewrites = result.get("bullet_rewrites", [])
            if not rewrites:
                st.info("No rewrites returned.")
            for idx, item in enumerate(rewrites, start=1):
                st.markdown(f"**Rewrite {idx}**")
                st.write("Original:")
                st.code(item.get("original", ""))
                st.write("Improved:")
                st.code(item.get("improved", ""))
                st.write("Reason:")
                st.write(item.get("reason", ""))
                st.divider()

        with tabs[5]:
            sections = result.get("section_suggestions", [])
            if not sections:
                st.info("No section suggestions returned.")
            for item in sections:
                st.write(f"- {item}")

        with tabs[6]:
            red_flags = result.get("red_flags", [])
            if not red_flags:
                st.info("No red flags returned.")
            for item in red_flags:
                st.write(f"- {item}")

        with tabs[7]:
            st.json(result)

        st.divider()
        st.subheader("Resume Comparison")

        left_col, right_col = st.columns(2)

        with left_col:
            st.markdown("### Current Resume")
            if uploaded_resume.name.lower().endswith(".pdf"):
                try:
                    st.pdf(uploaded_file_bytes)
                except Exception:
                    st.info("PDF preview is not available in this Streamlit version.")
                    st.text_area("Extracted Resume Text", resume_text, height=700)
            else:
                st.text_area("Extracted Resume Text", resume_text, height=700)

        with right_col:
            st.markdown("### Tailored Resume")
            tailored_resume_text = result.get("tailored_resume_text", "")
            if not tailored_resume_text:
                st.warning("No tailored resume draft was returned.")
            st.text_area("Improved Resume Draft", tailored_resume_text, height=700)

    except Exception as e:
        st.error(f"Error: {e}")