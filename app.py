import streamlit as st
import requests
import json

# ------------------------------------
# Page setup
# ------------------------------------
st.set_page_config(page_title="AI MCQ Quiz", layout="centered")
st.title("📘 AI‑Powered MCQ Quiz")

# ------------------------------------
# Load secrets
# ------------------------------------
API_KEY = st.secrets["WATSONX_API_KEY"]
PROJECT_ID = st.secrets["WATSONX_PROJECT_ID"]
ENDPOINT = st.secrets["WATSONX_ENDPOINT"]

# ------------------------------------
# Watsonx.ai call
# ------------------------------------
def get_mcq_from_watsonx():
    url = f"{ENDPOINT}/ml/v1/text/generation?version=2023-05-29"

    prompt = """
Generate ONE multiple choice question on Accounts Payable best practices.

Rules:
- Exactly 4 options
- Only one correct answer
- Output ONLY valid JSON
- Do NOT add markdown or text outside JSON

JSON format:
{
  "question": "...",
  "options": ["...", "...", "...", "..."],
  "correct_index": 0,
  "explanation": "..."
}
"""

    payload = {
        "model_id": "ibm/granite-8b-code-instruct",
        "project_id": PROJECT_ID,
        "input": prompt,
        "parameters": {
            "temperature": 0.4,
            "max_new_tokens": 300
        }
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    text_output = response.json()["results"][0]["generated_text"]
    return json.loads(text_output)

# ------------------------------------
# Session state
# ------------------------------------
if "mcq" not in st.session_state:
    st.session_state.mcq = get_mcq_from_watsonx()

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "score" not in st.session_state:
    st.session_state.score = 0

# ------------------------------------
# Display MCQ
# ------------------------------------
mcq = st.session_state.mcq

st.subheader("Question")
st.write(mcq["question"])

selected_index = st.radio(
    "Select an option:",
    range(len(mcq["options"])),
    format_func=lambda x: mcq["options"][x],
    index=None,
    disabled=st.session_state.submitted
)

# ------------------------------------
# Submit logic
# ------------------------------------
if st.button("✅ Submit", disabled=st.session_state.submitted):
    st.session_state.submitted = True

    if selected_index == mcq["correct_index"]:
        st.session_state.score += 1
        st.success("Correct ✅")
    else:
        st.error("Incorrect ❌")

    st.info(f"Explanation: {mcq['explanation']}")

# ------------------------------------
# Next question
# ------------------------------------
if st.session_state.submitted:
    if st.button("➡️ Next Question"):
        st.session_state.mcq = get_mcq_from_watsonx()
        st.session_state.submitted = False
        st.rerun()

st.markdown(f"**Score:** {st.session_state.score}")
