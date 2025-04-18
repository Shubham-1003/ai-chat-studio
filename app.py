# app.py (Corrected - Removed Bad CSS, Uploader Above Chat Input)

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

# Load base CSS ONLY - REMOVE previous custom positioning CSS
load_css("css/style.css")

# Minimal CSS for the remove button (optional, adjust as needed)
st.markdown("""
<style>
/* Style the small remove button for staged files */
/* Find a more specific selector if needed */
button[kind="secondary"] {
    font-size: 0.8em;
    padding: 0.1rem 0.3rem !important;
    min-height: 1em !important;
    line-height: 1em !important;
}
/* Add some space below the chat messages before the upload area */
.stChatMessage {
    margin-bottom: 1rem;
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
if "staged_files" not in st.session_state: # Holds UploadedFile objects before sending
    st.session_state.staged_files = {} # Use a dict {name: UploadedFile}

# --- Helper Functions ---
def display_processed_file_card(filename, metadata):
    # (Function remains the same as before)
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
        st.session_state.uploaded_file_data = {}
        st.session_state.staged_files = {}
        st.rerun()
    st.markdown("---")
    # --- Model Selection (remains the same) ---
    st.subheader("🤖 Model Selection")
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models:
        st.error("No models configured in `utils/llm_api.py`.")
        st.stop()
    if st.session_state.selected_model not in available_models:
        st.session_state.selected_model = available_models[0]
    selected_model_display_name = st.selectbox(
        "Choose an LLM:", options=available_models,
        index=available_models.index(st.session_state.selected_model),
        key="model_selector"
    )
    # Internal API Key Check
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    st.session_state.api_keys = {}
    st.session_state.stop_app = False
    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets:
            st.session_state.api_keys[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
        else:
            st.session_state.stop_app = True
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name
        st.rerun()
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")
    # --- Display Processed Files (remains the same) ---
    if st.session_state.uploaded_file_data:
        st.subheader("Chat Context Files")
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                data = st.session_state.uploaded_file_data[filename]
                display_processed_file_card(filename, data["metadata"])
            else: pass
        if st.button("Clear All Context Files"):
            st.session_state.uploaded_file_data = {}
            st.toast("Cleared all files from chat context.")
            st.rerun()
        st.markdown("---")

# --- Main Chat Area ---
st.header(f"Chat with {st.session_state.selected_model}")

# --- Display Chat Messages ---
# This container will hold the conversation history
message_container = st.container()
with message_container:
    # Add some vertical space if needed, e.g., message_container.empty() or adjust CSS
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display generated files if any
            if "generated_files" in message and message["generated_files"]:
                 for file_info in message["generated_files"]:
                    # (Code for download link)
                    pass # Simplified for brevity

# --- File Upload and Staging Area (Placed *Before* Chat Input) ---
# This container holds the uploader and the display of staged files
upload_staging_area = st.container()
with upload_staging_area:
    # Display Staged Files First
    if st.session_state.staged_files:
        st.markdown("**Files attached to next message:**")
        # Arrange staged files - using columns for better layout
        num_staged = len(st.session_state.staged_files)
        max_cols = 4 # Adjust how many cards per row
        cols = st.columns(max_cols)
        col_index = 0
        staged_file_names = list(st.session_state.staged_files.keys())

        for filename in staged_file_names:
            if filename in st.session_state.staged_files: # Check if still staged
                uploaded_file = st.session_state.staged_files[filename]
                with cols[col_index % max_cols]:
                    # Use a container with border for each file card
                    with st.container(border=True):
                        file_type = uploaded_file.type or "unknown"
                        icon = "📄"
                        if "image" in file_type: icon = "🖼️"
                        elif "pdf" in file_type: icon = "📕"

                        # Display file info and remove button
                        st.markdown(f"{icon} **{uploaded_file.name}**")
                        st.caption(f"({(uploaded_file.size / 1024):.1f} KB)")
                        # Place remove button next to caption or below name
                        if st.button("✖️ Remove", key=f"remove_{filename}", type="secondary"):
                            del st.session_state.staged_files[filename]
                            st.rerun()
                col_index += 1
        st.markdown("---", unsafe_allow_html=True) # Use markdown for HR


    # File Uploader - appears below the staged files (if any)
    uploaded_files = st.file_uploader(
        "📎 Attach Files",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"],
        accept_multiple_files=True,
        label_visibility="visible", # Keep the label visible
        key="main_uploader" # Reset key on rerun implicitly
    )
    # Add newly selected files to staging
    if uploaded_files:
        newly_staged_count = 0
        for file in uploaded_files:
            if file.name not in st.session_state.staged_files:
                st.session_state.staged_files[file.name] = file
                newly_staged_count += 1
        if newly_staged_count > 0:
            st.toast(f"Attached {newly_staged_count} file(s). Ready for your next message.")
            # Rerun needed to show the files in the staging area above
            st.rerun()


# --- Chat Input (At the very bottom of the script execution) ---
# `st.chat_input` will naturally stick to the bottom of the viewport
chat_input_disabled = st.session_state.stop_app
chat_placeholder = f"Ask {st.session_state.selected_model} anything..."
if chat_input_disabled:
    key_name = required_key_name_for_selected or "API Key" # Fallback text
    chat_placeholder = f"Cannot chat: {key_name} missing in secrets.toml"

prompt = st.chat_input(
    chat_placeholder,
    disabled=chat_input_disabled,
    key="chat_input_main" # Unique key
)

# --- Handle Send Action (When prompt is submitted) ---
if prompt:
    files_processed_this_turn = {}
    prompt_to_send = prompt

    # 1. Process any staged files *before* sending the prompt
    # This runs ONLY when the user actually sends a message
    if st.session_state.staged_files:
        num_staged = len(st.session_state.staged_files)
        # Use status instead of spinner for potentially longer processing
        with st.status(f"Processing {num_staged} attached file(s)...", expanded=False) as status:
            staged_files_to_process = list(st.session_state.staged_files.values())
            for staged_file in staged_files_to_process:
                st.write(f"Processing: {staged_file.name}")
                if staged_file.name not in st.session_state.uploaded_file_data:
                    content, metadata = file_parser.process_uploaded_file(staged_file)
                    if content is not None:
                        st.session_state.uploaded_file_data[staged_file.name] = {
                            "content": content, "metadata": metadata
                        }
                        files_processed_this_turn[staged_file.name] = metadata
            # Clear staging area ONLY after successful processing loop
            st.session_state.staged_files = {}
            status.update(label=f"Processed {len(files_processed_this_turn)} file(s)!", state="complete", expanded=False)
        st.toast(f"Added {len(files_processed_this_turn)} file(s) to context.")

    # 2. Add User Message (will appear after rerun caused by chat_input)
    user_message_content = prompt_to_send
    # We don't need to manually add the "(Processed attachments...)" text anymore
    # as the files are now part of the persistent context displayed in the sidebar.
    st.session_state.messages.append({"role": "user", "content": user_message_content})

    # 3. Prepare context for LLM call
    history_for_llm = st.session_state.messages[-10:]
    file_context_for_llm = st.session_state.uploaded_file_data # Use full context

    # 4. Get LLM Response and add to messages
    # (LLM call logic remains the same - occurs after message is added)
    with st.chat_message("assistant"): # Display thinking indicator
         message_placeholder = st.empty()
         message_placeholder.markdown("🧠 Thinking...")
         try:
             current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
             response_text, generated_file_info = llm_api.get_llm_response(
                 model_display_name=st.session_state.selected_model,
                 messages=history_for_llm,
                 api_keys=st.session_state.api_keys,
                 uploaded_file_context=file_context_for_llm,
                 model_capabilities=current_model_capabilities
             )
             message_placeholder.markdown(response_text) # Update placeholder with actual response
             assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
             # ... (handle generated file downloads) ...
             st.session_state.messages.append(assistant_message) # Add assistant message AFTER getting it

         except ValueError as ve:
              st.error(f"Configuration Error: {ve}")
              error_message = f"Sorry, could not get response: {ve}"
              # Add error as assistant message
              st.session_state.messages.append({"role": "assistant", "content": error_message})
              message_placeholder.error(error_message) # Show error in placeholder too
         except Exception as e:
             st.error(f"An error occurred: {e}")
             error_message = f"Sorry, I encountered an error trying to get a response. Error: {e}"
             st.session_state.messages.append({"role": "assistant", "content": error_message})
             message_placeholder.error(error_message)

    # 5. Rerun to display the new user/assistant messages and clear staging area visually
    # (st.chat_input handles the rerun needed to display the prompt message,
    # and the clearing of staged_files happens above. A final rerun might be needed
    # if status widget behavior requires it, but often not).
    st.rerun()


# --- Display Stop App Warning (if applicable) ---
if st.session_state.stop_app:
     st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
