# app.py

import streamlit as st
from utils.llm_api import get_llm_response, check_llm_server

# Set Streamlit page config
st.set_page_config(page_title="Multi-LLM Chat", layout="wide")
st.title("🧠 Chat with Multiple LLM APIs")

# Sidebar for model selection
with st.sidebar:
    st.header("Choose Your Model")
    selected_model = st.selectbox("Select Model", [
        "meta/llama3-8b-instruct",
        "mistralai/mixtral-8x7b-instruct",
        "google/gemma-7b-it",
        "phi3",
        "openhermes",
        "dolphin-mixtral"
    ])
    st.markdown(f"**Selected Model:** `{selected_model}`")

# Show warning if server is down
if not check_llm_server():
    st.error("❌ LLM server is not reachable. Please start Ollama or check port 11434.")
    st.stop()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input for new prompt
if prompt := st.chat_input("Ask your question here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get and show LLM response
    with st.chat_message("assistant"):
        response = get_llm_response(prompt, selected_model)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
