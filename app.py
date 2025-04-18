# app.py (Modified - Chat-Like Uploader Experience)

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

# --- Additional Custom CSS for File Upload Experience ---
st.markdown("""
<style>
/* File staging area styling */
.file-staging-area {
    padding: 10px;
    margin-bottom: 10px;
    border-radius: 8px;
}

/* Staged file cards */
.staged-file-card {
    display: inline-block;
    margin-right: 8px;
    margin-bottom: 8px;
    padding: 5px 10px;
    background-color: #f0f2f6;
    border-radius: 8px;
    border: 1px solid #dfe1e6;
    font-size: 14px;
}

/* Upload button styling */
.chat-controls {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
}

/* Fix file uploader to be minimal */
.stFileUploader > div > div > div:first-child {
    display: none;
}
</style>
""", unsafe_allow_html=True)

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
# Add staged_files state to hold files that are selected but not yet processed
if "staged_files" not in st.session_state:
    st.session_state.staged_files = []

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

def process_staged_files():
    """Process all staged files and add them to the uploaded_file_data."""
    processed_files = []
    
    if not st.session_state.staged_files:
        return processed_files
    
    for file in st.session_state.staged_files:
        # Check if file hasn't been processed yet
        if file.name not in st.session_state.uploaded_file_data:
            content, metadata = file_parser.process_uploaded_file(file)
            if content is not None:
                st.session_state.uploaded_file_data[file.name] = {
                    "content": content, "metadata": metadata
                }
                processed_files.append(file.name)
    
    # Clear staged files after processing
    st.session_state.staged_files = []
    
    return processed_files

def remove_staged_file(file_index):
    """Remove a file from the staged files list."""
    if 0 <= file_index < len(st.session_state.staged_files):
        st.session_state.staged_files.pop(file_index)
        st.rerun()

# --- Sidebar ---
with st.sidebar:
    st.title("✨ AI Chat Studio")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.session_state.uploaded_file_data = {} # Clear processed files context
        st.session_state.staged_files = [] # Clear staged files
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
        st.caption("Upload files to add context to the chat.")


# --- Main Chat Area ---
st.header(f"Chat with {st.session_state.selected_model}")

# Create the main layout structure
chat_container = st.container()
file_staging_container = st.container()  
input_container = st.container()

# --- Display Chat Messages ---
with chat_container:
    if not st.session_state.messages:
        st.markdown("Start a conversation by sending a message below.")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display attached files info if available
            if "attached_files" in message and message["attached_files"]:
                st.caption(f"📎 Files: {', '.join(message['attached_files'])}")
            # Display generated files if any
            if "generated_files" in message and message["generated_files"]:
                for file_info in message["generated_files"]:
                    pass # Simplified

# --- File Staging Area (Between Chat and Input) ---
with file_staging_container:
    # Only show staging area if there are files staged
    if st.session_state.staged_files:
        st.markdown('<div class="file-staging-area">', unsafe_allow_html=True)
        
        # Use columns to display files with remove buttons
        cols = st.columns([1, 20])
        with cols[0]:
            st.markdown("📎")
        with cols[1]:
            # Use horizontal layout for file cards
            file_html = ""
            for i, file in enumerate(st.session_state.staged_files):
                # Create the file card with filename and remove button
                col1, col2 = st.columns([10, 1])
                with col1:
                    st.markdown(f"""<div class="staged-file-card">
                                    {file.name}
                                </div>""", unsafe_allow_html=True)
                with col2:
                    if st.button("✖", key=f"remove_file_{i}", help=f"Remove {file.name}"):
                        remove_staged_file(i)
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- Chat Input Area with Upload Button ---
with input_container:
    # Create a row with columns for upload button and chat input
    cols = st.columns([1, 20])
    
    # Column 1: Upload Button
    with cols[0]:
        # Use a container to create vertical space alignment
        button_container = st.container()
        with button_container:            
            # Create a hidden file uploader triggered by the button
            uploaded_files = st.file_uploader(
                "Hidden uploader",
                type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"],
                accept_multiple_files=True,
                label_visibility="collapsed",
                key="chat_file_uploader"
            )
            
            if uploaded_files:
                # Add uploaded files to staged_files
                for file in uploaded_files:
                    # Add only if not already in staged files (by name)
                    if file.name not in [f.name for f in st.session_state.staged_files]:
                        st.session_state.staged_files.append(file)
                st.rerun()  # Refresh to show the staged files
            
            # Upload button appearance
            st.markdown("""
                <style>
                .upload-button {
                    background-color: #f0f2f6;
                    border-radius: 50%;
                    width: 36px;
                    height: 36px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    margin-bottom: 0;
                    padding: 0;
                    border: 1px solid #dfe1e6;
                }
                .upload-button:hover {
                    background-color: #e6e9ef;
                }
                </style>
                <div class="upload-button" title="Attach files">
                    <span style="font-size: 20px;">+</span>
                </div>
            """, unsafe_allow_html=True)
    
    # Column 2: Chat Input
    with cols[1]:
        # Chat input configuration
        chat_input_disabled = st.session_state.stop_app
        chat_placeholder = f"Ask {st.session_state.selected_model} anything..."
        if chat_input_disabled:
            key_name = required_key_name_for_selected or "API Key"
            chat_placeholder = f"Cannot chat: {key_name} missing in secrets.toml"

        # The actual chat input
        prompt = st.chat_input(
            chat_placeholder,
            disabled=chat_input_disabled,
            key="chat_input_main"
        )

        # --- Handle Send Action ---
        if prompt:
            # Process any staged files first
            processed_files = process_staged_files()
            
            # 1. Add User Message (now with attached files info)
            user_message = {"role": "user", "content": prompt}
            if processed_files:
                user_message["attached_files"] = processed_files
            st.session_state.messages.append(user_message)

            # 2. Prepare context for LLM call
            history_for_llm = st.session_state.messages[-10:]
            file_context_for_llm = st.session_state.uploaded_file_data

            # 3. Get LLM Response and add to messages
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🧠 Thinking...")
                try:
                    # LLM API call logic
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

            # 4. Rerun to display new messages
            st.rerun()

# --- Display Stop App Warning (if applicable) ---
if st.session_state.stop_app:
    st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
