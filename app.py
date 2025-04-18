# app.py (Redesigned - ChatGPT-Style Interface)

import streamlit as st
from PIL import Image
import io
import os
from utils import llm_api, file_parser

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Chat Studio",
    page_icon="✨",
    layout="wide"
)

# --- Custom CSS for ChatGPT-like Interface ---
st.markdown("""
<style>
/* Global Styles */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 0;
    max-width: 52rem;
}

/* Header styling */
header {
    visibility: hidden;
}

/* Sidebar styling */
.css-1d391kg {
    background-color: #202123;
}

/* Chat styling */
.stChatMessage {
    background-color: transparent !important;
    padding: 1rem 0 !important;
}
.stChatMessage [data-testid="stChatMessageContent"] {
    background-color: #f7f7f8;
    border-radius: 12px;
    padding: 1rem;
}
.stChatMessage.st-emotion-cache-5trom0 [data-testid="stChatMessageContent"] {
    background-color: #f7f7f8;
}
.stChatMessage.st-emotion-cache-rklll2 [data-testid="stChatMessageContent"] {
    background-color: #ececf1;
}

/* File Upload Area */
.chat-input-area {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 0.8rem 1rem;
    background-color: white;
    z-index: 999;
    border-top: 1px solid #e5e5e5;
    max-width: 52rem;
    margin: 0 auto;
}

.file-dropzone {
    border: 2px dashed #ddd;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 10px;
    text-align: center;
    background-color: #f9f9f9;
    cursor: pointer;
}

.file-badge {
    display: inline-flex;
    align-items: center;
    background-color: #f0f0f0;
    padding: 5px 10px;
    border-radius: 15px;
    margin-right: 8px;
    margin-bottom: 8px;
    font-size: 0.8rem;
}

.file-badge-container {
    margin-bottom: 10px;
}

.file-badge .remove-btn {
    margin-left: 5px;
    cursor: pointer;
    color: #888;
}

.file-badge .remove-btn:hover {
    color: #ff4d4f;
}

.upload-icon {
    background-color: #f0f0f0;
    border-radius: 50%;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    cursor: pointer;
    border: none;
}

.upload-icon:hover {
    background-color: #e6e6e6;
}

.chat-input-container {
    display: flex;
    align-items: flex-end;
}

.chat-input-box {
    flex-grow: 1;
    margin-right: 8px;
}

/* Hide streamlit branding */
#MainMenu {visibility: hidden;}
.stDeployButton {display:none;}
footer {visibility: hidden;}

/* Make chat input stick to bottom properly */
.main {
    margin-bottom: 100px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .chat-input-area {
        padding: 0.5rem;
    }
}

/* Custom file uploader */
div[data-testid="stFileUploader"] {
    width: 36px;
    height: 36px;
    overflow: hidden;
    opacity: 0;
    position: absolute;
}

.stFileUploader > div > div > div:first-child {
    display: none;
}

#chat_file_uploader {
    opacity: 0;
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
if "uploaded_file_data" not in st.session_state:
    st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state:
    st.session_state.stop_app = False
if "staged_files" not in st.session_state:
    st.session_state.staged_files = []
if "show_dropzone" not in st.session_state:
    st.session_state.show_dropzone = False

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
    
    with st.status("Processing files...", expanded=False) as status:
        for file in st.session_state.staged_files:
            # Check if file hasn't been processed yet
            if file.name not in st.session_state.uploaded_file_data:
                content, metadata = file_parser.process_uploaded_file(file)
                if content is not None:
                    st.session_state.uploaded_file_data[file.name] = {
                        "content": content, "metadata": metadata
                    }
                    processed_files.append(file.name)
        status.update(label=f"Processed {len(processed_files)} files", state="complete")
    
    # Clear staged files after processing
    st.session_state.staged_files = []
    st.session_state.show_dropzone = False
    
    return processed_files

def remove_staged_file(file_index):
    """Remove a file from the staged files list."""
    if 0 <= file_index < len(st.session_state.staged_files):
        st.session_state.staged_files.pop(file_index)
        if not st.session_state.staged_files:
            st.session_state.show_dropzone = False
        st.rerun()

def toggle_dropzone():
    """Toggle the file dropzone visibility."""
    st.session_state.show_dropzone = not st.session_state.show_dropzone
    st.rerun()

# --- Sidebar ---
with st.sidebar:
    st.title("✨ AI Chat Studio")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.session_state.uploaded_file_data = {}
        st.session_state.staged_files = []
        st.session_state.show_dropzone = False
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
    if st.session_state.uploaded_file_data:
        st.subheader("Chat Context Files")
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                data = st.session_state.uploaded_file_data[filename]
                display_processed_file_card(filename, data["metadata"])
        if st.button("Clear All Context Files"):
            st.session_state.uploaded_file_data = {}
            st.toast("Cleared all files from chat context.")
            st.rerun()
        st.markdown("---")
    else:
        st.caption("Upload files to add context to the chat.")

# --- Main Chat Area ---
# Provide some extra space at the bottom for the fixed chat input
st.markdown(f"<div style='height: 80px;'></div>", unsafe_allow_html=True)

# --- Display Chat Messages ---
if not st.session_state.messages:
    st.markdown("<div style='text-align: center; color: #888; margin-top: 100px;'>Send a message to start chatting with AI</div>", unsafe_allow_html=True)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Display attached files info if available
        if "attached_files" in message and message["attached_files"]:
            files_html = ""
            for file in message["attached_files"]:
                files_html += f"<span class='file-badge'>📎 {file}</span>"
            st.markdown(f"<div class='file-badge-container'>{files_html}</div>", unsafe_allow_html=True)

# --- Create the fixed chat input area at the bottom ---
chat_input_container = st.container()

with chat_input_container:
    st.markdown("<div class='chat-input-area'>", unsafe_allow_html=True)
    
    # --- File Dropzone (only shown when toggled) ---
    if st.session_state.show_dropzone:
        # Create drag-and-drop area
        st.markdown("<div class='file-dropzone'>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Drag and drop files here",
            type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"],
            accept_multiple_files=True,
            key="chat_file_uploader"
        )
        
        if uploaded_files:
            # Add uploaded files to staged_files if not already there
            for file in uploaded_files:
                if file.name not in [f.name for f in st.session_state.staged_files]:
                    st.session_state.staged_files.append(file)
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)
    
    # --- Display Staged Files ---
    if st.session_state.staged_files:
        files_html = ""
        for i, file in enumerate(st.session_state.staged_files):
            files_html += f"""
            <span class='file-badge'>
                {file.name}
                <span class='remove-btn' onclick="document.dispatchEvent(new CustomEvent('remove-file', {{detail: {{index: {i}}}}}))">×</span>
            </span>
            """
        st.markdown(f"<div class='file-badge-container'>{files_html}</div>", unsafe_allow_html=True)
        
        # Handle file removal with a hidden button for each file
        for i in range(len(st.session_state.staged_files)):
            if st.button(f"Remove {i}", key=f"remove_btn_{i}", visible=False):
                remove_staged_file(i)
    
    # --- Chat Input with Attachment Button ---
    cols = st.columns([1, 20])
    
    with cols[0]:
        # Upload icon button
        if st.button("📎", help="Attach files", key="attachment_button", use_container_width=True):
            toggle_dropzone()
    
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
    
    st.markdown("</div>", unsafe_allow_html=True)

# Add custom JS for handling file removal events
st.markdown("""
<script>
document.addEventListener('remove-file', function(e) {
    const index = e.detail.index;
    const buttons = document.querySelectorAll('button');
    const removeButton = Array.from(buttons).find(button => button.innerText === `Remove ${index}`);
    if (removeButton) {
        removeButton.click();
    }
});
</script>
""", unsafe_allow_html=True)

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

    # 3. Get LLM Response
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
