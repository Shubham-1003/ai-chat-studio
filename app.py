import streamlit as st
# Import the updated get_response function and the custom error class
from utils.llm_api import get_response, APIError

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
# st.title("🧠 LLM Chat Interface") # Alternative way

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
    api_key = st.text_input("API Key (required)", type="password",
                            help=f"Enter your API key for the selected '{model_name}' model.")

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
                # Optionally add the error indication to chat history (user might want to know it failed)
                # st.session_state.chat_history.append(("assistant", f"Error: {e}"))
            # Catch errors like missing API key *before* calling the API (though get_response handles it now)
            except ValueError as e:
                 st.error(f"Configuration Error: {e}")
            # Catch any other unexpected errors
            except Exception as e:
                st.error(f"An unexpected application error occurred: {e}")
                # Log the full traceback for debugging if needed
                # import traceback
                # st.error(f"Traceback: {traceback.format_exc()}")
