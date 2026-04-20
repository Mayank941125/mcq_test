import streamlit as st
import requests
import json

# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(page_title="AI MCQ Quiz", layout="centered")
st.title("📘 AI‑Powered MCQ Quiz")

# --------------------------------------------------
# Secrets (Streamlit Cloud → App → Settings → Secrets)
# --------------------------------------------------
API_KEY = st.secrets["WATSONX_API_KEY"]
PROJECT_ID = st.secrets["WATSONX_PROJECT_ID"]
ENDPOINT = st.secrets["WATSONX_ENDPOINT"]

# --------------------------------------------------
# IAM Token handling (cached)
# --------------------------------------------------
@st.cache_data(ttl=3500)
def get_iam_token(api_key):
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "apikey": api_key,
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey"
    }
    r = requests.post(url, headers=headers, data=data)
    r.raise_for_status()
    return r.json()["access_token"]

# --------------------------------------------------
# Safe JSON parsing
# --------------------------------------------------
def safe_parse_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("No JSON found in output")
        return json.loads(text[start:end])

# --------------------------------------------------
# Validate MCQ structure
# --------------------------------------------------
def is_valid_mcq(mcq):
    return (
        isinstance(mcq, dict)
        and "question" in mcq
        and "options" in mcq
        and isinstance(mcq["options"], list)
        and len(mcq["options"]) == 4
        and "correct_index" in mcq
        and isinstance(mcq["correct_index"], int)
        and 0 <= mcq["correct_index"] < 4
        and "explanation" in mcq
    )

# --------------------------------------------------
# Watsonx.ai MCQ Generator (with retry + fallback)
# --------------------------------------------------
def get_mcq_from_watsonx(max_retries=3):

    fallback_mcq = {
        "question": "Which approval is required for invoices above ₹50,000?",
        "options": [
            "Single approval",
            "Two-level approval",
            "Finance approval only",
            "No approval required"
        ],
        "correct_index": 1,
        "explanation": "Invoices above ₹50,000 generally require two-level approval."
    }

    for attempt in range(max_retries):
        try:
            token = get_iam_token(API_KEY)
            url = f"{ENDPOINT}/ml/v1/text/generation?version=2023-05-29"

            prompt = """
Generate ONE multiple-choice question on Accounts Payable best practices.

STRICT RULES:
- Exactly 4 options
- Only ONE correct answer
- Output ONLY valid JSON
- No markdown
- No extra text

JSON:
{
  "question": "string",
  "options": ["string","string","string","string"],
  "correct_index": 0,
  "explanation": "string"
}
"""

            payload = {
                "model_id": "ibm/granite-8b-code-instruct",
                "project_id": PROJECT_ID,
                "input": prompt,
                "parameters": {
                    "temperature": 0.3,
                    "max_new_tokens": 300
                }
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            r = requests.post(url, headers=headers, json=payload, timeout=30)

            if r.status_code != 200:
                raise RuntimeError(f"watsonx status {r.status_code}")

            raw_text = r.json()["results"][0]["generated_text"]
            mcq = safe_parse_json(raw_text)

            if not is_valid_mcq(mcq):
                raise ValueError("Invalid MCQ structure")

            return mcq

        except Exception as e:
            print(f"MCQ generation attempt {attempt+1} failed:", e)

    return fallback_mcq

# --------------------------------------------------
# Session state
# --------------------------------------------------
if "mcq" not in st.session_state:
    st.session_state.mcq = get_mcq_from_watsonx()

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "score" not in st.session_state:
    st.session_state.score = 0

# --------------------------------------------------
# UI Rendering
# --------------------------------------------------
mcq = st.session_state.mcq

st.subheader("Question")
st.write(mcq["question"])

selected = st.radio(
    "Select one option:",
    range(4),
    format_func=lambda i: mcq["options"][i],
    index=None,
    disabled=st.session_state.submitted
)

if st.button("✅ Submit", disabled=st.session_state.submitted):
    st.session_state.submitted = True
    if selected == mcq["correct_index"]:
        st.session_state.score += 1
        st.success("Correct ✅")
    else:
        st.error("Incorrect ❌")
    st.info(mcq["explanation"])

if st.session_state.submitted:
    if st.button("➡️ Next Question"):
        st.session_state.mcq = get_mcq_from_watsonx()
        st.session_state.submitted = False
        st.rerun()

st.markdown(f"### 🏆 Score: {st.session_state.score}")
