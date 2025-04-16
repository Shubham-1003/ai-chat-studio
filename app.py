# app.py (Updated for Streamlit Secrets)

import streamlit as st
from PIL import Image
import os
from utils import llm_api, file_parser # Use the utility modules

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Chat Studio",
    page_icon="✨",
    layout="wide" # Changed layout to 'wide'
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
    st.session_state.messages = [] # Stores chat history: {"role": "user/assistant", "content": "...", "files": []}
if "selected_model" not in st.session_state:
    # Default to first model if available, otherwise handle gracefully
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    st.session_state.selected_model = available_models[0] if available_models else None
if "api_keys" not in st.session_state:
    st.session_state.api_keys = {} # Stores API keys loaded from secrets
if "uploaded_file_data" not in st.session_state:
    # Stores processed content and metadata of uploaded files
    # Format: {"filename": {"content": "...", "metadata": {...}}}
    st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state:
    st.session_state.stop_app = False # Flag to stop app execution if keys are missing

# --- Helper Functions ---
def display_file_card(filename, metadata):
    """Displays a small card for an uploaded file."""
    file_type = metadata.get("type", "unknown")
    file_size = metadata.get("size", 0)
    # Simple preview for text-based content stored directly
    content_preview = st.session_state.uploaded_file_data[filename].get("content", "")
    if isinstance(content_preview, str) and len(content_preview) > 100:
        content_preview = content_preview[:100] + "..."
    elif not isinstance(content_preview, str):
        content_preview = f"[{file_type} content]" # Placeholder for non-text

    with st.expander(f"📄 {filename} ({file_type} - {file_size / 1024:.1f} KB)", expanded=False):
        st.markdown(f"**Preview:**")
        # Use st.code for potentially long text to make it scrollable
        if isinstance(content_preview, str):
            st.code(content_preview, language=None) # 'None' prevents syntax highlighting
        else:
            st.text(content_preview) # Keep original for non-string


# --- Sidebar ---
with st.sidebar:
    st.title("✨ AI Chat Studio")
    st.markdown("---")

    # --- Model Selection ---
    st.subheader("🤖 Model Selection")
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models:
        st.error("No models configured in `utils/llm_api.py`. Please check the configuration.")
        st.stop() # Stop if no models are defined

    # Ensure default model is valid
    if st.session_state.selected_model not in available_models:
        st.session_state.selected_model = available_models[0]

    selected_model_display_name = st.selectbox(
        "Choose an LLM:",
        options=available_models,
        index=available_models.index(st.session_state.selected_model), # Keep selection
        key="model_selector" # Add unique key
    )
    # Update session state only if selection changes
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name
        # Clear API key status message when model changes, it will be re-evaluated
        st.session_state.stop_app = False
        st.rerun() # Rerun to update capabilities and key checks

    # Display capabilities based on the potentially updated selection
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.info(f"Capabilities: {', '.join(model_capabilities)}")
    st.markdown("---")

    # --- API Key Status (Using Secrets) ---
    st.subheader("🔑 API Keys Status")
    st.caption("Checking for API keys in `.streamlit/secrets.toml`")

    keys_loaded_from_secrets = {}
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    required_key_found = False

    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets:
            keys_loaded_from_secrets[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
            required_key_found = True
        else:
            st.warning(f"Required key ({required_key_name_for_selected}) for {st.session_state.selected_model} missing in secrets.toml.", icon="⚠️")
    else:
        # No specific key mapped for this provider (e.g., maybe a local model later?)
        st.info(f"No specific API key mapping found for {st.session_state.selected_model}'s provider.")
        required_key_found = True # Treat as found if none is expected

    # Store only the necessary loaded keys in session state
    st.session_state.api_keys = keys_loaded_from_secrets

    if not required_key_found:
        st.error(f"Please add the key '{required_key_name_for_selected}' to your .streamlit/secrets.toml file to use {st.session_state.selected_model}.")
        st.session_state.stop_app = True # Set flag to stop main execution
    else:
        st.success(f"Required API key for {st.session_state.selected_model} found.", icon="✅")
        st.session_state.stop_app = False # Ensure flag is reset if key is found


    st.markdown("---")
    # End of modified API Key section

    # --- File Upload ---
    st.subheader("📁 File Upload")
    allowed_types = ["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"]
    # Disable uploader if API keys are missing to prevent processing without chat capability
    uploader_disabled = st.session_state.stop_app
    uploaded_files = st.file_uploader(
        "Upload files",
        type=allowed_types,
        accept_multiple_files=True,
        label_visibility="collapsed", # Keep UI clean
        disabled=uploader_disabled,
        key="file_uploader" # Add unique key
    )

    # --- Process Uploaded Files ---
    if uploaded_files and not uploader_disabled:
        new_files_processed = False
        with st.spinner("Processing uploaded files..."):
            for uploaded_file in uploaded_files:
                # Check if file is already processed to avoid reprocessing on reruns
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
            st.success(f"Processed {len(uploaded_files)} new file(s). Ready for interaction.")
            # Don't rerun here automatically, let user interact

    # --- Display Uploaded Files in Sidebar ---
    if st.session_state.uploaded_file_data:
        st.markdown("---")
        st.subheader("Uploaded Files")
        # Sort files alphabetically by name for consistent order
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            data = st.session_state.uploaded_file_data[filename]
            display_file_card(filename, data["metadata"])

        # Add clear button outside the loop
        if st.button("Clear All Files"):
            st.session_state.uploaded_file_data = {}
            st.session_state.messages.append({"role": "system", "content": "All uploaded files have been cleared."})
            st.rerun()


# --- Main Chat Interface ---

# Stop execution here if the required API key was not found
if st.session_state.stop_app:
    st.error("Application halted. Please provide the required API key in `.streamlit/secrets.toml` and refresh.")
    st.stop()


st.header(f"Chat with {st.session_state.selected_model}")

# --- Display Prior Chat Messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Display text content
        st.markdown(message["content"])

        # Display generated file download links if they exist in the message
        if "generated_files" in message and message["generated_files"]:
            for file_info in message["generated_files"]:
                # Ensure content is bytes or string before passing
                file_content = file_info.get("content", "")
                if isinstance(file_content, (str, bytes)):
                    file_parser.generate_download_link(
                        content=file_content,
                        filename=file_info.get("filename", "download"),
                        link_text=f"Download {file_info.get('filename', 'file')}"
                    )
                else:
                    st.warning(f"Cannot generate download for non-text/bytes content: {file_info.get('filename')}")


# --- Chat Input Handling ---
# Use st.chat_input which is designed to stick to the bottom
prompt = st.chat_input(f"Ask {st.session_state.selected_model} anything...")

if prompt:
    # 1. Add User Message to History and Display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Prepare context for the LLM
    # Include recent chat history (adjust length as needed)
    history_for_llm = st.session_state.messages[-10:] # Send last 10 messages (user+assistant+system)

    # Include processed file data (content + metadata)
    file_context_for_llm = st.session_state.uploaded_file_data

    # 3. Get Response from LLM
    with st.chat_message("assistant"):
        message_placeholder = st.empty() # Placeholder for streaming/final response
        message_placeholder.markdown("🧠 Thinking...")

        # Call the LLM API via the utility function
        try:
            # Retrieve capabilities again in case model changed just before prompt
            current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)

            response_text, generated_file_info = llm_api.get_llm_response(
                model_display_name=st.session_state.selected_model,
                messages=history_for_llm,
                api_keys=st.session_state.api_keys, # Pass keys loaded from secrets
                uploaded_file_context=file_context_for_llm, # Pass processed data
                model_capabilities=current_model_capabilities # Pass capabilities like 'vision'
            )
            message_placeholder.markdown(response_text)

            # Store response and any generated file info
            assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
            if generated_file_info and isinstance(generated_file_info, dict):
                # Assuming generated_file_info is like {"filename": "...", "content": "..."}
                assistant_message["generated_files"].append(generated_file_info)
                 # Display download button immediately if content is valid
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
            st.error(f"An error occurred while communicating with the LLM: {e}")
            # Add error to chat history for context
            error_message = f"Sorry, I encountered an error trying to get a response: {e}"
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            # Update the placeholder directly with the error
            message_placeholder.markdown(error_message)