import streamlit as st

st.set_page_config(
    page_title="Career Agent",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Career Agent")
st.caption("Optimize your resume and LinkedIn profile for better job matches.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Resume Match")
    st.write("Upload your resume, paste a job description, and get a fit score, rewrite suggestions, and a side-by-side tailored draft.")

with col2:
    st.subheader("LinkedIn Optimizer")
    st.write("Paste your LinkedIn profile URL and upload your LinkedIn profile PDF or paste the profile text to get optimization suggestions.")

st.divider()

st.markdown("### What this app does")
st.write("- Resume-to-job fit analysis")
st.write("- Tailored resume draft")
st.write("- LinkedIn headline and about section optimization")
st.write("- Before/after comparison for better readability")

st.info("Use the left sidebar to switch between pages.")