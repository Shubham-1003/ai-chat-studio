import streamlit as st
# Import the updated get_response function and the custom error class
from utils.llm_api import get_response, APIError # Make sure utils.llm_api points to the updated file

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
    # Define available models clearly
    AVAILABLE_MODELS = ["Gemini", "OpenAI", "Claude", "Mistral", "Groq"]
    model_name = st.selectbox("Select LLM Model", options=AVAILABLE_MODELS)

    # Add helper text for clarity
    temperature = st.slider("Temperature", 0.0, 1.0, 0.5,
                            help="Controls randomness. Lower values make the output more deterministic, higher values make it more creative.")
    max_tokens = st.slider("Max Tokens", 100, 2048, 512, # Adjust max range if needed for specific models
                           help="Maximum number of tokens (words/subwords) the model should generate.")
    # Update help text based on the check inside get_response
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
        st.markdown(msg) # Use markdown to render potential formatting in responses

# Get user input via chat input widget
user_input = st.chat_input("Ask your question...")

if user_input:
    # Add user message to history and display it
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    # Process and display assistant response
    with st.chat_message("assistant"):
        # Show spinner while waiting for response
        with st.spinner("Thinking..."):
            try:
                # Call the updated get_response function
                output = get_response(
                    prompt=user_input,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=api_key
                )
                # Display the successful response
                st.markdown(output)
                # Add assistant response to history
                st.session_state.chat_history.append(("assistant", output))

            # Catch specific API errors from llm_api.py
            except APIError as e:
                st.error(f"API Communication Error: {e}")
                # Optionally add the error indication to chat history
                # st.session_state.chat_history.append(("assistant", f"Error: {e}"))
            # Catch configuration errors like unsupported model
            except ValueError as e:
                 st.error(f"Configuration Error: {e}")
            # Catch any other unexpected errors during Streamlit execution
            except Exception as e:
                st.error(f"An unexpected application error occurred: {type(e).__name__} - {e}")
                # For debugging, you might want to log the full traceback
                import traceback
                print(f"Traceback: {traceback.format_exc()}") # Print traceback to console where streamlit runs
                # Consider showing a simplified error or logging more formally in production
                # st.error("An unexpected error occurred. Please check the logs or contact support.")
