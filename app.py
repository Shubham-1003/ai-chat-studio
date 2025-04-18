# app.py (Stable Version - Sidebar Upload, Standard Components)

import streamlit as st
from PIL import Image
import io
import os
# Assuming these util files exist and work as expected
from utils import llm_api, file_parser

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Chat Studio",
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

# Load base CSS ONLY - Ensure NO positioning CSS from previous attempts remains here
load_css("css/style.css")

# REMOVE ALL OTHER st.markdown(<style>...) blocks from this file

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

    # Use an expander for each file in the sidebar context list
    with st.expander(f"📄 {filename} ({file_type} - {file_size / 1024:.1f} KB)", expanded=False):
        st.markdown(f"**Preview:**")
        if isinstance(content_preview, str):
            # Use st.code for potentially long text to make it scrollable within expander
            st.code(content_preview, language=None)
        else:
            st.text(content_preview) # Keep original for non-string (like PIL Images)

# --- Sidebar ---
with st.sidebar:
    st.title("✨ AI Chat Studio")

    # New Chat Button
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.session_state.uploaded_file_data = {} # Clear context on new chat
        st.rerun()
    st.markdown("---")

    # Model Selection
    st.subheader("🤖 Model Selection")
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models: st.error("No models configured."); st.stop()
    if st.session_state.selected_model not in available_models: st.session_state.selected_model = available_models[0]
    selected_model_display_name = st.selectbox(
        "Choose an LLM:", options=available_models,
        index=available_models.index(st.session_state.selected_model), key="model_selector"
    )
    # Internal API Key Check (using model-specific keys)
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    st.session_state.api_keys = {}; st.session_state.stop_app = False
    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets:
            st.session_state.api_keys[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
        else:
            st.session_state.stop_app = True # Set flag if key missing
            st.warning(f"API Key '{required_key_name_for_selected}' not found in secrets.", icon="⚠️") # Add warning
    # Rerun if model changes
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name; st.rerun()
    # Display Capabilities
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")

    # --- File Upload Section (Moved Back to Sidebar) ---
    st.subheader("📁 Add Files to Context")
    uploaded_files_sidebar = st.file_uploader(
        "Upload PDF, DOCX, TXT, Images, etc.",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"], # Customize allowed types
        accept_multiple_files=True,
        label_visibility="collapsed", # Use subheader as label
        key="sidebar_uploader"
    )

    # Immediate Processing Logic (Now in Sidebar)
    if uploaded_files_sidebar:
        files_processed_count = 0
        # Use spinner for feedback in the sidebar
        with st.spinner(f"Processing {len(uploaded_files_sidebar)} file(s)..."):
            for file in uploaded_files_sidebar:
                # Process only if the file isn't already in the context data
                if file.name not in st.session_state.uploaded_file_data:
                    content, metadata = file_parser.process_uploaded_file(file)
                    if content is not None:
                        st.session_state.uploaded_file_data[file.name] = {
                            "content": content, "metadata": metadata
                        }
                        files_processed_count += 1
                    # else: Optional: Log processing failure if needed

        if files_processed_count > 0:
            st.toast(f"Added {files_processed_count} new file(s) to context.")
            # Rerun is necessary to update the context display below and clear the uploader state
            st.rerun()
        elif uploaded_files_sidebar: # Files were selected, but all existed already
             st.toast("Selected file(s) are already in the chat context.")
             # Still rerun to clear the uploader widget's file list visually
             st.rerun()
    st.markdown("---") # Separator after upload section

    # --- Display Processed Context Files (Remains in Sidebar) ---
    if st.session_state.uploaded_file_data:
        st.subheader("Chat Context Files")
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                data = st.session_state.uploaded_file_data[filename]
                # Use the helper function to display the expander card
                display_processed_file_card(filename, data["metadata"])

        # Add Clear button below the list of files
        if st.button("Clear All Context Files"):
            st.session_state.uploaded_file_data = {}; st.toast("Cleared all files from chat context."); st.rerun()
        st.markdown("---")
    else:
        # Provide feedback if no files have been uploaded yet
        st.caption("Upload files above to add context to the chat.")


# --- Main Chat Area ---
st.header(f"Chat with {st.session_state.selected_model}")

# --- Display Chat Messages ---
# This container holds the conversation history. It will grow naturally.
message_container = st.container()
with message_container:
    if not st.session_state.messages:
         st.caption("Conversation history will appear here...")

    for message in st.session_state.messages:
        # Use standard st.chat_message for reliable rendering
        with st.chat_message(message["role"]):
            st.markdown(message["content"]) # Render message content as markdown
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

# --- Chat Input (Standard - Will stick to bottom) ---
# No file upload elements needed here anymore
chat_input_disabled = st.session_state.stop_app
chat_placeholder = f"Ask {st.session_state.selected_model}..."
if chat_input_disabled:
    key_name = required_key_name_for_selected or "API Key"
    chat_placeholder = f"Cannot chat: {key_name} missing in secrets.toml"

prompt = st.chat_input(
    chat_placeholder,
    disabled=chat_input_disabled,
    key="chat_input_main" # Unique key for the chat input widget
)

# --- Handle Send Action ---
if prompt:
    # 1. Add User Message to state
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Prepare context for LLM call (using existing processed files from sidebar)
    history_for_llm = st.session_state.messages[-10:]
    file_context_for_llm = st.session_state.uploaded_file_data # Use current context

    # 3. Get LLM Response and add to messages state
    # Display thinking indicator within standard chat message structure
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
             message_placeholder.markdown(response_text) # Display final response
             assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
             # Handle generated files
             if generated_file_info and isinstance(generated_file_info, dict):
                 assistant_message["generated_files"].append(generated_file_info)
                 # Display download link immediately below response
                 file_content = generated_file_info.get("content", "")
                 if isinstance(file_content, (str, bytes)):
                     file_parser.generate_download_link( file_content, generated_file_info.get("filename", "download"), f"Download {generated_file_info.get('filename', 'file')}" )
                 else: st.warning(f"Cannot generate download for: {generated_file_info.get('filename')}")

             st.session_state.messages.append(assistant_message) # Append full message to state

         except ValueError as ve: # Handle specific config errors
              error_message = f"Configuration Error: {ve}"
              message_placeholder.error(error_message) # Show error in placeholder
              st.session_state.messages.append({"role": "assistant", "content": error_message}) # Log error
         except Exception as e: # Handle generic errors
             error_message = f"An error occurred: {e}"
             message_placeholder.error(error_message) # Show error in placeholder
             st.session_state.messages.append({"role": "assistant", "content": error_message}) # Log error

    # 4. Rerun (handled automatically by st.chat_input) to display messages
    st.rerun()


# --- Display Stop App Warning (Optional - at the end) ---
if st.session_state.stop_app:
     # This warning appears at the bottom, not interfering with layout
     st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
