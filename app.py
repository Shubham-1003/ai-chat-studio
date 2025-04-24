# app.py

import streamlit as st
from utils.llm_api import get_llm_response

# Set Streamlit page config
st.set_page_config(page_title="Multi-LLM Chat", layout="wide")

st.title("🧠 Chat with Multiple LLM APIs")

# Sidebar for model selection
with st.sidebar:
    st.header("Choose Your Model")
    model = st.selectbox("Select Model", [
        "meta/llama3-8b-instruct",
        "mistralai/mixtral-8x7b-instruct",
        "google/gemma-7b-it",
        "phi3",
        "openhermes",
        "dolphin-mixtral"
    ])

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Prompt for new input
if prompt := st.chat_input("Ask your question here..."):
    # Add user message to session
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response from LLM
    with st.chat_message("assistant"):
        response = get_llm_response(prompt, model)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
