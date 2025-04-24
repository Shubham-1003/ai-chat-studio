import streamlit as st
import traceback
# Ensure this import matches your file structure
from utils.llm_api import get_response, APIError

# Function to load local CSS file
def load_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found at {file_path}. Please ensure 'css/style.css' exists.")
    except Exception as e:
        st.error(f"Error loading CSS: {e}")

# --- Start Basic Error Check ---
try:
    st.set_page_config(page_title="LLM Chat App", layout="wide")

    # --- Load the external CSS file ---
    load_css("css/style.css") # Assuming style.css is inside a 'css' folder

    # --- Main App UI ---
    # Using markdown for title (can be styled via CSS if needed)
    # st.markdown("<h1 class='chat-header'>🧠 LLM Chat Interface</h1>", unsafe_allow_html=True)
    # Or simpler:
    st.markdown("# 🧠 LLM Chat Interface")


    with st.sidebar:
        st.header("Model Settings")
        AVAILABLE_MODELS = ["Gemini", "OpenAI", "Claude", "Mistral", "Groq"]
        model_name = st.selectbox("Select LLM Model", options=AVAILABLE_MODELS)

        temperature = st.slider("Temperature", 0.0, 1.0, 0.5,
                                help="Controls randomness. Lower values make the output more deterministic, higher values make it more creative.")
        max_tokens = st.slider("Max Tokens", 100, 2048, 512,
                               help="Maximum number of tokens (words/subwords) the model should generate.")

        api_key_help = "Enter your API key."
        if model_name in ["OpenAI", "Gemini", "Claude", "Mistral", "Groq"]:
            api_key_help = f"Enter your API key for the selected '{model_name}' model (Required)."
        api_key = st.text_input("API Key", type="password", help=api_key_help)


    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # --- Chat message display area ---
    # Use st.container() to potentially apply custom class if needed by CSS
    # chat_container = st.container() # Use if your CSS targets '.stContainer' or similar
    # with chat_container: # This doesn't directly map to the example CSS's structure well

    # Display existing messages (Streamlit handles the container)
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg) # Markdown is often preferred for rendering code/lists


    # --- Chat input area ---
    user_input = st.chat_input("Ask your question...")

    if user_input:
        # Append and display user message
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    output = get_response(
                        prompt=user_input,
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        api_key=api_key
                    )
                    st.markdown(output) # Display response
                    st.session_state.chat_history.append(("assistant", output))

                except APIError as e:
                    st.error(f"API Communication Error: {e}")
                except ValueError as e:
                     st.error(f"Configuration Error: {e}")
                except Exception as e:
                    print("--- Detailed Traceback ---")
                    traceback.print_exc()
                    print("--- End Traceback ---")
                    st.error(f"An unexpected application error occurred: {type(e).__name__}")


# --- Catching errors happening before/during Streamlit setup ---
except ImportError as e:
    # These errors will likely only show in the terminal if they happen very early
    error_message = f"Import Error: Failed to import necessary code. Please check file structure and installations. Is 'requests' installed? Details: {e}"
    st.error(error_message)
    print(f"Import Error: {e}")
    traceback.print_exc()
except Exception as e:
    # Catch any other exception that prevents the app from starting
    error_message = f"A critical error occurred while starting the application. Error Type: {type(e).__name__}. Details: {e}"
    st.error(error_message)
    print("--- CRITICAL STARTUP ERROR ---")
    traceback.print_exc()
    print("--- END CRITICAL STARTUP ERROR ---")
