import streamlit as st
from utils.llm_api import get_response

st.set_page_config(page_title="LLM Chat App", layout="wide")

# Apply a cleaner, modern design
st.markdown(
    """
    <style>
    .main {
        background-color: #f4f4f9;
    }
    .stTextInput>div>div>input {
        background-color: white;
    }
    .stChatMessage {
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🧠 LLM Chat Interface")

with st.sidebar:
    st.header("Model Settings")
    model_name = st.selectbox("Select LLM Model", options=["Gemini", "OpenAI", "Claude", "Mistral", "Groq"])
    temperature = st.slider("Temperature", 0.0, 1.0, 0.5)
    max_tokens = st.slider("Max Tokens", 100, 2048, 512)
    api_key = st.text_input("API Key (if required)", type="password")

# Store the chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for i, (role, msg) in enumerate(st.session_state.chat_history):
    with st.chat_message(role):
        st.markdown(msg)

user_input = st.chat_input("Ask your question...")

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                output = get_response(user_input, model=model_name, temperature=temperature, max_tokens=max_tokens, api_key=api_key)
                st.markdown(output)
                st.session_state.chat_history.append(("assistant", output))
            except Exception as e:
                st.error(f"Error communicating with LLM API: {e}")
