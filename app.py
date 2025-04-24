import streamlit as st
import traceback
# Ensure this import matches your file structure
from utils.llm_api import get_response, APIError # This line should now work correctly

# --- Secrets Key Mapping ---
# Maps the model selection name to the key name expected in secrets.toml
SECRETS_KEY_MAPPING = {
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GOOGLE_API_KEY", # Matches your secrets.toml
    "Claude": "ANTHROPIC_API_KEY",
    "Mistral": "MISTRAL_API_KEY",
    # Add Groq if you have a key for it in secrets.toml, e.g.:
    # "Groq": "GROQ_API_KEY"
    # Note: The NVIDIA keys in your example secrets aren't used by the current llm_api.py
}

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
    st.markdown("# 🧠 LLM Chat Interface")


    with st.sidebar:
        st.header("Model Settings")
        AVAILABLE_MODELS = ["Gemini", "OpenAI", "Claude", "Mistral", "Groq"] # Add/remove based on available keys/code
        # Filter available models based on whether their key is in secrets (optional but good practice)
        models_with_keys = [name for name, key in SECRETS_KEY_MAPPING.items() if st.secrets.get(key)]
        if not models_with_keys:
             st.error("No API keys found in Streamlit Secrets. Please add keys to `.streamlit/secrets.toml`.")
             st.stop() # Stop execution if no keys are available

        # Only show models for which keys are available
        model_name = st.selectbox("Select LLM Model", options=models_with_keys)

        temperature = st.slider("Temperature", 0.0, 1.0, 0.5,
                                help="Controls randomness. Lower values make the output more deterministic, higher values make it more creative.")
        max_tokens = st.slider("Max Tokens", 100, 2048, 512,
                               help="Maximum number of tokens (words/subwords) the model should generate.")

        # --- REMOVED API Key text input ---
        # api_key = st.text_input("API Key", type="password", help=api_key_help) # No longer needed if using secrets

        # Optional: Display which key is being used (useful for debugging)
        # key_to_display = SECRETS_KEY_MAPPING.get(model_name, "N/A")
        # st.caption(f"Using key: secrets.{key_to_display}")


    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # --- Chat message display area ---
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)


    # --- Chat input area ---
    user_input = st.chat_input("Ask your question...")

    if user_input:
        # --- Retrieve API Key from Secrets ---
        retrieved_api_key = None
        secret_key_name = SECRETS_KEY_MAPPING.get(model_name)

        if not secret_key_name:
            st.error(f"Internal Error: No secret key mapping defined for model '{model_name}'.")
            st.stop()

        try:
            retrieved_api_key = st.secrets[secret_key_name]
        except KeyError:
            st.error(f"API Key Error: Key '{secret_key_name}' not found in Streamlit Secrets (`.streamlit/secrets.toml`).")
            st.stop() # Stop if key is missing

        if not retrieved_api_key:
             st.error(f"API Key Error: Key '{secret_key_name}' found in Streamlit Secrets but is empty.")
             st.stop() # Stop if key is empty

        # --- Process Input ---
        # Append and display user message
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Call get_response with the key from secrets
                    output = get_response(
                        prompt=user_input,
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        api_key=retrieved_api_key # Pass the key retrieved from secrets
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
    error_message = f"Import Error: Failed to import necessary code. Please check file structure and installations. Is 'requests' installed? Details: {e}"
    st.error(error_message)
    print(f"Import Error: {e}")
    traceback.print_exc()
except Exception as e:
    error_message = f"A critical error occurred while starting the application. Error Type: {type(e).__name__}. Details: {e}"
    st.error(error_message)
    print("--- CRITICAL STARTUP ERROR ---")
    traceback.print_exc()
    print("--- END CRITICAL STARTUP ERROR ---")
