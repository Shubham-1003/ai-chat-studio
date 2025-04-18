# app.py (Simplified - Standard Uploader Above Chat Input, Immediate Processing)

import streamlit as st
from PIL import Image
import io
import os
from utils import llm_api, file_parser

# --- Page Configuration ---
st.set_page_config(
    page_title="FreeLM",
    page_icon="✨",
    layout="wide"
)

# --- Custom CSS ---
def load_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found at {file_path}. Using default styles.")

# Load base CSS ONLY
load_css("css/style.css")
# REMOVE ALL other custom CSS added in previous attempts

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_model" not in st.session_state:
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    st.session_state.selected_model = available_models[0] if available_models else None
if "api_keys" not in st.session_state:
    st.session_state.api_keys = {}
if "uploaded_file_data" not in st.session_state: # Holds processed context data for LLM
    st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state:
    st.session_state.stop_app = False
# REMOVE staged_files state

# --- Helper Functions ---
def display_processed_file_card(filename, metadata):
    """Displays a card for a fully processed file in the sidebar."""
    file_type = metadata.get("type", "unknown")
    file_size = metadata.get("size", 0)
    content_preview = st.session_state.uploaded_file_data[filename].get("content", "")
    if isinstance(content_preview, str) and len(content_preview) > 100:
        content_preview = content_preview[:100] + "..."
    elif not isinstance(content_preview, str):
        content_preview = f"[{file_type} content]"

    with st.expander(f"📄 {filename} ({file_type} - {file_size / 1024:.1f} KB)", expanded=False):
        st.markdown(f"**Preview:**")
        if isinstance(content_preview, str):
            st.code(content_preview, language=None)
        else:
            st.text(content_preview)

# --- Sidebar ---
with st.sidebar:
    st.title("✨ AI Chat Studio")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.session_state.uploaded_file_data = {} # Clear processed files context
        st.rerun()
    st.markdown("---")
    # --- Model Selection ---
    st.subheader("🤖 Model Selection")
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models: st.error("No models configured."); st.stop()
    if st.session_state.selected_model not in available_models: st.session_state.selected_model = available_models[0]
    selected_model_display_name = st.selectbox(
        "Choose an LLM:", options=available_models,
        index=available_models.index(st.session_state.selected_model), key="model_selector"
    )
    # Internal API Key Check
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    st.session_state.api_keys = {}; st.session_state.stop_app = False
    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets:
            st.session_state.api_keys[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
        else: st.session_state.stop_app = True
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name; st.rerun()
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")
    # --- Display Processed Files ---
    # This section lists files that are part of the overall chat context
    if st.session_state.uploaded_file_data:
        st.subheader("Chat Context Files")
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                data = st.session_state.uploaded_file_data[filename]
                display_processed_file_card(filename, data["metadata"]) # Display card
        # Add Clear button
        if st.button("Clear All Context Files"):
            st.session_state.uploaded_file_data = {}; st.toast("Cleared all files from chat context."); st.rerun()
        st.markdown("---")
    else:
        st.caption("Upload files below to add context to the chat.")


# --- Main Chat Area ---
st.header(f"Chat with {st.session_state.selected_model}")

# --- Display Chat Messages ---
message_container = st.container()
with message_container:
    if not st.session_state.messages:
        # Optionally add height or placeholder if you want space above uploader when chat is empty
        # message_container.write(" " * 10) # Hacky way to add space
        pass
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display generated files if any
            if "generated_files" in message and message["generated_files"]:
                for file_info in message["generated_files"]:
                    pass # Simplified

# --- File Upload Area (Placed Above Chat Input) ---
upload_area = st.container()
with upload_area:
    # Use a standard file uploader. Files processed immediately.
    uploaded_files = st.file_uploader(
        "Attach Files to Context (will be processed immediately)",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"],
        accept_multiple_files=True,
        label_visibility="visible",
        key="immediate_uploader"
    )

    # Immediate Processing Logic
    if uploaded_files:
        files_processed_count = 0
        # Use st.status for better feedback during processing
        with st.status(f"Processing {len(uploaded_files)} uploaded file(s)...", expanded=False) as status:
            for file in uploaded_files:
                if file.name not in st.session_state.uploaded_file_data:
                    st.write(f"Processing: {file.name}")
                    content, metadata = file_parser.process_uploaded_file(file)
                    if content is not None:
                        st.session_state.uploaded_file_data[file.name] = {
                            "content": content, "metadata": metadata
                        }
                        files_processed_count += 1
                    else:
                         st.write(f"⚠️ Failed to process {file.name}")
            status.update(label=f"Processing complete. Added {files_processed_count} new file(s) to context.", state="complete")

        if files_processed_count > 0:
            st.toast(f"Added {files_processed_count} file(s) to the chat context (see sidebar).")
            # Rerun required to update sidebar and clear the uploader widget
            st.rerun()
        elif uploaded_files: # Files were selected, but all existed already
             st.toast("Selected file(s) are already in the chat context.")
             # Rerun to clear the uploader widget state
             st.rerun()


# --- Chat Input (Standard - Will stick to bottom) ---
chat_input_disabled = st.session_state.stop_app
chat_placeholder = f"Ask {st.session_state.selected_model} anything..."
if chat_input_disabled:
    key_name = required_key_name_for_selected or "API Key"
    chat_placeholder = f"Cannot chat: {key_name} missing in secrets.toml"

prompt = st.chat_input(
    chat_placeholder,
    disabled=chat_input_disabled,
    key="chat_input_main"
)

# --- Handle Send Action ---
if prompt:
    # 1. Add User Message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Prepare context for LLM call (using existing processed files)
    history_for_llm = st.session_state.messages[-10:]
    file_context_for_llm = st.session_state.uploaded_file_data

    # 3. Get LLM Response and add to messages
    with st.chat_message("assistant"):
         message_placeholder = st.empty()
         message_placeholder.markdown("🧠 Thinking...")
         try:
             # (LLM API call logic remains the same)
             current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
             response_text, generated_file_info = llm_api.get_llm_response(
                 model_display_name=st.session_state.selected_model, messages=history_for_llm,
                 api_keys=st.session_state.api_keys, uploaded_file_context=file_context_for_llm,
                 model_capabilities=current_model_capabilities
             )
             message_placeholder.markdown(response_text)
             assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
             st.session_state.messages.append(assistant_message) # Add response to state

         except ValueError as ve: # Handle specific errors
              st.error(f"Configuration Error: {ve}")
              error_message = f"Sorry, could not get response: {ve}"
              st.session_state.messages.append({"role": "assistant", "content": error_message})
              message_placeholder.error(error_message)
         except Exception as e: # Handle generic errors
             st.error(f"An error occurred: {e}")
             error_message = f"Sorry, I encountered an error trying to get a response. Error: {e}"
             st.session_state.messages.append({"role": "assistant", "content": error_message})
             message_placeholder.error(error_message)

    # 4. Rerun (handled automatically by st.chat_input) to display new messages
    st.rerun()


# --- Display Stop App Warning (if applicable) ---
if st.session_state.stop_app:
     st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
