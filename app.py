import streamlit as st
import requests
import json

# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="AI MCQ Quiz",
    layout="centered"
)

st.title("📘 AI‑Powered MCQ Quiz")

# --------------------------------------------------
# Load secrets (from Streamlit Cloud → Secrets)
# --------------------------------------------------
API_KEY = st.secrets["WATSONX_API_KEY"]
PROJECT_ID = st.secrets["WATSONX_PROJECT_ID"]
ENDPOINT = st.secrets["WATSONX_ENDPOINT"]

# --------------------------------------------------
# Get IAM access token (REQUIRED for watsonx.ai)
# --------------------------------------------------
def get_iam_token(api_key):
    iam_url = "https://iam.cloud.ibm.com/identity/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "apikey": api_key,
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey"
    }

    response = requests.post(iam_url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

# --------------------------------------------------
# Call watsonx.ai to generate an MCQ
# --------------------------------------------------
def get_mcq_from_watsonx():
    iam_token = get_iam_token(API_KEY)

    url = f"{ENDPOINT}/ml/v1/text/generation?version=2023-05-29"

    prompt = """
Generate ONE multiple choice question on Accounts Payable best practices.

Rules:
- Exactly 4 options
- Only ONE correct answer
- Output ONLY valid JSON
- Do NOT include markdown or extra text

JSON format:
{
  "question": "string",
  "options": ["option1", "option2", "option3", "option4"],
  "correct_index": 0,
  "explanation": "string"
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
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    generated_text = response.json()["results"][0]["generated_text"]

    # Convert model output (string) to JSON
    return json.loads(generated_text)

# --------------------------------------------------
# Session state initialization
# --------------------------------------------------
if "mcq" not in st.session_state:
    st.session_state.mcq = get_mcq_from_watsonx()

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "score" not in st.session_state:
    st.session_state.score = 0

# --------------------------------------------------
# Display MCQ
# --------------------------------------------------
mcq = st.session_state.mcq

st.subheader("Question")
st.write(mcq["question"])

selected_index = st.radio(
    "Select one option:",
    options=list(range(len(mcq["options"]))),
    format_func=lambda x: mcq["options"][x],
    index=None,
    disabled=st.session_state.submitted
)

# --------------------------------------------------
# Submit logic
# --------------------------------------------------
if st.button("✅ Submit", disabled=st.session_state.submitted):
    st.session_state.submitted = True

    if selected_index == mcq["correct_index"]:
        st.session_state.score += 1
        st.success("Correct ✅")
    else:
        st.error("Incorrect ❌")

