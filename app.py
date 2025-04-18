# app.py (Stable Version - Standard Uploader & Chat Input)

import streamlit as st
from PIL import Image
import io
import os
# Assuming these util files exist and work as expected
from utils import llm_api, file_parser

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Chat Studio", # Changed title back
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
# REMOVED staging state: if "staged_files" not in st.session_state: ...

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
    # Use the model-specific key lookup logic
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
        else: st.session_state.stop_app = True # Set flag if key missing
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name; st.rerun()
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")
    # --- Display Processed Files in Sidebar ---
    if st.session_state.uploaded_file_data:
        st.subheader("Chat Context Files")
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                data = st.session_state.uploaded_file_data[filename]
                display_processed_file_card(filename, data["metadata"]) # Use helper
        if st.button("Clear All Context Files"):
            st.session_state.uploaded_file_data = {}; st.toast("Cleared all files from chat context."); st.rerun()
        st.markdown("---")
    else:
        # Optional: Add message if no files uploaded yet
        st.caption("Upload files in the main area to add context.")


# --- Main Chat Area ---
st.header(f"Chat with {st.session_state.selected_model}")

# --- Display Chat Messages ---
message_container = st.container()
# Give the container some minimum height if needed when empty, e.g., using CSS or st.empty()
with message_container:
    # Add a placeholder if no messages exist yet
    if not st.session_state.messages:
         st.caption("Conversation history will appear here...")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display generated files if any
            if "generated_files" in message and message["generated_files"]:
                 for file_info in message["generated_files"]:
                    file_content = file_info.get("content", "")
                    if isinstance(file_content, (str, bytes)):
                        file_parser.generate_download_link(
                            content=file_content,
                            filename=file_info.get("filename", "download"),
                            link_text=f"Download {file_info.get('filename', 'file')}"
                        )
                    else:
                        st.warning(f"Cannot generate download for: {file_info.get('filename')}")


# --- File Upload Area (Normal Flow - Above Chat Input) ---
upload_area = st.container()
with upload_area:
    # Standard File Uploader
    uploaded_files = st.file_uploader(
        "Attach Files to Context (processed immediately)",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"], # Add/remove types as needed
        accept_multiple_files=True,
        label_visibility="visible",
        key="immediate_uploader"
    )

    # Immediate Processing Logic
    if uploaded_files:
        files_processed_count = 0
        with st.spinner(f"Processing {len(uploaded_files)} file(s)...") as spinner: # Use spinner for immediate feedback
            for file in uploaded_files:
                if file.name not in st.session_state.uploaded_file_data:
                    # st.write(f"Processing: {file.name}") # Spinner shows general progress
                    content, metadata = file_parser.process_uploaded_file(file)
                    if content is not None:
                        st.session_state.uploaded_file_data[file.name] = {
                            "content": content, "metadata": metadata
                        }
                        files_processed_count += 1
                    # else: Optional: Log failure if needed

        if files_processed_count > 0:
            st.toast(f"Added {files_processed_count} file(s) to the chat context (see sidebar).")
            # Rerun required to update sidebar and clear the uploader widget
            st.rerun()
        elif uploaded_files: # Files were selected, but all existed already
             st.toast("Selected file(s) are already in the chat context.")
             # Rerun to clear the uploader widget state
             st.rerun()


# --- Chat Input (Standard - Sticks to Bottom) ---
chat_input_disabled = st.session_state.stop_app
chat_placeholder = f"Ask {st.session_state.selected_model}..."
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
    file_context_for_llm = st.session_state.uploaded_file_data # Use current context

    # 3. Get LLM Response and add to messages
    with st.chat_message("assistant"):
         message_placeholder = st.empty()
         message_placeholder.markdown("🧠 Thinking...")
         try:
             current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
             response_text, generated_file_info = llm_api.get_llm_response(
                 model_display_name=st.session_state.selected_model, messages=history_for_llm,
                 api_keys=st.session_state.api_keys, uploaded_file_context=file_context_for_llm,
                 model_capabilities=current_model_capabilities
             )
             message_placeholder.markdown(response_text) # Display response
             assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
             # Add generated file handling back if needed
             if generated_file_info and isinstance(generated_file_info, dict):
                 assistant_message["generated_files"].append(generated_file_info)
                 # Display download link immediately
                 file_content = generated_file_info.get("content", "")
                 if isinstance(file_content, (str, bytes)):
                     file_parser.generate_download_link(
                        file_content,
                        generated_file_info.get("filename", "download"),
                        f"Download {generated_file_info.get('filename', 'file')}"
                     )
                 else:
                     st.warning(f"Cannot generate download for non-text/bytes generated content: {generated_file_info.get('filename')}")
             st.session_state.messages.append(assistant_message) # Add response to state

         except ValueError as ve: # Handle specific config errors
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
# Placed at the very end, it won't interfere with layout
if st.session_state.stop_app:
     st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
