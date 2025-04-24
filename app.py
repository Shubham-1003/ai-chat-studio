import streamlit as st
import traceback
# This import depends on utils/__init__.py being correct (empty)
from utils.llm_api import get_response, APIError

# --- Secrets Key Mapping ---
# Maps the user-facing model name to the key name in secrets.toml
SECRETS_KEY_MAPPING = {
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GOOGLE_API_KEY",
    "Claude": "ANTHROPIC_API_KEY",
    "Mistral": "MISTRAL_API_KEY",
    "Groq": "GROQ_API_KEY", # Assuming you add GROQ_API_KEY to secrets if using Groq
    "NVIDIA Mistral Small": "NVIDIA_Mistral_Small_24B_Instruct",
    "NVIDIA DeepSeek Qwen": "NVIDIA_DeepSeek_R1_Distill_Qwen_32B",
}

# --- Function to load local CSS ---
def load_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {file_path}. Ensure 'css/style.css' exists.")
    except Exception as e:
        st.error(f"Error loading CSS: {e}")

# --- Main App Logic Wrapped in Try/Except ---
try:
    st.set_page_config(page_title="LLM Chat App", layout="wide")
    load_css("css/style.css") # Load CSS
    st.markdown("# 🧠 LLM Chat Interface") # Title

    # --- Sidebar Configuration ---
    with st.sidebar:
        st.header("Model Settings")

        # Define all models potentially available
        ALL_POSSIBLE_MODELS = list(SECRETS_KEY_MAPPING.keys()) # Get models from our mapping

        # Filter list to only models that have a non-empty key in secrets.toml
        models_with_keys = [
            name for name in ALL_POSSIBLE_MODELS
            if st.secrets.get(SECRETS_KEY_MAPPING.get(name, "")) # Check if key exists and is not empty
        ]

        if not models_with_keys:
             st.error("No valid API keys found in `.streamlit/secrets.toml` for configured models.")
             st.warning("Please add your API keys to the secrets file.")
             st.stop() # Halt execution if no models can be used

        # Model Selection Dropdown
        model_name = st.selectbox(
            "Select LLM Model",
            options=models_with_keys,
            help="Choose the language model to interact with."
        )

        # Temperature Slider
        temperature = st.slider(
            "Temperature", 0.0, 1.0, 0.5,
            help="Controls randomness: 0.0 = deterministic, 1.0 = creative."
        )

        # Max Tokens Slider
        max_tokens = st.slider(
             "Max Tokens", 100, 4096, 512, # Adjusted max range slightly
             help="Maximum length of the model's response."
        )

    # --- Chat History Initialization ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # --- Display Chat History ---
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg) # Use markdown to render formatting

    # --- User Input Handling ---
    user_input = st.chat_input("Ask your question...")

    if user_input:
        # Retrieve API Key safely
        retrieved_api_key = None
        secret_key_name = SECRETS_KEY_MAPPING.get(model_name) # Get secret name like 'GOOGLE_API_KEY'

        if not secret_key_name:
            # This case should ideally not be reached due to selectbox filtering
            st.error(f"Internal configuration error: No secret key name mapped for model '{model_name}'.")
            st.stop()
        try:
            retrieved_api_key = st.secrets[secret_key_name]
            if not retrieved_api_key: # Check if the retrieved key is actually empty
                 raise ValueError(f"API key '{secret_key_name}' is empty in secrets.")
        except (KeyError, ValueError) as e: # Catch missing key or empty key
            st.error(f"API Key Error: Could not load key '{secret_key_name}' from `.streamlit/secrets.toml`. Reason: {e}")
            st.stop() # Stop execution if key is invalid

        # Add user message to UI and history
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Call the backend function
                    output = get_response(
                        prompt=user_input,
                        model=model_name, # Pass the selected model name
                        temperature=temperature,
                        max_tokens=max_tokens,
                        api_key=retrieved_api_key # Pass the validated key
                    )
                    # Add assistant response to UI and history
                    st.markdown(output)
                    st.session_state.chat_history.append(("assistant", output))

                # Handle errors from the API call
                except APIError as e:
                    st.error(f"API Communication Error: {e}")
                except ValueError as e:
                     st.error(f"Configuration Error: {e}")
                except Exception as e:
                    # Log detailed error to console, show generic message in UI
                    print(f"--- Unexpected Error for model {model_name} ---")
                    traceback.print_exc()
                    print("--- End Traceback ---")
                    st.error(f"An unexpected application error occurred: {type(e).__name__}")

# --- Catch Errors During App Startup ---
except ImportError as e:
    # This usually means a dependency is missing or a file path is wrong
    error_message = f"Import Error: Could not import necessary code. Check installations (`requirements.txt`) and file structure. Details: {e}"
    st.error(error_message)
    print(f"Import Error: {e}")
    traceback.print_exc() # Log for debugging
except Exception as e:
    # Catch any other error preventing the app from loading
    error_message = f"Critical startup error: {type(e).__name__} - {e}"
    st.error(error_message)
    print("--- CRITICAL STARTUP ERROR ---")
    traceback.print_exc()
    print("--- END CRITICAL STARTUP ERROR ---")
