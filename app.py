# app.py (Reverted to st.chat_input, Added Staging Area)

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

# Minimal CSS needed now
st.markdown("""
<style>
/* Style the remove button for staged files */
.stButton>button[kind="secondary"] {
    /* Make the 'x' button smaller */
    padding: 0.1rem 0.3rem !important;
    min-height: 1em !important;
    line-height: 1em !important;
}
/* Add some space below the chat messages */
.stChatMessage {
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

load_css("css/style.css")


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
if "staged_files" not in st.session_state: # Holds UploadedFile objects before sending <<< NEW
    st.session_state.staged_files = {} # Use a dict {name: UploadedFile} to handle removals easily

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
        st.session_state.staged_files = {} # Clear staged files
        st.rerun()
    st.markdown("---")
    # --- Model Selection ---
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
    # --- Display Processed Files ---
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
# Use a container to group messages if needed, but not strictly required now
message_container = st.container()
with message_container:
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
                        st.warning(f"Cannot generate download for non-text/bytes content: {file_info.get('filename')}")

# --- File Upload and Staging Area (Above Chat Input) ---
# Container to group uploader and staged files display
upload_area = st.container()
with upload_area:
    # Display Staged Files First
    if st.session_state.staged_files:
        st.markdown("**Files staged for next message:**")
        cols = st.columns(4) # Adjust number of columns based on expected file count
        col_index = 0
        staged_file_names = list(st.session_state.staged_files.keys()) # Get names for iteration
        for filename in staged_file_names:
            if filename in st.session_state.staged_files: # Check if still exists
                uploaded_file = st.session_state.staged_files[filename]
                with cols[col_index % len(cols)]:
                    with st.container(border=True): # Add border for visual grouping
                        file_type = uploaded_file.type or "unknown"
                        icon = "📄"
                        if "image" in file_type: icon = "🖼️"
                        elif "pdf" in file_type: icon = "📕"
                        # Use markdown for tighter spacing
                        st.markdown(f"{icon} {uploaded_file.name}")
                        st.caption(f"({(uploaded_file.size / 1024):.1f} KB)")
                        if st.button("Remove", key=f"remove_{filename}", type="secondary"):
                            del st.session_state.staged_files[filename]
                            st.rerun()
                col_index += 1
        st.markdown("---") # Separator below staged files


    # File Uploader Button
    uploaded_files = st.file_uploader(
        "📎 Attach Files", # Use an icon in the label
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"],
        accept_multiple_files=True,
        label_visibility="visible", # Show the label as the button text
        key="main_uploader"
    )
    if uploaded_files:
        newly_staged_count = 0
        for file in uploaded_files:
            if file.name not in st.session_state.staged_files:
                st.session_state.staged_files[file.name] = file
                newly_staged_count += 1
        if newly_staged_count > 0:
            st.toast(f"Staged {newly_staged_count} file(s). They will be processed with your next message.")
            # Rerun to update the staging display and clear the uploader's internal state
            st.rerun()

# --- Chat Input ---
chat_input_disabled = st.session_state.stop_app
chat_placeholder = f"Ask {st.session_state.selected_model} anything..."
if chat_input_disabled:
    chat_placeholder = f"Cannot chat: API key for {st.session_state.selected_model} missing in secrets.toml"

prompt = st.chat_input(
    chat_placeholder,
    disabled=chat_input_disabled,
    key="chat_input"
    # on_submit=handle_send # We'll handle submit logic below
)

# --- Handle Send Action (Triggered by st.chat_input) ---
if prompt: # This block executes when user sends message via chat_input
    files_processed_this_turn = {}
    prompt_to_send = prompt # Store the text prompt

    # 1. Process Staged Files *before* sending the prompt
    if st.session_state.staged_files:
        num_staged = len(st.session_state.staged_files)
        with st.spinner(f"Processing {num_staged} attached file(s)..."):
            staged_files_to_process = list(st.session_state.staged_files.values()) # Get file objects
            for staged_file in staged_files_to_process:
                # Check if not already in the main context (might be redundant but safe)
                if staged_file.name not in st.session_state.uploaded_file_data:
                    content, metadata = file_parser.process_uploaded_file(staged_file)
                    if content is not None:
                        st.session_state.uploaded_file_data[staged_file.name] = {
                            "content": content,
                            "metadata": metadata
                        }
                        files_processed_this_turn[staged_file.name] = metadata
        # Clear staging area *after* processing
        st.session_state.staged_files = {}
        st.toast(f"Processed {len(files_processed_this_turn)} file(s) into context.")


    # 2. Add User Message to History (potentially mentioning processed files)
    user_message_content = prompt_to_send
    if files_processed_this_turn:
         user_message_content += "\n\n*(Processed attachments: " + ", ".join(files_processed_this_turn.keys()) + ")*"

    st.session_state.messages.append({"role": "user", "content": user_message_content})

    # Display user message immediately (st.chat_input does this automatically on rerun,
    # but doing it explicitly ensures it appears before the thinking spinner)
    with message_container: # Ensure it appears in the right container
        with st.chat_message("user"):
            st.markdown(user_message_content)

    # 3. Prepare context for LLM
    history_for_llm = st.session_state.messages[-10:]
    file_context_for_llm = st.session_state.uploaded_file_data # Use full, updated context

    # 4. Get LLM Response
    with message_container: # Display assistant message in the same container
        with st.chat_message("assistant"):
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

    # 5. Rerun is handled implicitly by st.chat_input submission or explicitly if needed
    # Check if a manual rerun is needed to clear staging display if processing happened
    # but maybe not strictly required as chat_input causes rerun anyway.
    # st.rerun() # Might cause double rerun, test without first

# --- Display Stop App Warning (if applicable) ---
if st.session_state.stop_app:
     st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
