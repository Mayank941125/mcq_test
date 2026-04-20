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
# IAM Token (cached)
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
            raise ValueError("No JSON found")
        return json.loads(text[start:end])

# --------------------------------------------------
# Content quality checks
# --------------------------------------------------
def is_meaningful_option(option):
    bad_patterns = ["option", "choice", "answer", "placeholder"]
    text = option.lower().strip()

    if len(text) < 6:
        return False

    for bad in bad_patterns:
        if text == bad or text.startswith(bad + " "):
            return False

    return True

def is_valid_mcq(mcq):
    if not (
        isinstance(mcq, dict)
        and isinstance(mcq.get("question"), str)
        and isinstance(mcq.get("options"), list)
        and len(mcq["options"]) == 4
        and isinstance(mcq.get("correct_index"), int)
        and 0 <= mcq["correct_index"] < 4
        and isinstance(mcq.get("explanation"), str)
    ):
        return False

    if len(mcq["question"].strip()) < 15:
        return False

    if len(set(mcq["options"])) < 4:
        return False

    for opt in mcq["options"]:
        if not is_meaningful_option(opt):
            return False

    if len(mcq["explanation"].strip()) < 20:
        return False

    return True

# --------------------------------------------------
# Prompt builder (prevents repetition + placeholders)
# --------------------------------------------------
def build_prompt(previous_questions):
    recent = "\n".join(previous_questions[-5:]) or "None"

    return f"""
Generate ONE NEW multiple-choice question on Accounts Payable best practices.

IMPORTANT:
- Do NOT repeat any of these previous questions:
{recent}

STRICT RULES:
- Exactly 4 options
- Each option must describe a concrete Accounts Payable activity
- DO NOT use placeholders like "Option 1", "Choice A", etc.
- Options must be realistic and distinct
- Only ONE option is correct
- Output ONLY valid JSON
- No markdown
- No commentary

JSON format:
{{
  "question": "string",
  "options": ["string","string","string","string"],
  "correct_index": 0,
  "explanation": "string"
}}
"""

# --------------------------------------------------
# Watsonx.ai MCQ generator (retry + fallback)
# --------------------------------------------------
def get_mcq_from_watsonx(max_retries=3):

    fallback_mcq = {
        "question": "Which approval is required for invoices above ₹50,000?",
        "options": [
            "Processing invoices without any approval",
            "Requiring two levels of documented approval",
            "Paying invoices immediately upon receipt",
            "Allowing vendors to self-approve invoices"
        ],
        "correct_index": 1,
        "explanation": (
            "Invoices above approval thresholds typically require two levels "
            "of documented approval to ensure control and compliance."
        )
    }

    for attempt in range(max_retries):
        try:
            token = get_iam_token(API_KEY)
            url = f"{ENDPOINT}/ml/v1/text/generation?version=2023-05-29"

            prompt = build_prompt(st.session_state.asked_questions)

            payload = {
                "model_id": "ibm/granite-8b-code-instruct",
                "project_id": PROJECT_ID,
                "input": prompt,
                "parameters": {
                    "temperature": 0.75,
                    "max_new_tokens": 350
                }
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            r = requests.post(url, headers=headers, json=payload, timeout=30)

            if r.status_code != 200:
                raise RuntimeError(f"watsonx error {r.status_code}")

            raw = r.json()["results"][0]["generated_text"]
            mcq = safe_parse_json(raw)

            if not is_valid_mcq(mcq):
                raise ValueError("MCQ failed semantic validation")

            st.session_state.asked_questions.append(mcq["question"])
            return mcq

        except Exception as e:
            print(f"Attempt {attempt + 1} failed:", e)

    return fallback_mcq

# --------------------------------------------------
# Session state
# --------------------------------------------------
if "asked_questions" not in st.session_state:
    st.session_state.asked_questions = []

if "mcq" not in st.session_state:
    st.session_state.mcq = get_mcq_from_watsonx()

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "score" not in st.session_state:
    st.session_state.score = 0

# --------------------------------------------------
# UI
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
