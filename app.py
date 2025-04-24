import streamlit as st
import traceback
# Ensure this import matches your file structure
from utils.llm_api import get_response, APIError # This line should now work correctly

# --- Secrets Key Mapping ---
# Maps the model selection name to the key name expected in secrets.toml
SECRETS_KEY_MAPPING = {
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GOOGLE_API_KEY",
    "Claude": "ANTHROPIC_API_KEY",
    "Mistral": "MISTRAL_API_KEY",
    # Add Groq if you have a key for it in secrets.toml
    # "Groq": "GROQ_API_KEY",

    # --- ADD NVIDIA MAPPINGS ---
    # Use user-friendly display names on the left, exact secret key names on the right
    "NVIDIA Mistral Small": "NVIDIA_Mistral_Small_24B_Instruct",
    "NVIDIA DeepSeek Qwen": "NVIDIA_DeepSeek_R1_Distill_Qwen_32B",
    # Add more NVIDIA models here if needed
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
    load_css("css/style.css")

    # --- Main App UI ---
    st.markdown("# 🧠 LLM Chat Interface")

    with st.sidebar:
        st.header("Model Settings")

        # --- UPDATED AVAILABLE MODELS ---
        # Define all models you want to potentially offer
        ALL_POSSIBLE_MODELS = [
            "Gemini", "OpenAI", "Claude", "Mistral", "Groq", # Existing
            "NVIDIA Mistral Small", "NVIDIA DeepSeek Qwen"  # Added NVIDIA
        ]

        # Filter available models based on keys ACTUALLY PRESENT in secrets
        # This prevents showing models for which keys are missing
        models_with_keys = [
            name for name in ALL_POSSIBLE_MODELS
            if SECRETS_KEY_MAPPING.get(name) and st.secrets.get(SECRETS_KEY_MAPPING[name])
        ]
        # Add a check if Groq key exists if Groq is in ALL_POSSIBLE_MODELS but not SECRETS_KEY_MAPPING yet
        # if "Groq" in ALL_POSSIBLE_MODELS and st.secrets.get("GROQ_API_KEY"):
        #     models_with_keys.append("Groq") # Assuming GROQ_API_KEY is the secret name

        if not models_with_keys:
             st.error("No valid API keys found in Streamlit Secrets. Please add keys to `.streamlit/secrets.toml`.")
             st.stop()

        # Only show models for which keys are available
        model_name = st.selectbox("Select LLM Model", options=models_with_keys)

        temperature = st.slider("Temperature", 0.0, 1.0, 0.5,
                                help="Controls randomness.")
        max_tokens = st.slider("Max Tokens", 100, 2048, 512, # Adjust range as needed
                               help="Maximum number of tokens to generate.")

        # Removed API Key text input

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display messages
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    # Get user input
    user_input = st.chat_input("Ask your question...")

    if user_input:
        # Retrieve API Key from Secrets
        retrieved_api_key = None
        secret_key_name = SECRETS_KEY_MAPPING.get(model_name)

        if not secret_key_name:
            st.error(f"Internal Error: No secret key mapping defined for model '{model_name}'.")
            st.stop()

        try:
            retrieved_api_key = st.secrets[secret_key_name]
        except KeyError:
            st.error(f"API Key Error: Key '{secret_key_name}' not found in Streamlit Secrets (`.streamlit/secrets.toml`).")
            st.stop()

        if not retrieved_api_key:
             st.error(f"API Key Error: Key '{secret_key_name}' found in Streamlit Secrets but is empty.")
             st.stop()

        # Process Input
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    output = get_response(
                        prompt=user_input,
                        model=model_name, # Pass the display name
                        temperature=temperature,
                        max_tokens=max_tokens,
                        api_key=retrieved_api_key # Pass the key from secrets
                    )
                    st.markdown(output)
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

# --- Error Handling Blocks (remain the same) ---
except ImportError as e:
    error_message = f"Import Error: ... Details: {e}" # Simplified
    st.error(error_message); print(f"Import Error: {e}"); traceback.print_exc()
except Exception as e:
    error_message = f"A critical error occurred... Details: {e}" # Simplified
    st.error(error_message); print("--- CRITICAL STARTUP ERROR ---"); traceback.print_exc(); print("--- END ---")
