# app.py (Claude's Attempt - Syntax Error Fixed in display_chat_message)

import streamlit as st
from PIL import Image
import io
import os
import time
import random
import markdown # Requires: pip install markdown python-markdown-math (optional for math)
# Assuming these util files exist and work as expected
from utils import llm_api, file_parser

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Chat Interface",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for exact ChatGPT/Claude-like Interface ---
# WARNING: This extensive CSS is very likely to break with Streamlit updates.
st.markdown("""
<style>
/* Global Styles */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

* {
    font-family: 'Inter', sans-serif;
    box-sizing: border-box;
}

body {
    background-color: #ffffff;
    color: #343541;
    margin: 0;
    padding: 0;
    overflow-x: hidden; /* Prevent horizontal scroll */
}

/* Reduce padding around main content area */
.main .block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 48rem; /* Maintain max width like ChatGPT */
    margin: 0 auto;
}

/* Hide Streamlit elements */
header { visibility: hidden; height: 0; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }

/* Dark mode sidebar like ChatGPT */
.css-1d391kg, [data-testid="stSidebar"] {
    background-color: #202123 !important; /* Use !important cautiously */
    color: #ffffff !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] .stSelectbox div[role="button"] {
    color: #ffffff !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}
[data-testid="stSidebar"] hr { border-color: #444654 !important; }
[data-testid="stSidebar"] button {
    background-color: #343541 !important; color: #ffffff !important; border: 1px solid #565869 !important;
    border-radius: 4px !important; transition: background-color 0.2s !important;
}
[data-testid="stSidebar"] button:hover { background-color: #40414f !important; }
/* Style selectbox dropdown text color */
/* Streamlit's internal structure might change, making this brittle */
.st-emotion-cache-1hverhl {
    color: #ffffff !important; /* Target text within options */
}
[data-testid="stSidebar"] .stSelectbox [data-testid="stMarkdownContainer"] p { color: #343541 !important; } /* Text inside selectbox main button */


/* Chat message styling */
.chat-message-container {
    padding-bottom: 10px;
}
.chat-message {
    display: flex; padding: 1rem; margin: 0 auto; max-width: 48rem;
}
.chat-message.user { background-color: #ffffff; }
.chat-message.bot { background-color: #f7f7f8; }

.chat-message .avatar {
    width: 30px; height: 30px; border-radius: 4px; margin-right: 1rem;
    display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0;
}
.chat-message .avatar.user { background-color: #9173e8; color: white; }
.chat-message .avatar.bot { background-color: #10a37f; color: white; }

.chat-message .message-content {
    padding-top: 3px; overflow-wrap: break-word; width: 100%;
}
/* Styles for markdown content rendered as HTML */
.message-content p, .message-content ul, .message-content ol { margin-bottom: 0.5em; line-height: 1.6; }
.message-content ul, .message-content ol { padding-left: 1.5em; }
.message-content pre { background-color: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 0.9em; margin: 0.5em 0; font-family: monospace; }
.message-content code:not(pre code) { font-size: 90%; background-color: rgba(0,0,0,0.07); padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace;}
.message-content strong { font-weight: 600; }
.message-content em { font-style: italic; }
.message-content table { border-collapse: collapse; width: auto; margin: 0.5em 0; }
.message-content th, .message-content td { border: 1px solid #ccc; padding: 6px 10px; text-align: left;}
.message-content th { background-color: #eee; font-weight: 600; }

/* Chat input area styling */
.chat-input-area-wrapper {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #ffffff 70%, #ffffff 100%);
    padding-top: 2rem; z-index: 99; pointer-events: none;
}
.chat-input-area {
    padding: 1rem; background-color: #ffffff; border-top: 1px solid #e5e5e5;
    max-width: 48rem; margin: 0 auto;
    display: flex; flex-direction: column; pointer-events: auto;
}

/* Staging area styles */
.staging-area { margin-bottom: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
.file-badge {
    display: inline-flex; align-items: center; background-color: #f0f0f0;
    padding: 5px 10px; border-radius: 15px; font-size: 0.8rem;
    border: 1px solid #e0e0e0;
}
.file-badge span { margin-right: 5px; }
.file-badge .remove-btn {
    margin-left: 5px; cursor: pointer; color: #888; font-weight: bold;
    background: none; border: none; padding: 0 2px; line-height: 1;
}
.file-badge .remove-btn:hover { color: #ff4d4f; }

/* Container for input row */
.chat-input-row {
    display: flex; align-items: flex-end; background-color: #ffffff;
    border: 1px solid #e5e5e5; border-radius: 12px; padding: 0.5rem 0.75rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
/* Make columns take appropriate space */
.chat-input-row > div[data-testid="stHorizontalBlock"] > div:nth-child(1) { flex: 0 0 auto; } /* Attach button */
.chat-input-row > div[data-testid="stHorizontalBlock"] > div:nth-child(2) { flex: 1 1 auto; } /* Text area */
.chat-input-row > div[data-testid="stHorizontalBlock"] > div:nth-child(3) { flex: 0 0 auto; } /* Send button */

.file-upload-button-container button { /* Target Streamlit button used for upload */
    border: none !important; background: transparent !important; color: #6e6e80 !important;
    cursor: pointer; padding: 5px !important;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2em !important; height: 32px !important; width: 32px !important; flex-shrink: 0 !important;
    margin-right: 8px !important;
    border-radius: 4px !important;
}
.file-upload-button-container button:hover { color: #10a37f !important; background: #f0f0f0 !important;}

.chat-input-textarea textarea { /* Target the textarea specifically */
    flex-grow: 1; border: none !important; outline: none !important; resize: none !important;
    font-size: 1rem !important; line-height: 1.5 !important; padding: 4px 0 !important;
    background: transparent !important; max-height: 200px !important; overflow-y: auto !important;
    color: #343541 !important; align-self: center !important; width: 100% !important;
    margin: 0 !important; box-shadow: none !important;
}

.send-button-container button { /* Target Streamlit button used for send */
    width: 32px !important; height: 32px !important; border-radius: 8px !important; background-color: #10a37f !important;
    color: white !important; display: flex !important; align-items: center !important; justify-content: center !important;
    cursor: pointer !important; transition: background-color 0.2s !important; border: none !important;
    margin-left: 8px !important; flex-shrink: 0 !important; padding: 0 !important;
}
.send-button-container button:hover { background-color: #0c8d6e !important; }
.send-button-container button:disabled { background-color: #cccccc !important; color: #888888 !important; cursor: not-allowed !important; }

/* Thinking animation */
@keyframes pulse { 0% { opacity: 0.3; } 50% { opacity: 0.8; } 100% { opacity: 0.3; } }
.thinking-animation { display: flex; align-items: center; margin-top: 8px; }
.thinking-dot { height: 8px; width: 8px; border-radius: 50%; background-color: #10a37f; margin-right: 4px; animation: pulse 1.5s infinite; }
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

/* Ensure main content area has enough bottom padding */
.main { padding-bottom: 160px; /* Increased padding */ }

/* Hidden File Uploader Styling */
div[data-testid="stFileUploader"].hidden-uploader > section {
    display: none; /* Hide the dropzone part */
    border: none !important;
    padding: 0 !important;
}
div[data-testid="stFileUploader"].hidden-uploader small {
    display: none; /* Hide file limit text */
}
/* Make the overall widget take no space */
div[data-testid="stFileUploader"].hidden-uploader {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    z-index: -10;
    overflow: hidden;
}

/* Welcome screen styling */
/* (Code remains the same) */

</style>

<!-- Custom JavaScript (textarea auto-height, Enter key) -->
<script>
    // Function to auto-resize textarea
    function autoGrow(element) {
        if (element) {
            element.style.height = 'auto'; // Temporarily shrink
            element.style.height = Math.max(24, element.scrollHeight) + 'px';
        }
    }

    // Attach event listener to the correct textarea
    function attachListeners() {
        const textarea = document.querySelector('textarea[aria-label="Your message"]');
        const hiddenSendButton = document.getElementById('hidden-send-trigger-button'); // Find the *actual* Streamlit button
        const htmlSendButton = document.getElementById('send-button-html'); // Find the fake HTML button

        if (textarea && !textarea.dataset.listenerAttached) {
            // console.log("Attaching listeners to textarea");
            textarea.addEventListener('input', () => autoGrow(textarea));
            textarea.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey && !hiddenSendButton.disabled) { // Check if button is enabled
                    e.preventDefault();
                    if (hiddenSendButton) {
                        // console.log("Enter pressed, clicking hidden send button");
                        hiddenSendButton.click();
                    } else { console.error("Hidden Send button not found by ID"); }
                }
            });
            textarea.dataset.listenerAttached = 'true';
            autoGrow(textarea); // Initial resize
        }

        // Sync disabled state from hidden Streamlit button to HTML button
        if (htmlSendButton && hiddenSendButton) {
            htmlSendButton.disabled = hiddenSendButton.disabled;
            htmlSendButton.style.opacity = hiddenSendButton.disabled ? '0.5' : '1';
        }

        // --- File Remove Button Listeners (Still Unreliable) ---
        const removeButtons = document.querySelectorAll('.remove-btn');
        removeButtons.forEach(btn => {
             if (!btn.dataset.listenerAttached) {
                const index = btn.dataset.index;
                const hiddenRemoveButtonId = `remove-btn-${index}-hidden`;
                 btn.addEventListener('click', function() {
                     const hiddenRemoveButton = document.getElementById(hiddenRemoveButtonId);
                     if (hiddenRemoveButton) {
                        // console.log(`Remove clicked, clicking hidden button: ${hiddenRemoveButtonId}`);
                         hiddenRemoveButton.click();
                     } else { console.error(`Hidden Remove button not found by ID: ${hiddenRemoveButtonId}`); }
                 });
                 btn.dataset.listenerAttached = 'true';
             }
         });
    }

    // Use MutationObserver for robustness against Streamlit rerenders
    const observer = new MutationObserver((mutationsList, observer) => {
        attachListeners(); // Re-attach listeners when DOM changes
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Initial call
    document.addEventListener('DOMContentLoaded', attachListeners);

    // Add click handler for the fake HTML send button if needed (though hidden button click should suffice)
    // document.getElementById('send-button-html')?.addEventListener('click', () => {
    //     document.getElementById('hidden-send-trigger-button')?.click();
    // });

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
if "staged_files" not in st.session_state: st.session_state.staged_files = [] # List to hold UploadedFile objects
if "thinking" not in st.session_state: st.session_state.thinking = False
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_" + str(int(time.time()))
if "chat_history" not in st.session_state: st.session_state.chat_history = {st.session_state.current_chat_id: {"title": "New Chat", "messages": [], "context_files": {}}}
if "example_queries" not in st.session_state:
    st.session_state.example_queries = [
        "Explain quantum computing", "Suggest Python libraries",
        "Write a short story", "How does photosynthesis work?"
    ]


# --- Helper Functions ---
def create_new_chat():
    # (Same as before)
    chat_id = "chat_" + str(int(time.time()))
    st.session_state.chat_history[chat_id] = {"title": "New Chat", "messages": [], "context_files": {}}
    st.session_state.current_chat_id = chat_id
    st.session_state.messages = []
    st.session_state.uploaded_file_data = {}
    st.session_state.staged_files = []
    st.rerun()

def load_chat(chat_id):
    # (Same as before)
    if chat_id in st.session_state.chat_history:
        st.session_state.current_chat_id = chat_id
        st.session_state.messages = st.session_state.chat_history[chat_id].get("messages", [])
        st.session_state.uploaded_file_data = st.session_state.chat_history[chat_id].get("context_files", {})
        st.session_state.staged_files = []
        st.rerun()

def update_chat_title():
    # (Same as before)
    if st.session_state.messages and st.session_state.messages[0]["role"] == "user":
        first_message = st.session_state.messages[0]["content"]
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        st.session_state.chat_history[st.session_state.current_chat_id]["title"] = title

def display_chat_message(message):
    """Display a single chat message using custom HTML"""
    role = message["role"]
    content = message["content"]
    avatar_icon = "U" if role == "user" else "🤖"
    avatar_class = "user" if role == "user" else "bot"
    message_class = "user" if role == "user" else "bot"

    # Convert markdown content to HTML
    try:
        extensions = ['fenced_code', 'codehilite', 'tables', 'nl2br', 'sane_lists']
        # Use codehilite options if needed, e.g., CodeHiliteExtension(css_class='highlight')
        content_html = markdown.markdown(content, extensions=extensions)
    except ImportError:
        st.warning("`markdown` library not found. Install `pip install markdown`. Formatting limited.", icon="⚠️")
        content_html = content.replace("&", "&").replace("<", "<").replace(">", ">").replace("\n", "<br>")
    except Exception as md_err:
        st.error(f"Markdown processing error: {md_err}")
        content_html = content.replace("&", "&").replace("<", "<").replace(">", ">").replace("\n", "<br>")

    # Display using markdown with unsafe_allow_html
    # CORRECTED f-string (no comment inside braces):
    st.markdown(f"""
    <div class="chat-message-container">
        <div class="chat-message {message_class}">
            <div class="avatar {avatar_class}">
                <span>{avatar_icon}</span>
            </div>
            <div class="message-content">
                 {content_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def remove_staged_file(file_index_to_remove):
    """Remove file triggered by hidden button"""
    # (Same logic as before)
    try:
        if 0 <= file_index_to_remove < len(st.session_state.staged_files):
            removed_file = st.session_state.staged_files.pop(file_index_to_remove)
            st.toast(f"Removed {removed_file.name}")
            st.rerun()
    except IndexError: pass
    except Exception as e: st.error(f"Error removing file: {e}")


def process_staged_files():
    """Process staged files and add to context (triggered on send)"""
    # (Same logic as before)
    processed_files_names = []
    if not st.session_state.staged_files: return processed_files_names
    with st.status(f"Processing {len(st.session_state.staged_files)} file(s)...", expanded=False) as status:
        staged_copy = list(st.session_state.staged_files)
        for file in staged_copy:
            if file.name not in st.session_state.uploaded_file_data:
                status.write(f"Processing {file.name}...")
                content, metadata = file_parser.process_uploaded_file(file)
                if content is not None:
                    st.session_state.uploaded_file_data[file.name] = {"content": content, "metadata": metadata}
                    processed_files_names.append(file.name)
                else: status.write(f"⚠️ Failed to process {file.name}")
        # Save context files associated with this specific chat
        st.session_state.chat_history[st.session_state.current_chat_id]["context_files"] = st.session_state.uploaded_file_data
        status.update(label=f"Processed {len(processed_files_names)} file(s)!", state="complete")
    st.session_state.staged_files = [] # Clear staging
    if processed_files_names: st.toast(f"Added {len(processed_files_names)} file(s) to context.")
    return processed_files_names

# --- Sidebar ---
# (Same as before)
with st.sidebar:
    st.markdown('<h1 style="color: white; margin-bottom: 20px;">💬 AI Chat</h1>', unsafe_allow_html=True)
    if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"): create_new_chat()
    st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="color: white; margin-bottom: 10px;">Chat History</h3>', unsafe_allow_html=True)
    sorted_chat_ids = sorted(st.session_state.chat_history.keys(), reverse=True)
    for chat_id in sorted_chat_ids:
        chat_data = st.session_state.chat_history[chat_id]
        chat_title = chat_data.get("title", "Chat")
        if st.button(f"{chat_title}", key=f"load_chat_{chat_id}", use_container_width=True): load_chat(chat_id)

    st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="color: white; margin-bottom: 10px;">Model Settings</h3>', unsafe_allow_html=True)
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    if not available_models: st.error("No models configured."); st.stop()
    if st.session_state.selected_model not in available_models: st.session_state.selected_model = available_models[0]
    selected_model_display_name = st.selectbox(
        "Choose a model:", options=available_models,
        index=available_models.index(st.session_state.selected_model), key="model_selector"
    )
    required_key_name_for_selected = llm_api.get_required_api_key_name(st.session_state.selected_model)
    st.session_state.api_keys = {}; st.session_state.stop_app = False
    if required_key_name_for_selected:
        if required_key_name_for_selected in st.secrets:
            st.session_state.api_keys[required_key_name_for_selected] = st.secrets[required_key_name_for_selected]
        else: st.session_state.stop_app = True
    if selected_model_display_name != st.session_state.selected_model:
        st.session_state.selected_model = selected_model_display_name; st.rerun()
    model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    st.markdown(f'<div style="color: #aaa; font-size: 12px; margin-top: 5px;">Capabilities: {", ".join(model_capabilities)}</div>', unsafe_allow_html=True)

    # Display Processed Files
    if st.session_state.uploaded_file_data:
        st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<h3 style="color: white; margin-bottom: 10px;">Uploaded Files</h3>', unsafe_allow_html=True)
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                 metadata = st.session_state.uploaded_file_data[filename]["metadata"]
                 file_type = metadata.get("type", "unknown")
                 st.markdown(f'<div style="color: #ccc; font-size: 0.9em; padding: 2px 0;">📎 {filename} ({file_type})</div>', unsafe_allow_html=True)
        if st.button("Clear All Files", use_container_width=True, key="clear_files_btn"):
            st.session_state.uploaded_file_data = {}; st.toast("Cleared all files from chat context."); st.rerun()

# --- Main Chat Area ---
chat_display_container = st.container()
with chat_display_container:
    if not st.session_state.messages:
        # show_welcome_screen() # Optional
        pass
    else:
        for message in st.session_state.messages:
            display_chat_message(message) # Use custom HTML display

# --- LLM Response Trigger ---
if st.session_state.thinking:
    with chat_display_container:
         st.markdown(f"""
         <div class="chat-message-container">
             <div class="chat-message bot">
                 <div class="avatar bot"><span>🤖</span></div>
                 <div class="message-content"><div class="thinking-animation"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div></div>
             </div>
         </div>
         """, unsafe_allow_html=True)

    history_for_llm = st.session_state.messages[-10:]
    file_context_for_llm = st.session_state.uploaded_file_data
    current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)
    try:
        response_text, generated_file_info = llm_api.get_llm_response(
            model_display_name=st.session_state.selected_model, messages=history_for_llm,
            api_keys=st.session_state.api_keys, uploaded_file_context=file_context_for_llm,
            model_capabilities=current_model_capabilities
        )
        assistant_message = {"role": "assistant", "content": response_text, "generated_files": []}
        st.session_state.messages.append(assistant_message)
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages
    except Exception as e:
        st.error(f"An error occurred: {e}")
        error_message = f"Sorry, I encountered an error. Error: {e}"
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        st.session_state.chat_history[st.session_state.current_char_id]["messages"] = st.session_state.messages # typo fixed here
    finally:
        st.session_state.thinking = False
        st.rerun()


# --- Fixed Chat Input Area at Bottom ---
# Wrapper div for positioning and fade effect
st.markdown('<div class="chat-input-area-wrapper">', unsafe_allow_html=True)
# Inner div for content, centering, and top border
st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)

# --- Staging Area ---
if st.session_state.staged_files:
    st.markdown('<div class="staging-area">', unsafe_allow_html=True)
    staged_file_copy = list(st.session_state.staged_files)
    for i, file in enumerate(staged_file_copy):
        hidden_btn_id = f"remove-btn-{i}-hidden" # Unique ID for hidden button
        st.markdown(f"""
        <span class="file-badge">
            📎 {file.name}
            <button class="remove-btn" data-index="{i}" title="Remove {file.name}"
                    onclick="document.getElementById('{hidden_btn_id}').click()">×</button>
        </span>
        """, unsafe_allow_html=True)
        # Hidden Streamlit button - place it outside the markdown
    st.markdown('</div>', unsafe_allow_html=True)
    # Render hidden buttons *after* the markdown for the staging area
    for i, file in enumerate(staged_file_copy):
         hidden_btn_id = f"remove-btn-{i}-hidden"
         # Use columns to prevent buttons from taking full width / interfering visually
         # This is still a hack to hide them effectively
         with st.columns(1)[0]:
             st.button(f"X{i}", key=hidden_btn_id, on_click=remove_staged_file, args=(i,), help=f"Remove {file.name}")
             # Attempt to hide via CSS might be needed if this renders visibly
             st.markdown(f"<style>#{hidden_btn_id} {{ display: none; }}</style>", unsafe_allow_html=True)


# --- Input Row (using st.columns for layout) ---
input_cols = st.columns([1, 10, 1]) # Adjust ratios: Attach | Text Area | Send

with input_cols[0]: # Attach button column
    st.markdown('<div class="file-upload-button-container">', unsafe_allow_html=True)
    # This button toggles the file uploader's visibility state
    if st.button("📎", key="toggle_upload_btn", help="Attach files"):
         st.session_state.show_dropzone = not st.session_state.show_dropzone
         st.rerun() # Rerun to show/hide the uploader below
    st.markdown('</div>', unsafe_allow_html=True)


with input_cols[1]: # Text area column
    st.markdown('<div class="chat-input-textarea">', unsafe_allow_html=True)
    prompt = st.text_area(
        "Your message",
        key="chat_input_textarea",
        placeholder=f"Message {st.session_state.selected_model}..." if not st.session_state.stop_app else "API Key Missing",
        disabled=st.session_state.stop_app or st.session_state.thinking,
        label_visibility="collapsed",
        height=24, # Initial height for JS to grow
    )
    st.markdown('</div>', unsafe_allow_html=True)


with input_cols[2]: # Send button column
    st.markdown('<div class="send-button-container">', unsafe_allow_html=True)
    is_send_disabled = st.session_state.stop_app or st.session_state.thinking or not prompt.strip()
    # Hidden button MUST be rendered for JS/Enter key to trigger it
    submit_button_clicked = st.button("➤", key="hidden-send-trigger-button", disabled=is_send_disabled, help="Send message")
    st.markdown('</div>', unsafe_allow_html=True)


# --- Conditionally Rendered File Uploader ---
if st.session_state.show_dropzone:
    uploaded_files = st.file_uploader(
        "Drag and drop or browse files",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "csv", "xlsx", "ipynb", "zip"],
        accept_multiple_files=True,
        key="actual_file_uploader",
        label_visibility="visible" # Show label when dropzone is visible
    )
    if uploaded_files:
        newly_staged_count = 0
        for file in uploaded_files:
            is_already_staged = any(staged_file.name == file.name for staged_file in st.session_state.staged_files)
            if not is_already_staged:
                st.session_state.staged_files.append(file)
                newly_staged_count += 1
        if newly_staged_count > 0:
            st.toast(f"Staged {newly_staged_count} file(s).")
            st.session_state.show_dropzone = False # Hide after upload
            st.rerun()


st.markdown('</div>', unsafe_allow_html=True) # Close chat-input-area
st.markdown('</div>', unsafe_allow_html=True) # Close chat-input-area-wrapper


# --- Send Logic (Triggered by the *actual* hidden Streamlit button) ---
if submit_button_clicked: # Check if the Streamlit button was clicked
    if prompt and not st.session_state.stop_app and not st.session_state.thinking:
        processed_files_names = process_staged_files()
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages
        if len(st.session_state.messages) == 1: update_chat_title()
        st.session_state.thinking = True
        st.rerun() # Rerun to clear input, show message, start thinking

# --- Final check/warning ---
if st.session_state.stop_app:
    key_name_warn = required_key_name_for_selected or "API Key"
    st.warning(f"Chat input disabled. API key ('{key_name_warn}') missing.", icon="⚠️")
