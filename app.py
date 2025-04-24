import streamlit as st
import traceback
# Ensure this import matches your file structure
# The incorrect comment has been removed from the end of this line:
from utils.llm_api import get_response, APIError

# --- Secrets Key Mapping ---
# Maps the model selection name to the key name expected in secrets.toml
SECRETS_KEY_MAPPING = {
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GOOGLE_API_KEY", # Matches your secrets.toml
    "Claude": "ANTHROPIC_API_KEY",
    "Mistral": "MISTRAL_API_KEY",
    # "Groq": "GROQ_API_KEY" # Uncomment if you add Groq key
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
    load_css("css/style.css")
    st.markdown("# 🧠 LLM Chat Interface")

    with st.sidebar:
        st.header("Model Settings")
        ALL_POSSIBLE_MODELS = [
            "Gemini", "OpenAI", "Claude", "Mistral", "Groq",
            "NVIDIA Mistral Small", "NVIDIA DeepSeek Qwen"
        ]
        # Filter models based on keys present in secrets
        models_with_keys = [
            name for name in ALL_POSSIBLE_MODELS
            if SECRETS_KEY_MAPPING.get(name) and st.secrets.get(SECRETS_KEY_MAPPING.get(name,"INVALID_SECRET_KEY")) # Added default to prevent error if mapping missing
        ]
        # Add specific check for Groq if needed
        # if "Groq" in ALL_POSSIBLE_MODELS and st.secrets.get("GROQ_API_KEY"):
        #     if "Groq" not in models_with_keys: models_with_keys.append("Groq")

        if not models_with_keys:
             st.error("No valid API keys found in Streamlit Secrets for configured models.")
             st.stop()

        model_name = st.selectbox("Select LLM Model", options=models_with_keys)
        temperature = st.slider("Temperature", 0.0, 1.0, 0.5, help="Controls randomness.")
        max_tokens = st.slider("Max Tokens", 100, 2048, 512, help="Maximum number of tokens.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    user_input = st.chat_input("Ask your question...")

    if user_input:
        retrieved_api_key = None
        secret_key_name = SECRETS_KEY_MAPPING.get(model_name)

        if not secret_key_name:
            st.error(f"Internal Error: No secret key mapping for '{model_name}'.")
            st.stop()
        try:
            retrieved_api_key = st.secrets[secret_key_name]
        except KeyError:
            st.error(f"API Key Error: Key '{secret_key_name}' not found in Secrets.")
            st.stop()
        if not retrieved_api_key:
             st.error(f"API Key Error: Key '{secret_key_name}' is empty in Secrets.")
             st.stop()

        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    output = get_response(
                        prompt=user_input, model=model_name, temperature=temperature,
                        max_tokens=max_tokens, api_key=retrieved_api_key
                    )
                    st.markdown(output)
                    st.session_state.chat_history.append(("assistant", output))
                except APIError as e: st.error(f"API Communication Error: {e}")
                except ValueError as e: st.error(f"Configuration Error: {e}")
                except Exception as e:
                    print("--- Detailed Traceback ---"); traceback.print_exc(); print("--- End ---")
                    st.error(f"Unexpected application error: {type(e).__name__}")

except ImportError as e:
    error_message = f"Import Error: ... Details: {e}"; st.error(error_message); print(f"Import Error: {e}"); traceback.print_exc()
except Exception as e:
    error_message = f"A critical error occurred... Details: {e}"; st.error(error_message); print("--- CRITICAL STARTUP ERROR ---"); traceback.print_exc(); print("--- END ---")
