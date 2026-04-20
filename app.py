import streamlit as st

# -------------------------------
# Page configuration
# -------------------------------
st.set_page_config(
    page_title="MCQ Quiz",
    layout="centered"
)

st.title("📘 MCQ Quiz Demo")

# -------------------------------
# Sample MCQs (static for now)
# -------------------------------
MCQS = [
    {
        "question": "What is 2 + 2?",
        "options": ["1", "2", "3", "4"],
        "correct_index": 3,
        "explanation": "2 + 2 equals 4."
    },
    {
        "question": "Which approval is required for invoices above ₹50,000?",
        "options": [
            "Single approval",
            "Two-level approval",
            "Finance approval only",
            "No approval required"
        ],
        "correct_index": 1,
        "explanation": "Invoices above ₹50,000 require two-level approval."
    }
]

# -------------------------------
# Initialize session state
# -------------------------------
if "current_q" not in st.session_state:
    st.session_state.current_q = 0

if "score" not in st.session_state:
    st.session_state.score = 0

if "answered" not in st.session_state:
    st.session_state.answered = False

# -------------------------------
# Load current question
# -------------------------------
mcq = MCQS[st.session_state.current_q]

st.subheader(f"Question {st.session_state.current_q + 1}")
st.write(mcq["question"])

selected_option = st.radio(
    "Select one option:",
    mcq["options"],
    index=None,
    disabled=st.session_state.answered
)

# -------------------------------
# Submit button
# -------------------------------
if st.button("✅ Submit", disabled=st.session_state.answered):
    st.session_state.answered = True

    if selected_option is not None:
        selected_index = mcq["options"].index(selected_option)

        if selected_index == mcq["correct_index"]:
            st.session_state.score += 1
            st.success("Correct ✅")
        else:
            st.error("Incorrect ❌")

        st.info(f"Explanation: {mcq['explanation']}")
    else:
        st.warning("Please select an option.")

# -------------------------------
# Next question / Finish
# -------------------------------
if st.session_state.answered:
    if st.session_state.current_q < len(MCQS) - 1:
        if st.button("➡️ Next Question"):
            st.session_state.current_q += 1
            st.session_state.answered = False
            st.rerun()
    else:
        st.success("🎉 Quiz Completed!")
        st.write(f"**Your Score:** {st.session_state.score} / {len(MCQS)}")

        if st.button("🔄 Restart Quiz"):
            st.session_state.current_q = 0
            st.session_state.score = 0
            st.session_state.answered = False
            st.rerun()

