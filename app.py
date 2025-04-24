import streamlit as st
import traceback
# This import should now succeed because utils/__init__.py is fixed
from utils.llm_api import get_response, APIError

# --- Secrets Key Mapping ---
# Maps the model selection name to the key name expected in secrets.toml
SECRETS_KEY_MAPPING = {
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GOOGLE_API_KEY",
    "Claude": "ANTHROPIC_API_KEY",
    "Mistral": "MISTRAL_API_KEY",
    # "Groq": "GROQ_API_KEY" # Uncomment and add to secrets.toml if you use Groq
    "NVIDIA Mistral Small": "NVIDIA_Mistral_Small_24B_Instruct",
    "NVIDIA DeepSeek Qwen": "NVIDIA_DeepSeek_R1_Distill_Qwen_32B",
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
    load_css("css/style.css") # Load CSS file
    st.markdown("# 🧠 LLM Chat Interface") # App title

    with st.sidebar:
        st.header("Model Settings")
        # Define all models you might want to offer
        ALL_POSSIBLE_MODELS = [
            "Gemini", "OpenAI", "Claude", "Mistral", "Groq",
            "NVIDIA Mistral Small", "NVIDIA DeepSeek Qwen"
        ]
        # Filter models to only show those whose keys exist in secrets
        models_with_keys = [
            name for name in ALL_POSSIBLE_MODELS
            if SECRETS_KEY_MAPPING.get(name) # Check if mapped
               and st.secrets.get(SECRETS_KEY_MAPPING.get(name)) # Check if secret exists and is not empty
        ]
        # Add specific check for Groq if it wasn't in the mapping dict but might be in secrets
        if "Groq" in ALL_POSSIBLE_MODELS and "Groq" not in models_with_keys and st.secrets.get("GROQ_API_KEY"):
             models_with_keys.append("Groq")
             if "Groq" not in SECRETS_KEY_MAPPING: # Add mapping if missing
                 SECRETS_KEY_MAPPING["Groq"] = "GROQ_API_KEY"

        if not models_with_keys:
             st.error("No valid API keys found in Streamlit Secrets for configured models.")
             st.stop() # Stop if no models can be used

        # Let user select from models with available keys
        model_name = st.selectbox("Select LLM Model", options=models_with_keys)

        # Model parameters
        temperature = st.slider("Temperature", 0.0, 1.0, 0.5, help="Controls randomness (0.0=deterministic, 1.0=creative).")
        max_tokens = st.slider("Max Tokens", 100, 2048, 512, help="Maximum length of the response.") # Adjust range if needed

    # Initialize chat history if it doesn't exist
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display past chat messages
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    # Get user input
    user_input = st.chat_input("Ask your question...")

    if user_input:
        # Retrieve the correct API Key from secrets based on selection
        retrieved_api_key = None
        secret_key_name = SECRETS_KEY_MAPPING.get(model_name)

        if not secret_key_name:
            st.error(f"Internal Error: No secret key mapping defined for model '{model_name}'.")
            st.stop() # Should not happen if selectbox is populated correctly
        try:
            retrieved_api_key = st.secrets[secret_key_name]
            if not retrieved_api_key: # Check if key is empty string
                 raise ValueError("API key is empty.")
        except (KeyError, ValueError) as e:
            st.error(f"API Key Error: Key '{secret_key_name}' not found or empty in Streamlit Secrets (`.streamlit/secrets.toml`).")
            st.stop() # Stop if key is missing or empty

        # Add user message to history and display it
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get response from LLM
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Call the API function with the retrieved key
                    output = get_response(
                        prompt=user_input,
                        model=model_name, # Pass the display name (llm_api handles logic)
                        temperature=temperature,
                        max_tokens=max_tokens,
                        api_key=retrieved_api_key # Pass the actual key
                    )
                    st.markdown(output) # Display assistant's response
                    st.session_state.chat_history.append(("assistant", output)) # Add to history

                # Handle specific API errors
                except APIError as e:
                    st.error(f"API Communication Error: {e}")
                # Handle configuration errors (like unsupported model name mismatch)
                except ValueError as e:
                     st.error(f"Configuration Error: {e}")
                # Handle any other unexpected errors
                except Exception as e:
                    print("--- Detailed Traceback ---")
                    traceback.print_exc() # Log full error to console
                    print("--- End Traceback ---")
                    st.error(f"An unexpected application error occurred: {type(e).__name__}") # Show generic error in UI

# Catch errors happening during app startup (like imports)
except ImportError as e:
    error_message = f"Import Error: Failed to import code. Check file structure & installations (esp. 'requests'). Details: {e}"
    st.error(error_message)
    print(f"Import Error: {e}")
    traceback.print_exc()
except Exception as e:
    error_message = f"A critical error occurred during startup. Error: {type(e).__name__} - {e}"
    st.error(error_message)
    print("--- CRITICAL STARTUP ERROR ---")
    traceback.print_exc()
    print("--- END CRITICAL STARTUP ERROR ---")
