# app.py (Updated - Sections Removed, Uploader Moved)

import streamlit as st
from PIL import Image
import os
from utils import llm_api, file_parser # Use the utility modules

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

load_css("css/style.css")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_model" not in st.session_state:
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    st.session_state.selected_model = available_models[0] if available_models else None
if "api_keys" not in st.session_state:
    st.session_state.api_keys = {} # Still needed for the API call function
if "uploaded_file_data" not in st.session_state:
    st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state:
    st.session_state.stop_app = False # Keep internal flag, though UI is removed

# --- Helper Functions ---
def display_file_card(filename, metadata):
    """Displays a small card for an uploaded file in the sidebar."""
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
        st.rerun()

    st.markdown("---")

    # --- Model Selection ---
    st.subheader("🤖 Model Selection")
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models:
        st.error("No models configured in `utils/llm_api.py`. Please check the configuration.")
        st.stop()

    if st.session_state.selected_model not in available_models:
        st.session_state.selected_model = available_models[0]

    selected_model_display_name = st.selectbox(
        "Choose an LLM:",
        options=available_models,
        index=available_models.index(st.session_state.selected_model),
        key="model_selector"
    )
    # API Key Check (Internal Logic - No UI Feedback Here Anymore)
    # We still need to load the key for the API call function later
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    st.session_state.api_keys = {} # Reset keys found
    st.session_state.stop_app = False # Assume okay unless key is needed and missing

    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets:
            st.session_state.api_keys[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
        else:
            # Key is missing, set flag to stop chat input later, but don't display error here
            st.session_state.stop_app = True
            # Optionally log this for debugging if running locally
            # print(f"Debug: Missing key {required_key_name_for_selected}")

    # Update model if changed
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name
        # Rerun necessary to update internal API key check and capabilities display
        st.rerun()

    # Display Capabilities
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")

    # --- API Keys Status Section Removed ---

    # --- File Upload Section Removed from Sidebar ---

    # --- Display Uploaded Files (Remains in Sidebar) ---
    if st.session_state.uploaded_file_data:
        st.subheader("Uploaded Files")
        # Sort files alphabetically by name for consistent order
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data: # Check if key exists before accessing
                data = st.session_state.uploaded_file_data[filename]
                display_file_card(filename, data["metadata"]) # Call the helper function
            else:
                 # This might happen briefly during reruns, should resolve
                 # st.warning(f"Data for {filename} not found in session state. Skipping display.")
                 pass # Avoid cluttering sidebar with transient warnings


        # Add clear button
        if st.button("Clear All Uploaded Files"):
            st.session_state.uploaded_file_data = {}
            st.toast("Uploaded files cleared.") # Use toast for less intrusive message
            st.rerun()
        st.markdown("---")


# --- Main Chat Interface ---
st.header(f"Chat with {st.session_state.selected_model}")

# --- Display Prior Chat Messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # (Code for displaying generated files remains the same)
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

# --- File Uploader (Moved Above Chat Input) --- <<< NEW SECTION START
allowed_types = ["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"]
# Use a key to access the uploader's state
uploaded_files_main = st.file_uploader(
    "Attach files",
    type=allowed_types,
    accept_multiple_files=True,
    label_visibility="collapsed", # Hide the default label
    key="main_file_uploader" # Unique key for this uploader
)

# --- Process Uploaded Files (Logic Moved Here) ---
if uploaded_files_main: # Check if files were uploaded via the new uploader
    new_files_processed = False
    with st.spinner("Processing attached files..."): # Spinner shown in main area
        for uploaded_file in uploaded_files_main:
            # Check if file is already processed to avoid reprocessing
            if uploaded_file.name not in st.session_state.uploaded_file_data:
                # Process and store file content and metadata
                content, metadata = file_parser.process_uploaded_file(uploaded_file)
                if content is not None: # Check if processing was successful
                    st.session_state.uploaded_file_data[uploaded_file.name] = {
                        "content": content,
                        "metadata": metadata
                    }
                    new_files_processed = True
    if new_files_processed:
        st.toast(f"Processed {len(uploaded_files_main)} file(s).") # Use toast
        # We need to rerun ONLY IF new files were processed to update the sidebar display
        st.rerun()
# --- END OF NEW FILE UPLOADER SECTION ---


# --- Chat Input Handling ---
# Check if the app should be stopped due to missing API key BEFORE showing input
chat_input_disabled = st.session_state.stop_app
chat_placeholder = f"Ask {st.session_state.selected_model} anything..."
if chat_input_disabled:
    chat_placeholder = f"Cannot chat: API key for {st.session_state.selected_model} missing in secrets.toml"

prompt = st.chat_input(
    chat_placeholder,
    disabled=chat_input_disabled, # Disable input if key is missing
    key="chat_input"
)

if prompt and not chat_input_disabled:
    # 1. Add User Message to History and Display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Prepare context for the LLM
    history_for_llm = st.session_state.messages[-10:]
    # Use the globally updated file data
    file_context_for_llm = st.session_state.uploaded_file_data

    # 3. Get Response from LLM
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🧠 Thinking...")
        try:
            current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)

            # Pass the API keys loaded during sidebar rendering
            response_text, generated_file_info = llm_api.get_llm_response(
                model_display_name=st.session_state.selected_model,
                messages=history_for_llm,
                api_keys=st.session_state.api_keys, # Use keys loaded earlier
                uploaded_file_context=file_context_for_llm,
                model_capabilities=current_model_capabilities
            )
            message_placeholder.markdown(response_text)
            assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
            # (Code for handling generated files remains the same)
            if generated_file_info and isinstance(generated_file_info, dict):
                 assistant_message["generated_files"].append(generated_file_info)
                 file_content = generated_file_info.get("content", "")
                 if isinstance(file_content, (str, bytes)):
                      file_parser.generate_download_link(
                         file_content,
                         generated_file_info.get("filename", "download"),
                         f"Download {generated_file_info.get('filename', 'file')}"
                      )
                 else:
                      st.warning(f"Cannot generate download for non-text/bytes generated content: {generated_file_info.get('filename')}")
            st.session_state.messages.append(assistant_message)

        except ValueError as ve: # Catch specific API key errors from llm_api
             st.error(f"Configuration Error: {ve}")
             error_message = f"Sorry, could not get response due to a configuration issue: {ve}"
             if not st.session_state.messages or st.session_state.messages[-1].get("content") != error_message:
                 st.session_state.messages.append({"role": "assistant", "content": error_message})
             message_placeholder.error(error_message)
        except Exception as e:
            st.error(f"An error occurred: {e}")
            error_message = f"Sorry, I encountered an error trying to get a response. Please check API keys and model availability. Error: {e}"
            if not st.session_state.messages or st.session_state.messages[-1].get("content") != error_message:
                st.session_state.messages.append({"role": "assistant", "content": error_message})
            message_placeholder.error(error_message)

# Add a visual indicator if the app is halted due to missing keys (optional)
if st.session_state.stop_app:
    st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart the application.", icon="⚠️")
