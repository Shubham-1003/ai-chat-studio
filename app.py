import streamlit as st
import traceback # Import traceback for detailed error logging
# Ensure this import matches your file structure
from utils.llm_api import get_response, APIError

# --- Start Basic Error Check ---
# Wrap the entire Streamlit app rendering in a try-except
# to catch errors happening *before* the main UI tries to draw.
try:
    st.set_page_config(page_title="LLM Chat App", layout="wide")

    # Apply a cleaner, modern design
    st.markdown(
        """
        <style>
        .main {
            background-color: #f4f4f9;
        }
        .stTextInput>div>div>input {
            background-color: white;
        }
        .stChatMessage {
            /* Adjust font size or other properties if desired */
            /* font-size: 16px; */
        }
        .stAlert p { /* Style error messages slightly */
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Using markdown for title with emoji
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

    # Initialize chat history in session state if it doesn't exist
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display existing chat messages
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    # Get user input via chat input widget
    user_input = st.chat_input("Ask your question...")

    if user_input:
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

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
                    st.markdown(output)
                    st.session_state.chat_history.append(("assistant", output))

                except APIError as e:
                    st.error(f"API Communication Error: {e}")
                except ValueError as e:
                     st.error(f"Configuration Error: {e}")
                except Exception as e:
                    # Log the full traceback for debugging in the console
                    print("--- Detailed Traceback ---")
                    traceback.print_exc()
                    print("--- End Traceback ---")
                    # Show a user-friendly error in the app
                    st.error(f"An unexpected application error occurred: {type(e).__name__}")
                    # Optionally add more detail for the user if safe/desired
                    # st.error(f"Details: {e}")


# --- Catching errors happening before/during Streamlit setup ---
except ImportError as e:
    st.error(f"Import Error: Failed to import necessary code. Please check file structure and installations.")
    st.error(f"Details: {e}")
    print(f"Import Error: {e}")
    traceback.print_exc()
except Exception as e:
    # Catch any other exception that prevents the app from starting
    st.error("A critical error occurred while starting the application.")
    st.error(f"Error Type: {type(e).__name__}")
    st.error(f"Details: {e}")
    # Log the full traceback to the console for debugging
    print("--- CRITICAL STARTUP ERROR ---")
    traceback.print_exc()
    print("--- END CRITICAL STARTUP ERROR ---")
