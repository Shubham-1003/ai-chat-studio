# utils/llm_api.py
import streamlit as st
import requests # For API calls
import json
from PIL import Image
import base64
import io
import os # Potentially needed for other API client libraries

# --- Model Definitions ---

# Define user-facing names and their corresponding internal IDs/API identifiers
SUPPORTED_MODELS = {
    # OpenAI
    "GPT-4o": "gpt-4o",
    "GPT-4 Turbo": "gpt-4-turbo",
    "GPT-3.5 Turbo": "gpt-3.5-turbo",
    # Google
    "Gemini 1.5 Pro": "gemini-1.5-pro-latest",
    "Gemini 1.0 Pro": "gemini-1.0-pro",
    # Anthropic
    "Claude 3 Opus": "claude-3-opus-20240229",
    "Claude 3 Sonnet": "claude-3-sonnet-20240229",
    "Claude 3 Haiku": "claude-3-haiku-20240307",
    # Mistral AI (Direct)
    "Mistral Large": "mistral-large-latest",
    "Mistral Small": "mistral-small-latest", # Assuming you might add direct Mistral access later
    # NVIDIA NIM Models <<<--- ADDED
    "NVIDIA DeepSeek-R1 Distill Qwen 32B": "deepseek-ai/deepseek-r1-distill-qwen-32b",
    "NVIDIA Mistral Small 24B Instruct": "mistralai/mistral-small-24b-instruct",
    # Add other models here
}

# Map internal model IDs to their provider for API key lookup and logic branching
MODEL_PROVIDER_MAP = {
    "gpt-4o": "OpenAI",
    "gpt-4-turbo": "OpenAI",
    "gpt-3.5-turbo": "OpenAI",
    "gemini-1.5-pro-latest": "Google",
    "gemini-1.0-pro": "Google",
    "claude-3-opus-20240229": "Anthropic",
    "claude-3-sonnet-20240229": "Anthropic",
    "claude-3-haiku-20240307": "Anthropic",
    "mistral-large-latest": "Mistral",
    "mistral-small-latest": "Mistral",
    # NVIDIA Mapping <<<--- ADDED
    "deepseek-ai/deepseek-r1-distill-qwen-32b": "NVIDIA",
    "mistralai/mistral-small-24b-instruct": "NVIDIA",
}

# Map provider names to the required API key names in st.secrets
# IMPORTANT: Ensure this matches your secrets.toml file!
PROVIDER_API_KEY_NAMES = {
    "OpenAI": "OPENAI_API_KEY",
    "Google": "GOOGLE_API_KEY",
    "Anthropic": "ANTHROPIC_API_KEY",
    "Mistral": "MISTRAL_API_KEY",
    # NVIDIA Key Mapping <<<--- Changed to recommended name
    # If you kept the name 'DEEPSEEK_API' in secrets.toml, change "NVIDIA_API_KEY" back to "DEEPSEEK_API" below
    "NVIDIA": "NVIDIA_API_KEY",
}

# Define model capabilities (extend as needed)
MODEL_CAPABILITIES = {
    "gpt-4o": ["chat", "vision", "tool_use"],
    "gpt-4-turbo": ["chat", "vision", "tool_use"],
    "gpt-3.5-turbo": ["chat", "tool_use"],
    "gemini-1.5-pro-latest": ["chat", "vision"],
    "gemini-1.0-pro": ["chat"],
    "claude-3-opus-20240229": ["chat", "vision"],
    "claude-3-sonnet-20240229": ["chat", "vision"],
    "claude-3-haiku-20240307": ["chat", "vision"],
    "mistral-large-latest": ["chat"],
    "mistral-small-latest": ["chat"],
    # NVIDIA Capabilities <<<--- ADDED (Assuming text-based chat for now)
    # Check NVIDIA documentation if these specific models support vision via NIM API later
    "deepseek-ai/deepseek-r1-distill-qwen-32b": ["chat"],
    "mistralai/mistral-small-24b-instruct": ["chat"],
}

# --- Helper Functions ---

def get_model_capabilities(model_display_name):
    """Gets the capabilities list for a given model display name."""
    internal_id = SUPPORTED_MODELS.get(model_display_name)
    if internal_id:
        return MODEL_CAPABILITIES.get(internal_id, ["chat"]) # Default to chat
    return ["chat"]

def get_required_api_key_name(model_display_name):
    """Gets the required secret key name based on the model's provider."""
    internal_id = SUPPORTED_MODELS.get(model_display_name)
    if not internal_id:
        return None
    provider = MODEL_PROVIDER_MAP.get(internal_id)
    if not provider:
        return None
    return PROVIDER_API_KEY_NAMES.get(provider)

def _format_context_for_prompt(messages, uploaded_file_context):
    """
    Formats uploaded file content and integrates it with the message history.
    Simple approach: Prepends text context to the last user message.
    Ignores image context for now for NVIDIA models unless specifically handled.
    """
    context_string = ""
    if uploaded_file_context:
        context_string += "\n\n--- Uploaded File Context ---\n"
        for filename, data in uploaded_file_context.items():
            content = data.get("content")
            metadata = data.get("metadata", {})
            # Only include text content for this basic formatting
            if isinstance(content, str):
                context_string += f"\n--- Content from {filename} ---\n{content}\n--- End of {filename} ---\n"
            # Basic handling for images - just mention them (could be expanded based on model vision capability)
            elif isinstance(content, Image.Image):
                 file_type = metadata.get("type", "image")
                 context_string += f"\n--- Reference to uploaded {file_type}: {filename} ---\n"
            elif metadata.get("type") == "archive": # Basic mention for zip etc.
                context_string += f"\n--- Reference to uploaded archive: {filename} ---\n"
            # Add handling for other types if needed (e.g., pdf summary if not text)

        context_string += "\n--- End of Uploaded File Context ---\n"

    # Prepare a new list to avoid modifying the original session state directly
    formatted_messages = [msg.copy() for msg in messages]

    if context_string and formatted_messages:
        # Find the last user message and prepend context
        context_added = False
        for i in range(len(formatted_messages) - 1, -1, -1):
            if formatted_messages[i].get("role") == "user":
                formatted_messages[i]["content"] = context_string + "\n" + formatted_messages[i]["content"]
                context_added = True
                break
        # If no user message found (e.g., only system/assistant messages),
        # we might decide not to add context or add it differently.
        # For now, we only add it preceding the last user message.

    return formatted_messages # Return the potentially modified copy


# --- Main LLM Interaction Function ---

def get_llm_response(model_display_name, messages, api_keys, uploaded_file_context=None, model_capabilities=None):
    """
    Gets a response from the selected LLM provider.

    Args:
        model_display_name (str): The user-facing name of the model.
        messages (list): The chat history (list of dicts with 'role' and 'content').
        api_keys (dict): Dictionary containing available API keys ({key_name: key_value}).
        uploaded_file_context (dict, optional): Processed data from uploaded files.
        model_capabilities (list, optional): List of capabilities for the selected model.

    Returns:
        tuple: (response_text, generated_file_info)
               response_text (str): The text response from the LLM.
               generated_file_info (dict or None): Info about any generated file.
    """
    internal_id = SUPPORTED_MODELS.get(model_display_name)
    if not internal_id:
        raise ValueError(f"Model '{model_display_name}' is not supported.")

    provider = MODEL_PROVIDER_MAP.get(internal_id)
    if not provider:
        raise ValueError(f"Provider for model '{internal_id}' not found.")

    required_key_name = PROVIDER_API_KEY_NAMES.get(provider)
    api_key = api_keys.get(required_key_name)

    if required_key_name and not api_key:
        raise ValueError(f"API key '{required_key_name}' for provider {provider} not found in provided keys.")

    # Prepare messages, potentially adding context depending on provider/logic
    # We use the helper function to create a list with context potentially added
    messages_with_context = _format_context_for_prompt(messages, uploaded_file_context)

    # Filter messages for typical API format (role, content) and valid roles
    # Handle system prompt separately if needed by the API
    api_messages = []
    system_prompt = None
    for m in messages_with_context:
        role = m.get("role")
        content = m.get("content")
        if role == "system" and not system_prompt: # Capture first system prompt
            system_prompt = content
        elif role in ["user", "assistant"]:
            api_messages.append({"role": role, "content": content})
        # Ignore other roles or malformed messages for the API call

    # --- Provider Specific Logic ---
    response_text = ""
    generated_file_info = None # Placeholder

    try:
        # --- OpenAI ---
        if provider == "OpenAI":
            # Requires: pip install openai
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                # Prepare messages for OpenAI (handle system prompt)
                openai_messages = []
                if system_prompt:
                    openai_messages.append({"role": "system", "content": system_prompt})
                openai_messages.extend(api_messages)

                # Add vision handling if needed (requires more complex message formatting)
                # if "vision" in model_capabilities and uploaded_file_context:
                #    ... format image data for OpenAI ...

                response = client.chat.completions.create(
                    model=internal_id,
                    messages=openai_messages,
                    max_tokens=1024, # Adjust as needed
                )
                response_text = response.choices[0].message.content
            except ImportError:
                st.error("OpenAI library not installed. `pip install openai`")
                response_text = "Error: OpenAI library missing."
            except Exception as e:
                st.error(f"OpenAI API Error: {e}")
                response_text = f"Error communicating with OpenAI: {e}"


        # --- Google ---
        elif provider == "Google":
            # Requires: pip install google-generativeai
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(internal_id) # Use internal ID

                # Simple conversion for Gemini (doesn't separate system prompt explicitly in basic API)
                # History needs specific role mapping ('user' -> 'user', 'assistant' -> 'model')
                gemini_history = []
                full_prompt = ""
                if system_prompt:
                    full_prompt += system_prompt + "\n\n" # Prepend system prompt to first user message content

                for msg in api_messages:
                    role = "user" if msg["role"] == "user" else "model"
                    content = msg["content"]
                    # Prepend system prompt to the first user message if it exists
                    if msg["role"] == "user" and full_prompt:
                        content = full_prompt + content
                        full_prompt = "" # Clear prompt after adding
                    gemini_history.append({"role": role, "parts": [{"text": content}]})

                 # Add vision handling if needed
                 # if "vision" in model_capabilities and uploaded_file_context:
                 #    ... process image data and add to 'parts' ...

                # Adjust call based on history vs single prompt
                if len(gemini_history) > 1:
                    # Use history for conversation context
                    chat = model.start_chat(history=gemini_history[:-1]) # All but last user message
                    response = chat.send_message(gemini_history[-1]["parts"]) # Send last user message
                elif gemini_history: # Only one message (must be user)
                    response = model.generate_content(gemini_history[0]["parts"])
                else: # Should not happen if prompt exists, but handle defensively
                     response_text = "No message to send."
                     return response_text, None

                response_text = response.text

            except ImportError:
                st.error("Google GenAI library not installed. `pip install google-generativeai`")
                response_text = "Error: Google GenAI library missing."
            except Exception as e:
                st.error(f"Google API Error: {e}")
                response_text = f"Error communicating with Google GenAI: {e}"


        # --- Anthropic ---
        elif provider == "Anthropic":
             # Requires: pip install anthropic
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)

                 # Prepare messages for Anthropic (system prompt is a separate param)
                 # Add vision handling if needed
                 # if "vision" in model_capabilities and uploaded_file_context:
                 #    ... format image data for Anthropic messages ...

                response = client.messages.create(
                    model=internal_id,
                    system=system_prompt if system_prompt else None,
                    messages=api_messages,
                    max_tokens=1024, # Adjust as needed
                )
                # Handle different response structures (check Anthropic docs)
                if response.content and isinstance(response.content, list):
                    response_text = "".join([block.text for block in response.content if hasattr(block, 'text')])
                else:
                     response_text = "Received unexpected content structure from Anthropic."

            except ImportError:
                st.error("Anthropic library not installed. `pip install anthropic`")
                response_text = "Error: Anthropic library missing."
            except Exception as e:
                st.error(f"Anthropic API Error: {e}")
                response_text = f"Error communicating with Anthropic: {e}"


        # --- Mistral ---
        elif provider == "Mistral":
             # Requires: pip install mistralai
            try:
                from mistralai.client import MistralClient
                from mistralai.models.chat_completion import ChatMessage

                client = MistralClient(api_key=api_key)

                # Prepare messages for Mistral (handle system prompt - usually first message)
                mistral_messages = []
                if system_prompt:
                     mistral_messages.append(ChatMessage(role="system", content=system_prompt))
                for msg in api_messages:
                     mistral_messages.append(ChatMessage(role=msg["role"], content=msg["content"]))

                response = client.chat(
                    model=internal_id, # Use the internal model ID (e.g., "mistral-large-latest")
                    messages=mistral_messages,
                )
                response_text = response.choices[0].message.content

            except ImportError:
                st.error("MistralAI library not installed. `pip install mistralai`")
                response_text = "Error: MistralAI library missing."
            except Exception as e:
                st.error(f"Mistral API Error: {e}")
                response_text = f"Error communicating with MistralAI: {e}"


        # --- NVIDIA NIM API Call Logic ---
        elif provider == "NVIDIA":
            # Uses 'requests' library (already imported)
            # Check NVIDIA NIM documentation for specific model endpoint if needed,
            # but standard chat completion endpoint should work for listed models.
            invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                # Content-Type is set automatically by requests when using json=payload
            }

             # Prepare messages for NVIDIA (handle system prompt - usually first message)
            nvidia_messages = []
            if system_prompt:
                 nvidia_messages.append({"role": "system", "content": system_prompt})
            nvidia_messages.extend(api_messages)


            payload = {
                "model": internal_id, # Use the internal model ID from SUPPORTED_MODELS
                "messages": nvidia_messages, # Use the formatted messages
                "temperature": 0.5, # Optional: Adjust parameters
                "top_p": 1.0,      # Optional
                "max_tokens": 1024, # Optional
                "stream": False,   # Set to False for a single response object
            }

            try:
                # Make the API call
                api_response = requests.post(invoke_url, headers=headers, json=payload)
                api_response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

                # Parse the response
                response_data = api_response.json()
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message")
                    if message and message.get("content"):
                        response_text = message["content"]
                    else:
                        response_text = "Received an empty message content from NVIDIA API."
                        st.warning(f"Empty content in NVIDIA API response choice: {message}")
                else:
                    response_text = "Received an unexpected response structure from NVIDIA API."
                    st.warning(f"Unexpected NVIDIA API response structure: {response_data}")

            except requests.exceptions.RequestException as e:
                st.error(f"Network error calling NVIDIA API: {e}")
                response_text = f"Sorry, there was a network error connecting to NVIDIA: {e}"
            except json.JSONDecodeError as e:
                st.error(f"Failed to decode JSON response from NVIDIA API: {e}")
                response_text = f"Error parsing NVIDIA response: {e}. Response: {api_response.text[:500]}" # Show partial response
            except Exception as e: # Catch other potential errors from the API call/parsing
                 st.error(f"NVIDIA API Error: {e}")
                 response_text = f"Sorry, an error occurred with the NVIDIA API: {e}"


        # --- Fallback for Unimplemented Providers ---
        else:
            st.warning(f"Provider '{provider}' logic is not implemented yet.")
            response_text = f"Simulated response for {model_display_name} ({provider}) - Implementation Pending"
            # raise NotImplementedError(f"Provider '{provider}' logic is not implemented.")

    # Catch potential exceptions outside provider-specific blocks (e.g., during message formatting)
    except Exception as e:
        st.error(f"An unexpected error occurred in get_llm_response: {e}")
        response_text = f"Sorry, an unexpected error occurred: {e}"

    return response_text, generated_file_info # Return text and None for generated files for now
