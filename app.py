# app.py (Updated for Streamlit Secrets & Specific NVIDIA Keys & New Chat)

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
    st.session_state.api_keys = {}
if "uploaded_file_data" not in st.session_state:
    st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state:
    st.session_state.stop_app = False

# --- Helper Functions ---
def display_file_card(filename, metadata):
    """Displays a small card for an uploaded file."""
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

    # --- Add New Chat Button --- <<< NEW SECTION START
    if st.button("➕ New Chat"):
        st.session_state.messages = [] # Clear chat history
        # Optionally add a default starting message?
        # st.session_state.messages.append({"role": "system", "content": "Chat cleared. Ask me anything!"})
        st.rerun() # Rerun the app to clear the chat display
    # --- Add New Chat Button --- <<< NEW SECTION END

    st.markdown("---") # Separator

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
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name
        st.session_state.stop_app = False
        st.rerun()

    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")

    # --- API Key Status (Using Secrets) ---
    st.subheader("🔑 API Keys Status")
    st.caption("Checking for API keys in `.streamlit/secrets.toml`")
    st.caption("Note: NVIDIA models require specific keys like 'NVIDIA_Mistral_Small_24B_Instruct' in secrets.")

    keys_loaded_from_secrets = {}
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    required_key_found = False

    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets:
            keys_loaded_from_secrets[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
            required_key_found = True
        else:
            st.warning(f"Required key ('{required_key_name_for_selected}') for {st.session_state.selected_model} missing in secrets.toml.", icon="⚠️")
    else:
        st.info(f"No specific API key required for {st.session_state.selected_model}.") # Clarified message
        required_key_found = True # Treat as found if none is required

    st.session_state.api_keys = keys_loaded_from_secrets

    if not required_key_found and required_key_name_for_selected:
        st.error(f"Please add the key '{required_key_name_for_selected}' to your .streamlit/secrets.toml file and restart.")
        st.session_state.stop_app = True
    elif required_key_found:
        st.success(f"Required API key ('{required_key_name_for_selected}') found for {st.session_state.selected_model}.", icon="✅")
        st.session_state.stop_app = False
    elif not required_key_name_for_selected:
         # Condition where no key is needed, app should not stop
         st.session_state.stop_app = False


    st.markdown("---")

    # --- File Upload ---
    st.subheader("📁 File Upload")
    allowed_types = ["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"]
    uploader_disabled = st.session_state.stop_app
    uploaded_files = st.file_uploader(
        "Upload files",
        type=allowed_types,
        accept_multiple_files=True,
        label_visibility="collapsed",
        disabled=uploader_disabled,
        key="file_uploader"
    )

    if uploaded_files and not uploader_disabled:
        new_files_processed = False
        with st.spinner("Processing uploaded files..."):
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state.uploaded_file_data:
                    content, metadata = file_parser.process_uploaded_file(uploaded_file)
                    if content is not None:
                        st.session_state.uploaded_file_data[uploaded_file.name] = {
                            "content": content,
                            "metadata": metadata
                        }
                        new_files_processed = True
        if new_files_processed:
            st.success(f"Processed {len(uploaded_files)} new file(s). Ready for interaction.")

    if st.session_state.uploaded_file_data:
        st.markdown("---")
        st.subheader("Uploaded Files")
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                data = st.session_state.uploaded_file_data[filename]
                display_file_card(filename, data["metadata"])
            else:
                 st.warning(f"Data for {filename} not found in session state. Skipping display.")

        if st.button("Clear All Files"):
            st.session_state.uploaded_file_data = {}
            st.rerun()

# --- Main Chat Interface ---
if st.session_state.stop_app:
    st.error("Application halted. Please provide the required API key(s) in `.streamlit/secrets.toml` and restart.")
    st.stop()

st.header(f"Chat with {st.session_state.selected_model}")

# Display messages (will be empty after New Chat is clicked and rerun)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
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

prompt = st.chat_input(f"Ask {st.session_state.selected_model} anything...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history_for_llm = st.session_state.messages[-10:]
    file_context_for_llm = st.session_state.uploaded_file_data

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
        except Exception as e:
            st.error(f"An error occurred: {e}")
            error_message = f"Sorry, I encountered an error trying to get a response. Please check API keys and model availability. Error: {e}"
            if not st.session_state.messages or st.session_state.messages[-1].get("content") != error_message:
                st.session_state.messages.append({"role": "assistant", "content": error_message})
            message_placeholder.error(error_message)
