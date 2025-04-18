# app.py (Claude's Attempt - Completed Logic, WITH CAVEATS)

import streamlit as st
from PIL import Image
import io
import os
import time
import random
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
}

/* Reduce padding around main content area */
.main .block-container {
    padding-top: 1rem; /* Adjust as needed */
    padding-bottom: 1rem; /* Adjust as needed */
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
    background-color: #202123;
    color: #ffffff;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] .stSelectbox div[role="button"] {
    color: #ffffff;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #ffffff;
}
[data-testid="stSidebar"] hr { border-color: #444654; }
[data-testid="stSidebar"] button {
    background-color: #343541; color: #ffffff; border: 1px solid #565869;
    border-radius: 4px; transition: background-color 0.2s;
}
[data-testid="stSidebar"] button:hover { background-color: #40414f; }
[data-testid="stSidebar"] .stSelectbox [data-testid="stMarkdownContainer"] p { color: #343541; } /* Text inside selectbox dropdown */

/* Chat message styling */
/* Use divs instead of stChatMessage directly */
.chat-message-container { /* New class to wrap messages */
    padding-bottom: 10px; /* Space between messages */
}

.chat-message {
    display: flex;
    padding: 1rem; /* Smaller padding */
    margin: 0 auto; /* Center message block */
    max-width: 48rem; /* Match block-container */
}
.chat-message.user { background-color: #ffffff; }
.chat-message.bot { background-color: #f7f7f8; }

.chat-message .avatar {
    width: 30px; height: 30px; border-radius: 4px; margin-right: 1rem;
    display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0;
}
.chat-message .avatar.user { background-color: #9173e8; color: white; } /* Example purple */
.chat-message .avatar.bot { background-color: #10a37f; color: white; }

.chat-message .message-content {
    padding-top: 3px; overflow-wrap: break-word; width: 100%;
}
/* Ensure markdown content inside message-content renders correctly */
.message-content p, .message-content ul, .message-content ol, .message-content pre { margin-bottom: 0.5em; }
.message-content pre { background-color: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 0.9em; }
.message-content code:not(pre code) { font-size: 90%; background-color: rgba(0,0,0,0.05); padding: 0.2em 0.4em; border-radius: 3px; }

/* Chat input area styling */
.chat-input-area-wrapper { /* Wrapper to handle positioning */
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #ffffff 100%); /* Fade effect */
    padding-top: 2rem; /* Space for fade */
    z-index: 99;
}

.chat-input-area {
    padding: 1rem; /* Padding inside the area */
    background-color: #ffffff;
    border-top: 1px solid #e5e5e5;
    max-width: 48rem;
    margin: 0 auto; /* Center input area */
    display: flex;
    flex-direction: column; /* Allow staging area above input */
}

/* Staging area styles */
.staging-area {
    margin-bottom: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.file-badge {
    display: inline-flex; align-items: center; background-color: #f0f0f0;
    padding: 5px 10px; border-radius: 15px; font-size: 0.8rem;
    border: 1px solid #e0e0e0;
}
.file-badge span { margin-right: 5px; } /* Space before remove button */
.file-badge .remove-btn {
    margin-left: 5px; cursor: pointer; color: #888; font-weight: bold;
    background: none; border: none; padding: 0 2px; line-height: 1;
}
.file-badge .remove-btn:hover { color: #ff4d4f; }

/* Container for input row */
.chat-input-row {
    display: flex;
    align-items: flex-end; /* Align items to bottom (for attach button) */
    background-color: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 12px;
    padding: 0.5rem 0.75rem; /* Adjusted padding */
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.file-upload-button {
    border: none; background: transparent; color: #6e6e80;
    cursor: pointer; padding: 5px; /* Adjust padding */
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2em; /* Icon size */
    margin-right: 8px; /* Space between icon and textarea */
    height: 32px; /* Match button height */
    width: 32px; /* Match button width */
}
.file-upload-button:hover { color: #10a37f; }

.chat-input-textarea { /* Target the specific textarea */
    flex-grow: 1;
    border: none;
    outline: none;
    resize: none;
    font-size: 1rem; /* Match common chat font size */
    line-height: 1.5;
    padding: 4px 0; /* Minimal vertical padding */
    background: transparent;
    max-height: 200px; /* Limit growth */
    overflow-y: auto; /* Add scroll if needed */
    color: #343541; /* Match body text */
    align-self: center; /* Vertically center text */
}

.chat-submit-button {
    width: 32px; height: 32px; border-radius: 8px; background-color: #10a37f;
    color: white; display: flex; align-items: center; justify-content: center;
    cursor: pointer; transition: background-color 0.2s; border: none;
    margin-left: 8px; /* Space between textarea and button */
    flex-shrink: 0;
}
.chat-submit-button:hover { background-color: #0c8d6e; }
.chat-submit-button:disabled { background-color: #cccccc; color: #888888; cursor: not-allowed; }

/* Thinking animation */
/* ... (thinking animation CSS remains the same) ... */

/* Ensure main content area has enough bottom margin */
.main {
    padding-bottom: 150px; /* Adjust this value based on chat input area height */
}

/* Hide actual st.file_uploader widget (assuming it's triggered differently) */
/* This CSS might hide it even when you need it, be careful */
/* div[data-testid="stFileUploader"] > section { display: none; } */

/* Welcome screen styling */
/* ... (welcome screen CSS remains the same) ... */

</style>

<!-- Custom JavaScript (textarea auto-height, Enter key) -->
<!-- WARNING: JavaScript injection can be fragile -->
<script>
    // Function to auto-resize textarea
    function autoGrow(element) {
        element.style.height = 'auto'; // Temporarily shrink to get scrollHeight
        element.style.height = (element.scrollHeight) + 'px';
    }

    // Attach event listener to the correct textarea
    // Need to run this periodically or on mutation as Streamlit rerenders
    function attachListeners() {
        const textarea = document.querySelector('textarea[aria-label="Your message"]'); // Find textarea by label
        if (textarea && !textarea.dataset.listenerAttached) {
            textarea.addEventListener('input', () => autoGrow(textarea));
            textarea.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    // Find the hidden Streamlit button by its key (needs exact match)
                    const sendButton = document.querySelector('button[data-testid="baseButton-secondary"] span:contains("Send")');
                    // More robust: Use a specific key for the hidden button if possible
                    const hiddenSendButton = document.querySelector('button[data-testid="stButton"] span:contains("HiddenSendTrigger")')?.closest('button');

                    if (hiddenSendButton) {
                         hiddenSendButton.click();
                    } else {
                         console.error("Hidden Send button not found");
                         // Fallback or alternative trigger method needed if this fails
                    }
                }
            });
            textarea.dataset.listenerAttached = 'true'; // Mark as attached
            autoGrow(textarea); // Initial resize
        }

        // Attach listeners to remove buttons (less reliable with rerenders)
         const removeButtons = document.querySelectorAll('.remove-btn');
         removeButtons.forEach(btn => {
             if (!btn.dataset.listenerAttached) {
                 btn.addEventListener('click', function() {
                     // Logic to trigger corresponding hidden Streamlit remove button
                     const index = this.dataset.index; // Assuming index is set correctly
                     const hiddenRemoveButton = document.querySelector(`button[data-testid="stButton"] span:contains("RemoveFile${index}")`)?.closest('button');
                     if (hiddenRemoveButton) {
                         hiddenRemoveButton.click();
                     } else {
                         console.error(`Hidden Remove button for index ${index} not found`);
                     }
                 });
                 btn.dataset.listenerAttached = 'true';
             }
         });
    }

    // Run attachListeners initially and potentially on Streamlit updates
    document.addEventListener('DOMContentLoaded', attachListeners);
    // Might need MutationObserver for robustness, but adds complexity

    // Custom event listener for toggling dropzone (if using JS toggle)
    // document.addEventListener('toggle-dropzone', toggle_dropzone_js_function);

</script>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
# (Same as provided by Claude, assuming it's correct for the intended logic)
if "messages" not in st.session_state: st.session_state.messages = []
if "selected_model" not in st.session_state:
    available_models = list(llm_api.SUPPORTED_MODELS.keys())
    st.session_state.selected_model = available_models[0] if available_models else None
if "api_keys" not in st.session_state: st.session_state.api_keys = {}
if "uploaded_file_data" not in st.session_state: st.session_state.uploaded_file_data = {}
if "stop_app" not in st.session_state: st.session_state.stop_app = False
if "staged_files" not in st.session_state: st.session_state.staged_files = [] # List to hold UploadedFile objects
if "show_dropzone" not in st.session_state: st.session_state.show_dropzone = False # To toggle the explicit dropzone UI
if "thinking" not in st.session_state: st.session_state.thinking = False
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_" + str(int(time.time()))
if "chat_history" not in st.session_state: st.session_state.chat_history = {st.session_state.current_chat_id: {"title": "New Chat", "messages": []}}
# Add example queries if not present (or use Claude's examples)
if "example_queries" not in st.session_state:
    st.session_state.example_queries = [
        "Explain quantum computing", "Suggest Python libraries for data analysis",
        "Write a short story about a lost robot", "How does photosynthesis work?"
    ]


# --- Helper Functions (Adapted from Claude's code) ---
def create_new_chat():
    # (Same as Claude's version)
    chat_id = "chat_" + str(int(time.time()))
    st.session_state.chat_history[chat_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = chat_id
    st.session_state.messages = []
    st.session_state.uploaded_file_data = {}
    st.session_state.staged_files = []
    st.session_state.show_dropzone = False
    st.rerun()

def load_chat(chat_id):
    # (Same as Claude's version)
    if chat_id in st.session_state.chat_history:
        st.session_state.current_chat_id = chat_id
        st.session_state.messages = st.session_state.chat_history[chat_id].get("messages", []) # Use .get for safety
        st.session_state.uploaded_file_data = st.session_state.chat_history[chat_id].get("context_files", {}) # Assuming context is saved per chat
        st.session_state.staged_files = [] # Clear staging when loading
        st.session_state.show_dropzone = False
        st.rerun()

def update_chat_title():
    # (Same as Claude's version)
    if st.session_state.messages and st.session_state.messages[0]["role"] == "user":
        first_message = st.session_state.messages[0]["content"]
        title = first_message[:30] + "..." if len(first_message) > 30 else first_message
        st.session_state.chat_history[st.session_state.current_chat_id]["title"] = title

def display_chat_message(message):
    """Display a single chat message using custom HTML"""
    # (Adapted from Claude's - uses markdown HTML)
    role = message["role"]
    content = message["content"]
    avatar_icon = "U" if role == "user" else "🤖"
    avatar_class = "user" if role == "user" else "bot"
    message_class = "user" if role == "user" else "bot"

    # Basic escaping (replace with more robust library if needed)
    content_html = content.replace("&", "&").replace("<", "<").replace(">", ">")
    # You might need markdown conversion here if content includes markdown
    # import markdown
    # content_html = markdown.markdown(content, extensions=['fenced_code', 'codehilite'])

    st.markdown(f"""
    <div class="chat-message-container">
        <div class="chat-message {message_class}">
            <div class="avatar {avatar_class}">
                <span>{avatar_icon}</span>
            </div>
            <div class="message-content">
                 {content_html} {/* Display potentially processed HTML */}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def remove_staged_file(file_index_to_remove):
    """Remove file using Streamlit button callback logic"""
    # This function is now triggered by hidden Streamlit buttons
    try:
        if 0 <= file_index_to_remove < len(st.session_state.staged_files):
            removed_file = st.session_state.staged_files.pop(file_index_to_remove)
            st.toast(f"Removed {removed_file.name}")
            if not st.session_state.staged_files:
                st.session_state.show_dropzone = False
            st.rerun() # Rerun needed to update the display
    except IndexError:
        st.warning("Could not remove file, index out of range.")
    except Exception as e:
        st.error(f"Error removing file: {e}")


def process_staged_files():
    """Process staged files and add to context (triggered on send)"""
    # (Adapted from Claude's, uses standard status)
    processed_files_names = []
    if not st.session_state.staged_files:
        return processed_files_names

    with st.status(f"Processing {len(st.session_state.staged_files)} file(s)...", expanded=False) as status:
        # Iterate over a copy because we modify the original list via remove function potentially
        staged_copy = list(st.session_state.staged_files)
        for file in staged_copy:
            if file.name not in st.session_state.uploaded_file_data:
                status.write(f"Processing {file.name}...")
                content, metadata = file_parser.process_uploaded_file(file)
                if content is not None:
                    st.session_state.uploaded_file_data[file.name] = {
                        "content": content, "metadata": metadata
                    }
                    processed_files_names.append(file.name)
                else:
                    status.write(f"⚠️ Failed to process {file.name}")
        status.update(label=f"Processed {len(processed_files_names)} file(s)!", state="complete")

    # Clear staging AFTER processing all
    st.session_state.staged_files = []
    st.session_state.show_dropzone = False # Hide dropzone after processing

    if processed_files_names:
        st.toast(f"Added {len(processed_files_names)} file(s) to context.")

    return processed_files_names


# --- Sidebar (Adapted from Claude's) ---
with st.sidebar:
    st.markdown('<h1 style="color: white; margin-bottom: 20px;">💬 AI Chat</h1>', unsafe_allow_html=True)
    if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"):
        create_new_chat()
    st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="color: white; margin-bottom: 10px;">Chat History</h3>', unsafe_allow_html=True)
    # Sort chats by creation time (assuming IDs are timestamps)
    sorted_chat_ids = sorted(st.session_state.chat_history.keys(), reverse=True)
    for chat_id in sorted_chat_ids:
        chat_data = st.session_state.chat_history[chat_id]
        chat_title = chat_data.get("title", "Chat")
        # Use columns for title and maybe a delete button later
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            if st.button(f"{chat_title}", key=f"load_chat_{chat_id}", use_container_width=True, help=f"Load chat: {chat_title}"):
                load_chat(chat_id)
        # Add delete button functionality later if needed
        # with col2:
        #     if st.button("🗑️", key=f"delete_chat_{chat_id}", help="Delete chat"):
        #         # Add delete logic here
        #         pass

    st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="color: white; margin-bottom: 10px;">Model Settings</h3>', unsafe_allow_html=True)
    # (Model selection logic - same as Claude's, seems okay)
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

    # Display Processed Files (using helper for consistency)
    if st.session_state.uploaded_file_data:
        st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<h3 style="color: white; margin-bottom: 10px;">Uploaded Files</h3>', unsafe_allow_html=True)
        sorted_filenames = sorted(st.session_state.uploaded_file_data.keys())
        for filename in sorted_filenames:
            if filename in st.session_state.uploaded_file_data:
                 metadata = st.session_state.uploaded_file_data[filename]["metadata"]
                 # Display minimal info in sidebar, full card was too much
                 file_type = metadata.get("type", "unknown")
                 st.markdown(f'<div style="color: #ccc; font-size: 0.9em; padding: 2px 0;">📎 {filename} ({file_type})</div>', unsafe_allow_html=True)
        if st.button("Clear All Files", use_container_width=True, key="clear_files_btn"):
            st.session_state.uploaded_file_data = {}; st.toast("Cleared all files from chat context."); st.rerun()


# --- Main Chat Area ---
# This container holds the messages. CSS adds padding at the bottom.
chat_display_container = st.container()
with chat_display_container:
    if not st.session_state.messages:
        # show_welcome_screen() # Optional: Show welcome/examples
        st.caption("Chat messages will appear here.")
    else:
        for message in st.session_state.messages:
            display_chat_message(message) # Use custom HTML display

# --- Thinking Indicator Logic ---
# This needs to be placed *after* the main message display loop
if st.session_state.thinking:
    # Append a temporary thinking message structure if needed or just show animation
    # This part feels redundant if the LLM call happens below
    # Let's assume the main loop handles the actual response append
    # We just need to display the animation *while* thinking = True
    # This might require placing the thinking check *before* the LLM call is triggered
    # It's tricky with Streamlit's rerun. Let's try triggering LLM call on thinking state.
    pass # Thinking animation is handled visually by CSS, logic below triggers call

# --- LLM Response Generation Triggered by Thinking State ---
if st.session_state.thinking:
    # Retrieve necessary context
    history_for_llm = st.session_state.messages[-10:] # Get last messages for context
    file_context_for_llm = st.session_state.uploaded_file_data
    current_model_capabilities = llm_api.get_model_capabilities(st.session_state.selected_model)

    try:
        # Simulate delay (optional)
        # time.sleep(random.uniform(1.0, 2.0))

        # Actual LLM Call
        response_text, generated_file_info = llm_api.get_llm_response(
            model_display_name=st.session_state.selected_model,
            messages=history_for_llm,
            api_keys=st.session_state.api_keys,
            uploaded_file_context=file_context_for_llm,
            model_capabilities=current_model_capabilities
        )

        # Create assistant message
        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "generated_files": [] # Add logic for generated files if needed
        }
        # Append response
        st.session_state.messages.append(assistant_message)
        # Update persistent history
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages

    except Exception as e:
        st.error(f"An error occurred: {e}")
        error_message = f"Sorry, I encountered an error trying to get a response. Error: {e}"
        # Append error as assistant message
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages

    finally:
        # Always turn off thinking state and rerun
        st.session_state.thinking = False
        st.rerun() # Rerun to display the new assistant message


# --- Chat Input Area (using custom HTML/CSS) ---
st.markdown('<div class="chat-input-area-wrapper">', unsafe_allow_html=True)
st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)

# --- Staging Area (Files to be uploaded with next message) ---
if st.session_state.staged_files:
    st.markdown('<div class="staging-area">', unsafe_allow_html=True)
    for i, file in enumerate(st.session_state.staged_files):
        # Display file badge with a unique key for the hidden remove button
        st.markdown(f"""
        <span class="file-badge">
            📎 {file.name}
            <button class="remove-btn" data-index="{i}" title="Remove {file.name}"
                    onclick="document.getElementById('remove-btn-{i}').click()">×</button>
        </span>
        """, unsafe_allow_html=True)
        # Corresponding hidden Streamlit button to trigger the Python callback
        st.button(f"RemoveFile{i}", key=f"remove_btn_{i}", on_click=remove_staged_file, args=(i,), help=f"Internal remove trigger for index {i}")
        # ^^ NOTE: The 'visible=False' argument doesn't exist for st.button. Hiding relies on CSS/JS hacks or complex container tricks.
        # This hidden button approach is very likely to cause issues or not work reliably.
    st.markdown('</div>', unsafe_allow_html=True)


# --- Input Row ---
st.markdown('<div class="chat-input-row">', unsafe_allow_html=True)

# Attachment Button (triggers file uploader indirectly)
# This button itself doesn't upload, it should ideally trigger the hidden st.file_uploader
# Option 1: Use a visible st.button to toggle state? (Simpler)
# Option 2: Use markdown button + JS to click hidden uploader (Complex/Fragile)

# Using st.button for simplicity to toggle dropzone/uploader visibility state
if st.button("📎", key="toggle_upload_btn", help="Attach files"):
    st.session_state.show_dropzone = not st.session_state.show_dropzone
    # No rerun here, let the uploader appear/disappear below

# Text Area Input
prompt = st.text_area(
    "Your message", # Needs aria-label for JS selector
    key="chat_input_textarea", # Use a distinct key if needed
    placeholder=f"Message {st.session_state.selected_model}..." if not st.session_state.stop_app else "API Key Missing",
    disabled=st.session_state.stop_app or st.session_state.thinking,
    label_visibility="collapsed",
    height=24, # Initial height, JS tries to auto-grow
    # on_change=lambda: auto_grow_js() # Can't directly call JS easily
)

# Submit Button (using custom HTML + hidden button trigger)
# Check if prompt is empty or only whitespace
is_send_disabled = st.session_state.stop_app or st.session_state.thinking or not prompt.strip()
st.markdown(f"""
    <button id="send-button-html" class="chat-submit-button"
            title="Send message"
            {'disabled' if is_send_disabled else ''}
            onclick="document.getElementById('hidden-send-trigger').click()">
        ➤
    </button>
    """, unsafe_allow_html=True)

# Hidden button to actually trigger Streamlit logic when HTML button is clicked via JS
# This button click will be simulated by the Enter key JS or the HTML button onclick JS
if st.button("HiddenSendTrigger", key="hidden-send-trigger", disabled=is_send_disabled):
    if prompt and not st.session_state.stop_app and not st.session_state.thinking:
        # Process staged files *now*
        processed_files_names = process_staged_files() # Adds files to context

        # Append user message to state
        user_message = {"role": "user", "content": prompt}
        # Optionally link processed files to this specific message if needed
        # if processed_files_names: user_message["processed_files"] = processed_files_names
        st.session_state.messages.append(user_message)

        # Update chat history log
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.messages

        # Update title if first message
        if len(st.session_state.messages) == 1:
            update_chat_title()

        # Set thinking flag to trigger LLM call on next rerun
        st.session_state.thinking = True

        # Clear the text area (Streamlit handles this on button click + rerun)
        # Rerun to display user message and start thinking process
        st.rerun()


st.markdown('</div>', unsafe_allow_html=True) # Close chat-input-row
st.markdown('</div>', unsafe_allow_html=True) # Close chat-input-area

# --- Hidden File Uploader ---
# This is triggered by the attach button/logic
if st.session_state.show_dropzone: # Only render if toggled
    st.markdown("---") # Separator above dropzone
    st.caption("Attach files below:")
    uploaded_files = st.file_uploader(
        "Drag and drop or browse",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "csv", "xlsx", "ipynb", "zip"],
        accept_multiple_files=True,
        key="hidden_file_uploader", # Unique key
        label_visibility="collapsed"
    )
    if uploaded_files:
        newly_staged_count = 0
        for file in uploaded_files:
             # Check if file with same name is already staged
             is_already_staged = any(staged_file.name == file.name for staged_file in st.session_state.staged_files)
             if not is_already_staged:
                st.session_state.staged_files.append(file)
                newly_staged_count += 1
        if newly_staged_count > 0:
            st.toast(f"Staged {newly_staged_count} file(s).")
            # Maybe hide dropzone after successful upload?
            # st.session_state.show_dropzone = False
            st.rerun() # Rerun to show staged files and clear uploader state
    st.markdown("---") # Separator below dropzone

st.markdown('</div>', unsafe_allow_html=True) # Close chat-input-area-wrapper

# --- Final check/warning if app is stopped ---
if st.session_state.stop_app:
    st.warning(f"Chat input disabled. API key ('{required_key_name_for_selected}') missing.", icon="⚠️")
