# app.py (Simulated Input Bar for File Staging)

import streamlit as st
from PIL import Image
import io # Needed for staged file display
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

# Add CSS to try and push input elements down (basic approach)
# More robust solution might need custom component or complex CSS
st.markdown("""
<style>
.stApp {
    /* Add padding to the bottom to push content up */
    /* Adjust the value as needed */
    /* padding-bottom: 150px; */
}
.simulated-input-bar-container {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: var(--bg-light, #f0f4f8); /* Match your background */
    padding: 1rem 2rem; /* Adjust padding */
    box-shadow: 0 -4px 10px rgba(0, 0, 0, 0.05);
    z-index: 99;
    border-top: 1px solid #e0e0e0;
}
/* Target the specific columns container for the input bar */
[data-testid="stHorizontalBlock"] .stButton>button {
    /* Make buttons less tall */
     height: 2.5em;
     /* padding-top: 0.5em;
     padding-bottom: 0.5em; */
}
[data-testid="stHorizontalBlock"] .stTextInput>div>div>input {
    height: 2.5em; /* Match button height */
}

/* Style file uploader button */
[data-testid="stFileUploader"] label {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.4em 0.8em !important; /* Adjust padding */
    border-radius: var(--radius, 16px);
    height: 2.5em;
    width: 3em; /* Adjust width */
    box-sizing: border-box;
}
[data-testid="stFileUploader"] label svg {
    /* Hide default icon if needed */
    /* display: none; */
}
[data-testid="stFileUploader"] label::before {
    /* Add '+' icon using content */
    content: "📎"; /* Use an attachment icon */
    font-size: 1.2em; /* Adjust size */
}
[data-testid="stFileUploader"] section {
    /* Hide the drag/drop text */
     padding: 0 !important;
     border: none !important;
}
[data-testid="stFileUploader"] small {
    display: none; /* Hide the file size limit text */
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
if "uploaded_file_data" not in st.session_state: # Holds processed context data
    st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state:
    st.session_state.stop_app = False
if "staged_files" not in st.session_state: # Holds UploadedFile objects before sending <<< NEW
    st.session_state.staged_files = []
if "current_prompt" not in st.session_state: # Holds text from text_input <<< NEW
    st.session_state.current_prompt = ""

# --- Helper Functions ---
def display_processed_file_card(filename, metadata):
    """Displays a card for a fully processed file in the sidebar."""
    # (Same as previous display_file_card)
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

def display_staged_file_card(uploaded_file, index):
    """Displays a small card for a file staged for upload."""
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        # Show limited info, maybe an icon based on type
        file_type = uploaded_file.type or "unknown"
        icon = "📄"
        if "image" in file_type: icon = "🖼️"
        elif "pdf" in file_type: icon = "📕"
        st.caption(f"{icon} {uploaded_file.name} ({(uploaded_file.size / 1024):.1f} KB)")
    with col2:
        # Button to remove the file from staging
        if st.button("✖️", key=f"remove_staged_{index}", help="Remove file"):
            st.session_state.staged_files.pop(index)
            st.rerun()

# --- Sidebar ---
with st.sidebar:
    st.title("✨ AI Chat Studio")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.session_state.uploaded_file_data = {} # Clear processed files too
        st.session_state.staged_files = [] # Clear staged files
        st.session_state.current_prompt = "" # Clear prompt buffer
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
            st.session_state.stop_app = True # Stop input later

    # Update model if changed
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name
        st.rerun() # Rerun needed to update internal key check

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

# Container for chat messages (allows input bar to be potentially pushed down)
# We need enough content or padding to push the fixed input bar up
chat_container = st.container()
with chat_container:
    # --- Display Prior Chat Messages ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # (Code for displaying generated files remains the same)
            if "generated_files" in message and message["generated_files"]:
                 # ... (download link generation) ...
                 pass # Simplified for brevity

# --- Simulated Input Bar Area (at the bottom) ---
st.markdown('<div class="simulated-input-bar-container">', unsafe_allow_html=True)

# --- Staging Area Display (Inside the fixed container) ---
if st.session_state.staged_files:
    st.caption("Files attached to next message:")
    # Use columns for horizontal layout if many files? For now, vertical.
    for i, file in enumerate(st.session_state.staged_files):
        display_staged_file_card(file, i)
    st.markdown("---") # Separator

# --- Input Row: Uploader + Text Input + Send Button ---
col1, col2, col3 = st.columns([1, 8, 1]) # Adjust ratios as needed

with col1:
    # File Uploader styled as a button
    uploaded_files_staged = st.file_uploader(
        "Attach", # Shorter label, potentially hidden by CSS
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "ipynb", "zip"],
        accept_multiple_files=True,
        label_visibility="collapsed", # Important: Use CSS to style the button part
        key="staged_uploader"
    )
    # Add newly uploaded files to the staging area
    if uploaded_files_staged:
        newly_added = False
        for file in uploaded_files_staged:
            # Avoid duplicates in staging if user uploads same file again
            if file not in st.session_state.staged_files:
                 st.session_state.staged_files.append(file)
                 newly_added = True
        if newly_added:
             st.toast(f"Added {len(uploaded_files_staged)} file(s) to stage.")
             # Rerun to display staged files and clear the uploader widget state
             st.rerun()


with col2:
    # Text Input
    prompt_input = st.text_input(
        "Ask anything...",
        value=st.session_state.current_prompt, # Bind to session state
        key="text_prompt_input",
        placeholder=f"Ask {st.session_state.selected_model} anything..." if not st.session_state.stop_app else f"Cannot chat: API key for {st.session_state.selected_model} missing",
        disabled=st.session_state.stop_app,
        label_visibility="collapsed"
    )
    # Update session state as user types (optional, useful if complex interactions needed)
    st.session_state.current_prompt = prompt_input

with col3:
    # Send Button
    send_button_pressed = st.button(
        "Send",
        key="send_button",
        disabled=st.session_state.stop_app or not prompt_input, # Disable if no text or app stopped
        type="primary" # Make it stand out
    )

st.markdown('</div>', unsafe_allow_html=True) # Close the fixed container


# --- Handle Send Action ---
if send_button_pressed and prompt_input and not st.session_state.stop_app:

    # 1. Process Staged Files and add to main context
    files_processed_this_turn = {}
    if st.session_state.staged_files:
        with st.spinner("Processing attachments..."):
            for staged_file in st.session_state.staged_files:
                 # Avoid reprocessing if somehow already in main context (e.g., from previous turn)
                 if staged_file.name not in st.session_state.uploaded_file_data:
                     content, metadata = file_parser.process_uploaded_file(staged_file)
                     if content is not None:
                         st.session_state.uploaded_file_data[staged_file.name] = {
                             "content": content,
                             "metadata": metadata
                         }
                         files_processed_this_turn[staged_file.name] = metadata # Track what was new

    # 2. Add User Message to History
    user_message_content = prompt_input
    # Optionally mention attached files in the user message itself
    if files_processed_this_turn:
        user_message_content += "\n\n*(Attached files: " + ", ".join(files_processed_this_turn.keys()) + ")*"

    st.session_state.messages.append({"role": "user", "content": user_message_content})

    # 3. Prepare context (using the now updated global file data)
    history_for_llm = st.session_state.messages[-10:]
    file_context_for_llm = st.session_state.uploaded_file_data # Use the full context

    # 4. Clear Staged Files and Input Buffer from Session State
    st.session_state.staged_files = []
    st.session_state.current_prompt = "" # Clear prompt buffer

    # 5. Call LLM and Display Response (within the main chat container)
    with chat_container: # Ensure response appears in the right place
        with st.chat_message("user"): # Display the user message again (already done by rerun technically, but good for flow)
            st.markdown(user_message_content)

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
                # ... (handle generated files download) ...
                st.session_state.messages.append(assistant_message)

            except ValueError as ve:
                 st.error(f"Configuration Error: {ve}")
                 error_message = f"Sorry, could not get response due to a configuration issue: {ve}"
                 if not st.session_state.messages or st.session_state.messages[-1].get("content") != error_message:
                     st.session_state.messages.append({"role": "assistant", "content": error_message})
                 message_placeholder.error(error_message)
            except Exception as e:
                st.error(f"An error occurred: {e}")
                error_message = f"Sorry, I encountered an error trying to get a response. Error: {e}"
                if not st.session_state.messages or st.session_state.messages[-1].get("content") != error_message:
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                message_placeholder.error(error_message)

    # 6. Rerun to clear the text_input widget and update displays
    st.rerun()


# --- Display Stop App Warning (if applicable) ---
if st.session_state.stop_app:
     st.warning(f"Chat input disabled. Please ensure the required API key ('{required_key_name_for_selected}') is in your `.streamlit/secrets.toml` and restart.", icon="⚠️")
