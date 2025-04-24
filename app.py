# app.py

import streamlit as st
from PIL import Image
import os
from utils import llm_api, file_parser

# --- Page Configuration ---
st.set_page_config(
    page_title="Gemini-Style LLM Chat",
    page_icon="✨",
    layout="wide"
)

# --- Load Custom CSS ---
def load_css():
    st.markdown("""
    <style>
      html, body {
        height: 100%;
        font-family: 'Inter', 'Roboto', Arial, sans-serif;
        background: #fcfcfd;
        color: #151718;
      }
      .gradient-text {
        background: linear-gradient(90deg, #12c2e9 30%, #c471ed 60%, #f64f59 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      .chat-input:focus {
        outline: none;
        border-color: #4f8cff;
        background: #fff;
      }
    </style>
    """, unsafe_allow_html=True)

load_css()

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_model" not in st.session_state:
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    st.session_state.selected_model = available_models[0] if available_models else None
if "api_keys" not in st.session_state:
    st.session_state.api_keys = {}
if "uploaded_file_data" not in st.session_state:
    st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state:
    st.session_state.stop_app = False

# --- Sidebar ---
with st.sidebar:
    st.title("✨ Gemini 2.0 Flash")
    st.markdown("---")
    st.subheader("🤖 Choose Model")
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models:
        st.error("No models configured. Please check your settings.")
        st.stop()

    selected_model_display_name = st.selectbox(
        "Select an LLM:",
        options=available_models,
        index=available_models.index(st.session_state.selected_model)
    )

    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name
        st.rerun()

    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")
    st.caption("API Keys managed via `.streamlit/secrets.toml`")

# --- Main Chat Interface ---
st.title("Meet :rainbow[Gemini], your personal AI assistant")

prompt_suggestions = [
    ("💡", "Explain something"),
    ("⏱️", "Save me time"),
    ("✨", "Inspire me"),
    ("💻", "Write a python script to monitor system performance")
]

st.markdown("## What can I help you with?")
cols = st.columns(len(prompt_suggestions))
for col, (icon, prompt) in zip(cols, prompt_suggestions):
    if col.button(f"{icon} {prompt}"):
        st.session_state.messages.append({"role": "user", "content": prompt})

# --- Display Chat Messages ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# --- Chat Input ---
if user_input := st.chat_input("Ask Gemini"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    try:
        response = llm_api.get_response(
            model_name=st.session_state.selected_model,
            messages=st.session_state.messages
        )
        st.session_state.messages.append({"role": "assistant", "content": response})
    except Exception as e:
        st.error(f"Error fetching response: {e}")

# --- Footer ---
st.markdown("""
<div style='text-align: center; font-size: small; color: gray;'>
  Google Terms and the <a href="#" style='color: #3b82f6;'>Google Privacy Policy</a> apply. Gemini can make mistakes, so double-check it.
</div>
""", unsafe_allow_html=True)
