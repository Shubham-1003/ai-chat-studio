# app.py (Simplified - Immediate Processing, Standard Layout)

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

# REMOVE ALL custom CSS trying to position elements or hide uploader parts
# Minimal CSS only if absolutely needed for minor tweaks later

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
# if "staged_files" not in st.session_state:
#     st.session_state.staged_files = {}

# --- Helper Functions ---
def display_processed_file_card(filename, metadata):
    """Displays a card for a fully processed file in the sidebar."""
    # (Function remains the same)
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
        # st.session_state.staged_files = {} # No staging anymore
        st.rerun()
    st.markdown("---")
    # --- Model Selection (remains the same) ---
    st.subheader("🤖 Model Selection")
    # (Code remains the same)
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models: st.error("No models configured."); st.stop()
    if st.session_state.selected_model not in available_models: st.session_state.selected_model = available_models[0]
    selected_model_display_name = st.selectbox(
        "Choose an LLM:", options=available_models,
        index=available_models.index(st.session_state.selected_model), key="model_selector"
    )
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
    # --- Display Processed Files (remains the same) ---
    if st.session_state.uploaded_file_data:
        st.subheader("Chat Context Files")
        # (Code remains the same)
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                data = st.session_state.uploaded_file_data[filename]
                display_processed_file_card(filename, data["metadata"])
            else: pass
        if st.button("Clear All Context Files"):
            st.session_state.uploaded_file_data = {}; st.toast("Cleared all files from chat context."); st.rerun()
        st.markdown("---")

# --- Main Chat Area ---
st.header(f"Chat with {st.session_state.selected_model}")

# --- Display Chat Messages ---
# This container holds the conversation history
message_container = st.container()
# Give the container some height or let it grow naturally
# Maybe add min-height via CSS if needed later, but avoid complex positioning
with message_container:
    if not st.session_state.messages:
        st.caption("Conversation will appear here.") # Placeholder if empty
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display generated files if any
            if "generated_files" in message and message["generated_files"]:
                 for file_info in message["generated_files"]:
                    # (Code for download link)
                    pass

# --- File Upload Area (Normal Flow - Above Chat Input) ---
# This container holds the uploader
upload_area = st.container()
with upload_area:
    # REMOVE STAGING DISPLAY AREA
    # if st.session_state.staged_files: ...

    # Standard File Uploader
    uploaded_files = st.file_uploader(
        "Attach Files to Context (processed immediately)", # Clearer label
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"],
        accept_multiple_files=True,
        label_visibility="visible",
        key="immediate_uploader" # New key to avoid conflict
    )

    # Immediate Processing Logic
    if uploaded_files:
        files_processed_count = 0
        # Use status for better feedback during processing
        with st.status(f"Processing {len(uploaded_files)} file(s)...", expanded=False) as status:
            for file in uploaded_files:
                # Process if not already in the main context data
                if file.name not in st.session_state.uploaded_file_data:
                    st.write(f"Processing: {file.name}") # Update status area
                    content, metadata = file_parser.process_uploaded_file(file)
                    if content is not None:
                        st.session_state.uploaded_file_data[file.name] = {
                            "content": content, "metadata": metadata
                        }
                        files_processed_count += 1
                    else:
                         st.write(f"⚠️ Failed to process {file.name}")
                # else:
                    # Optionally notify if file with same name already exists
                    # st.write(f"ℹ️ File '{file.name}' already in context.")
            status.update(label=f"Processing complete. Added {files_processed_count} new file(s) to context.", state="complete")

        if files_processed_count > 0:
            st.toast(f"Added {files_processed_count} file(s) to the chat context (see sidebar).")
            # Rerun needed to update the sidebar display and clear the uploader widget state
            st.rerun()
        elif uploaded_files: # If files were selected but none were new
             st.toast("Selected file(s) are already in the chat context.")
             # Rerun to clear the uploader state
             st.rerun()


# --- Chat Input (Standard - Sticks to Bottom) ---
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
    # Files are already processed and in uploaded_file_data context
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Prepare context for LLM call
    history_for_llm = st.session_state.messages[-10:]
    # Use the current full context from processed files
    file_context_for_llm = st.session_state.uploaded_file_data

    # 3. Get LLM Response and add to messages
    with st.chat_message("assistant"):
         message_placeholder = st.empty()
         message_placeholder.markdown("🧠 Thinking...")
         try:
             current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
             response_text, generated_file_info = llm_api.get_llm_response(
                 model_display_name=st.session_state.selected_model,
                 messages=history_for_llm,
                 api_keys=st.session_state.api_keys,
                 uploaded_file_context=file_context_for_llm, # Pass current context
                 model_capabilities=current_model_capabilities
             )
             message_placeholder.markdown(response_text)
             assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
             # ... (handle generated file downloads) ...
             st.session_state.messages.append(assistant_message)

         except ValueError as ve:
              st.error(f"Configuration Error: {ve}")
              error_message = f"Sorry, could not get response: {ve}"
              st.session_state.messages.append({"role": "assistant", "content": error_message})
              message_placeholder.error(error_message)
         except Exception as e:
             st.error(f"An error occurred: {e}")
             error_message = f"Sorry, I encountered an error trying to get a response. Error: {e}"
             st.session_state.messages.append({"role": "assistant", "content": error_message})
             message_placeholder.error(error_message)

    # 4. Rerun (handled by st.chat_input submission) to display messages
    st.rerun()


# --- Display Stop App Warning (if applicable) ---
# Placed at the very end, it won't interfere with layout
if st.session_state.stop_app:
     st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
