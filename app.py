# app.py (Claude's Attempt - Fixed st.text_area Wrapper, Disabled JS Height Adjust)

import streamlit as st
from PIL import Image
import io
import os
import time
import random
import markdown # Requires: pip install markdown
from utils import llm_api, file_parser

# --- Page Configuration ---
st.set_page_config( page_title="AI Chat Interface", page_icon="🤖", layout="wide", initial_sidebar_state="expanded" )

# --- Custom CSS ---
# WARNING: Highly fragile CSS overrides
st.markdown(""" <style> /* ... (All the CSS from the previous version) ... */ </style> """, unsafe_allow_html=True)

# --- Custom JavaScript ---
# WARNING: JavaScript injection is fragile
st.markdown("""
<script>
    // Function to auto-resize textarea (COMMENTED OUT)
    // function autoGrow(element) { /* ... */ }

    // Attach event listener function
    function attachListeners() {
        const textarea = document.querySelector('textarea[aria-label="Your message"]');
        const hiddenSendButton = document.getElementById('hidden-send-trigger-button');
        const htmlSendButton = document.getElementById('send-button-html');

        if (textarea && !textarea.dataset.listenerAttached) {
            // Auto-grow listener REMOVED
            textarea.addEventListener('keydown', function(e) { // Enter key listener remains
                if (e.key === 'Enter' && !e.shiftKey && hiddenSendButton && !hiddenSendButton.disabled) {
                    e.preventDefault();
                    hiddenSendButton.click();
                }
            });
            textarea.dataset.listenerAttached = 'true';
            // Initial auto-grow call REMOVED
        }

        // Sync disabled state
        if (htmlSendButton && hiddenSendButton) {
            htmlSendButton.disabled = hiddenSendButton.disabled;
            htmlSendButton.style.opacity = hiddenSendButton.disabled ? '0.5' : '1';
        }

        // File Remove Button Listeners (Still Unreliable)
        const removeButtons = document.querySelectorAll('.remove-btn');
        removeButtons.forEach(btn => {
             if (!btn.dataset.listenerAttached) {
                const index = btn.dataset.index;
                const hiddenRemoveButtonId = `remove-btn-${index}-hidden`;
                 btn.addEventListener('click', function() {
                     const hiddenRemoveButton = document.getElementById(hiddenRemoveButtonId);
                     if (hiddenRemoveButton) { hiddenRemoveButton.click(); }
                     else { console.error(`Hidden Remove button not found by ID: ${hiddenRemoveButtonId}`); }
                 });
                 btn.dataset.listenerAttached = 'true';
             }
         });
    }

    // MutationObserver setup (same as before)
    const observer = new MutationObserver((mutationsList, observer) => { attachListeners(); });
    observer.observe(document.body, { childList: true, subtree: true });
    document.addEventListener('DOMContentLoaded', attachListeners);

</script>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
# (Same as before)
if "messages" not in st.session_state: st.session_state.messages = []
if "selected_model" not in st.session_state:
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    st.session_state.selected_model = available_models[0] if available_models else None
if "api_keys" not in st.session_state: st.session_state.api_keys = {}
if "uploaded_file_data" not in st.session_state: st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state: st.session_state.stop_app = False
if "staged_files" not in st.session_state: st.session_state.staged_files = []
if "thinking" not in st.session_state: st.session_state.thinking = False
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_" + str(int(time.time()))
if "chat_history" not in st.session_state: st.session_state.chat_history = {st.session_state.current_chat_id: {"title": "New Chat", "messages": [], "context_files": {}}}
if "example_queries" not in st.session_state: st.session_state.example_queries = ["Explain quantum computing", "Suggest Python libraries", "Write a short story", "How does photosynthesis work?"]
if "show_file_uploader" not in st.session_state: st.session_state.show_file_uploader = False


# --- Helper Functions ---
# (create_new_chat, load_chat, update_chat_title, display_chat_message, remove_staged_file, process_staged_files - all same as before)
def create_new_chat():
    chat_id = "chat_" + str(int(time.time())); st.session_state.chat_history[chat_id] = {"title": "New Chat", "messages": [], "context_files": {}}
    st.session_state.current_chat_id = chat_id; st.session_state.messages = []; st.session_state.uploaded_file_data = {}; st.session_state.staged_files = []; st.session_state.show_file_uploader = False
    st.rerun()
def load_chat(chat_id):
    if chat_id in st.session_state.chat_history:
        st.session_state.current_chat_id = chat_id; st.session_state.messages = st.session_state.chat_history[chat_id].get("messages", [])
        st.session_state.uploaded_file_data = st.session_state.chat_history[chat_id].get("context_files", {}); st.session_state.staged_files = []; st.session_state.show_file_uploader = False
        st.rerun()
def update_chat_title():
    if st.session_state.messages and st.session_state.messages[0]["role"] == "user":
        first_message = st.session_state.messages[0]["content"]; title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        st.session_state.chat_history[st.session_state.current_chat_id]["title"] = title
def display_chat_message(message):
    role = message["role"]; content = message["content"]; avatar_icon = "U" if role == "user" else "🤖"; avatar_class = "user" if role == "user" else "bot"; message_class = "user" if role == "user" else "bot"
    try: extensions = ['fenced_code', 'codehilite', 'tables', 'nl2br', 'sane_lists']; content_html = markdown.markdown(content, extensions=extensions)
    except ImportError: content_html = content.replace("&", "&").replace("<", "<").replace(">", ">").replace("\n", "<br>")
    except Exception as md_err: st.error(f"MD Error: {md_err}"); content_html = content.replace("&", "&").replace("<", "<").replace(">", ">").replace("\n", "<br>")
    st.markdown(f""" <div class="chat-message-container"> <div class="chat-message {message_class}"> <div class="avatar {avatar_class}"> <span>{avatar_icon}</span> </div> <div class="message-content"> {content_html} </div> </div> </div> """, unsafe_allow_html=True)
def remove_staged_file(file_index_to_remove):
    try:
        if 0 <= file_index_to_remove < len(st.session_state.staged_files): st.session_state.staged_files.pop(file_index_to_remove); st.rerun()
    except Exception as e: st.error(f"Error removing file: {e}")
def process_staged_files():
    processed_files_names = [];
    if not st.session_state.staged_files: return processed_files_names
    with st.status(f"Processing {len(st.session_state.staged_files)} file(s)...", expanded=False) as status:
        staged_copy = list(st.session_state.staged_files)
        for file in staged_copy:
            if file.name not in st.session_state.uploaded_file_data:
                status.write(f"Processing {file.name}..."); content, metadata = file_parser.process_uploaded_file(file)
                if content is not None: st.session_state.uploaded_file_data[file.name] = {"content": content, "metadata": metadata}; processed_files_names.append(file.name)
                else: status.write(f"⚠️ Failed to process {file.name}")
        st.session_state.chat_history[st.session_state.current_chat_id]["context_files"] = st.session_state.uploaded_file_data; status.update(label=f"Processed {len(processed_files_names)} file(s)!", state="complete")
    st.session_state.staged_files = []
    if processed_files_names: st.toast(f"Added {len(processed_files_names)} file(s) to context.")
    return processed_files_names

# --- Sidebar ---
# (Same as before)
with st.sidebar:
    st.markdown('<h1 style="color: white; margin-bottom: 20px;">💬 AI Chat</h1>', unsafe_allow_html=True);
    if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"): create_new_chat()
    st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True); st.markdown('<h3 style="color: white; margin-bottom: 10px;">Chat History</h3>', unsafe_allow_html=True)
    sorted_chat_ids = sorted(st.session_state.chat_history.keys(), reverse=True)
    for chat_id in sorted_chat_ids: chat_data = st.session_state.chat_history[chat_id]; chat_title = chat_data.get("title", "Chat");
    if st.button(f"{chat_title}", key=f"load_chat_{chat_id}", use_container_width=True): load_chat(chat_id)
    st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True); st.markdown('<h3 style="color: white; margin-bottom: 10px;">Model Settings</h3>', unsafe_allow_html=True)
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models: st.error("No models configured."); st.stop()
    if st.session_state.selected_model not in available_models: st.session_state.selected_model = available_models[0]
    selected_model_display_name = st.selectbox("Choose a model:", options=available_models, index=available_models.index(st.session_state.selected_model), key="model_selector")
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    st.session_state.api_keys = {}; st.session_state.stop_app = False
    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets: st.session_state.api_keys[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
        else: st.session_state.stop_app = True
    if selected_model_display_name != st.session_state.selected_model: st.session_state.selected_model = selected_model_display_name; st.rerun()
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.markdown(f'<div style="color: #aaa; font-size: 12px; margin-top: 5px;">Capabilities: {", ".join(model_capabilities)}</div>', unsafe_allow_html=True)
    if st.session_state.uploaded_file_data:
        st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True); st.markdown('<h3 style="color: white; margin-bottom: 10px;">Uploaded Files</h3>', unsafe_allow_html=True)
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data: metadata = st.session_state.uploaded_file_data[filename]["metadata"]; file_type = metadata.get("type", "unknown"); st.markdown(f'<div style="color: #ccc; font-size: 0.9em; padding: 2px 0;">📎 {filename} ({file_type})</div>', unsafe_allow_html=True)
        if st.button("Clear All Files", use_container_width=True, key="clear_files_btn"): st.session_state.uploaded_file_data = {}; st.toast("Cleared context files."); st.rerun()

# --- Main Chat Area ---
chat_display_container = st.container()
with chat_display_container:
    if not st.session_state.messages: pass
    else:
        for message in st.session_state.messages: display_chat_message(message)

# --- LLM Response Trigger ---
if st.session_state.thinking:
    with chat_display_container: st.markdown(f""" <div class="chat-message-container"> <div class="chat-message bot"> <div class="avatar bot"><span>🤖</span></div> <div class="message-content"><div class="thinking-animation"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div></div> </div> </div> """, unsafe_allow_html=True)
    history_for_llm = st.session_state.messages[-10:]; file_context_for_llm = st.session_state.uploaded_file_data; current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    try:
        response_text, _ = llm_api.get_llm_response( model_display_name=st.session_state.selected_model, messages=history_for_llm, api_keys=st.session_state.api_keys, uploaded_file_context=file_context_for_llm, model_capabilities=current_model_capabilities )
        assistant_message = {"role": "assistant", "content": response_text}; st.session_state.messages.append(assistant_message); st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages
    except Exception as e: st.error(f"An error occurred: {e}"); error_message = f"Sorry, error occurred: {e}"; st.session_state.messages.append({"role": "assistant", "content": error_message}); st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages
    finally: st.session_state.thinking = False; st.rerun()

# --- Fixed Chat Input Area at Bottom ---
st.markdown('<div class="chat-input-area-wrapper">', unsafe_allow_html=True)
st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)

# --- Staging Area ---
# (Same as before)
if st.session_state.staged_files:
    st.markdown('<div class="staging-area">', unsafe_allow_html=True)
    staged_file_copy = list(st.session_state.staged_files); hidden_remove_buttons = {}
    for i, file in enumerate(staged_file_copy):
        hidden_btn_id = f"remove-btn-{i}-hidden"
        st.markdown(f""" <span class="file-badge"> 📎 {file.name} <button class="remove-btn" data-index="{i}" title="Remove {file.name}" onclick="document.getElementById('{hidden_btn_id}').click()">×</button> </span> """, unsafe_allow_html=True)
        hidden_remove_buttons[i] = {"id": hidden_btn_id, "file_name": file.name}
    st.markdown('</div>', unsafe_allow_html=True)
    # Render hidden remove buttons
    with st.container():
         st.markdown("<style>div[data-testid='stVerticalBlock'] div[data-testid='element-container'] button[key*='-hidden'] { position: absolute; width: 1px; height: 1px; opacity: 0; z-index: -10; }</style>", unsafe_allow_html=True)
         for i, data in hidden_remove_buttons.items(): st.button(f"X{i}", key=data["id"], on_click=remove_staged_file, args=(i,), help=f"Remove {data['file_name']}")

# --- Input Row (using st.columns) ---
input_cols = st.columns([1, 10, 1]) # Attach | Text Area | Send

with input_cols[0]: # Attach button column
    # Use a container to apply class for easier CSS targeting if needed
    # st.markdown('<div class="file-upload-button-container">', unsafe_allow_html=True) # Removed as CSS targets button directly
    if st.button("📎", key="toggle_upload_btn", help="Attach files"):
         st.session_state.show_file_uploader = not st.session_state.show_file_uploader
         st.rerun()
    # st.markdown('</div>', unsafe_allow_html=True)

with input_cols[1]: # Text area column
    # *** REMOVED st.markdown wrapper ***
    prompt = st.text_area(
        "Your message", # Aria-label used by JS
        key="chat_input_textarea",
        placeholder=f"Message {st.session_state.selected_model}..." if not st.session_state.stop_app else "API Key Missing",
        disabled=st.session_state.stop_app or st.session_state.thinking,
        label_visibility="collapsed",
        height=24, # JS will attempt to auto-grow (but JS part is now commented out)
    )

with input_cols[2]: # Send button column
    # Use container to apply CSS class easier
    st.markdown('<div class="send-button-container">', unsafe_allow_html=True)
    is_send_disabled = st.session_state.stop_app or st.session_state.thinking or not prompt.strip()
    # The actual button Streamlit uses, styled via CSS above
    submit_button_clicked = st.button("➤", key="hidden-send-trigger-button", disabled=is_send_disabled, help="Send message")
    st.markdown('</div>', unsafe_allow_html=True)


# --- Conditionally Rendered File Uploader ---
if st.session_state.show_file_uploader:
    uploaded_files = st.file_uploader(
        "Attach files:",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "csv", "xlsx", "ipynb", "zip"],
        accept_multiple_files=True,
        key="actual_file_uploader",
        label_visibility="visible"
    )
    if uploaded_files:
        newly_staged_count = 0
        for file in uploaded_files:
            is_already_staged = any(sf.name == file.name for sf in st.session_state.staged_files)
            if not is_already_staged: st.session_state.staged_files.append(file); newly_staged_count += 1
        if newly_staged_count > 0: st.toast(f"Staged {newly_staged_count} file(s)."); st.session_state.show_file_uploader = False; st.rerun()

st.markdown('</div>', unsafe_allow_html=True) # Close chat-input-area
st.markdown('</div>', unsafe_allow_html=True) # Close chat-input-area-wrapper

# --- Send Logic ---
if submit_button_clicked:
    if prompt and not st.session_state.stop_app and not st.session_state.thinking:
        processed_files_names = process_staged_files()
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages
        if len(st.session_state.messages) == 1: update_chat_title()
        st.session_state.thinking = True
        st.rerun()

# --- Final check/warning ---
if st.session_state.stop_app:
    key_name_warn = required_key_name_for_selected or "API Key"
    st.warning(f"Chat input disabled. API key ('{key_name_warn}') missing.", icon="⚠️")
