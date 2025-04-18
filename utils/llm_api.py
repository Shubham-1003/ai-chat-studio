# utils/llm_api.py (Modified for Specific NVIDIA Key Names)
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
    "Mistral Small": "mistral-small-latest",
    # NVIDIA NIM Models
    "NVIDIA DeepSeek-R1 Distill Qwen 32B": "deepseek-ai/deepseek-r1-distill-qwen-32b",
    "NVIDIA Mistral Small 24B Instruct": "mistralai/mistral-small-24b-instruct",
    # Add other models here
}

# Map internal model IDs to their "provider" for logic branching (API call structure)
# NVIDIA models still use the same NVIDIA API structure, so we group them here.
MODEL_API_PROVIDER = {
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
    # Both NVIDIA models use the "NVIDIA" API logic branch
    "deepseek-ai/deepseek-r1-distill-qwen-32b": "NVIDIA",
    "mistralai/mistral-small-24b-instruct": "NVIDIA",
}

# Map SPECIFIC MODEL DISPLAY NAMES to the required API key names in st.secrets
# This is the key change: we map the display name directly
MODEL_DISPLAY_NAME_TO_API_KEY_NAME = {
    # Non-NVIDIA Models (using provider lookup still works, but explicit is clearer)
    "GPT-4o": "OPENAI_API_KEY",
    "GPT-4 Turbo": "OPENAI_API_KEY",
    "GPT-3.5 Turbo": "OPENAI_API_KEY",
    "Gemini 1.5 Pro": "GOOGLE_API_KEY",
    "Gemini 1.0 Pro": "GOOGLE_API_KEY",
    "Claude 3 Opus": "ANTHROPIC_API_KEY",
    "Claude 3 Sonnet": "ANTHROPIC_API_KEY",
    "Claude 3 Haiku": "ANTHROPIC_API_KEY",
    "Mistral Large": "MISTRAL_API_KEY",
    "Mistral Small": "MISTRAL_API_KEY",
    # NVIDIA Models - Map display name to the specific key name in secrets.toml
    "NVIDIA DeepSeek-R1 Distill Qwen 32B": "NVIDIA_DeepSeek_R1_Distill_Qwen_32B",
    "NVIDIA Mistral Small 24B Instruct": "NVIDIA_Mistral_Small_24B_Instruct",
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
    "deepseek-ai/deepseek-r1-distill-qwen-32b": ["chat"],
    "mistralai/mistral-small-24b-instruct": ["chat"],
}

# --- Helper Functions ---

def get_model_capabilities(model_display_name):
    """Gets the capabilities list for a given model display name."""
    internal_id = SUPPORTED_MODELS.get(model_display_name)
    if internal_id:
        # Capabilities are still tied to the internal ID / model type
        return MODEL_CAPABILITIES.get(internal_id, ["chat"])
    return ["chat"]

def get_required_api_key_name(model_display_name):
    """
    Gets the required secret key name based DIRECTLY on the model display name.
    """
    # Use the direct mapping from display name to key name
    return MODEL_DISPLAY_NAME_TO_API_KEY_NAME.get(model_display_name, None)

def _format_context_for_prompt(messages, uploaded_file_context):
    """
    Formats uploaded file content and integrates it with the message history.
    (Code remains the same as before)
    """
    context_string = ""
    if uploaded_file_context:
        context_string += "\n\n--- Uploaded File Context ---\n"
        for filename, data in uploaded_file_context.items():
            content = data.get("content")
            metadata = data.get("metadata", {})
            if isinstance(content, str):
                context_string += f"\n--- Content from {filename} ---\n{content}\n--- End of {filename} ---\n"
            elif isinstance(content, Image.Image):
                 file_type = metadata.get("type", "image")
                 context_string += f"\n--- Reference to uploaded {file_type}: {filename} ---\n"
            elif metadata.get("type") == "archive":
                context_string += f"\n--- Reference to uploaded archive: {filename} ---\n"
        context_string += "\n--- End of Uploaded File Context ---\n"

    formatted_messages = [msg.copy() for msg in messages]
    if context_string and formatted_messages:
        context_added = False
        for i in range(len(formatted_messages) - 1, -1, -1):
            if formatted_messages[i].get("role") == "user":
                formatted_messages[i]["content"] = context_string + "\n" + formatted_messages[i]["content"]
                context_added = True
                break
    return formatted_messages

# --- Main LLM Interaction Function ---

def get_llm_response(model_display_name, messages, api_keys, uploaded_file_context=None, model_capabilities=None):
    """
    Gets a response from the selected LLM provider using the specific API key.
    """
    internal_id = SUPPORTED_MODELS.get(model_display_name)
    if not internal_id:
        raise ValueError(f"Model '{model_display_name}' is not supported.")

    # Determine the API call structure provider
    api_provider = MODEL_API_PROVIDER.get(internal_id)
    if not api_provider:
        raise ValueError(f"API provider logic for model '{internal_id}' not found.")

    # Get the SPECIFIC key name required for THIS display name
    required_key_name = get_required_api_key_name(model_display_name)
    if not required_key_name:
         # Should not happen if model is in SUPPORTED_MODELS and mapped in DISPLAY_NAME_TO_API_KEY_NAME
         raise ValueError(f"API key name mapping not found for '{model_display_name}'.")

    # Fetch the specific key value from the dictionary passed from app.py
    api_key = api_keys.get(required_key_name)

    if not api_key:
        # This error check is important - it means the key wasn't found in secrets.toml
        raise ValueError(f"API key '{required_key_name}' for model '{model_display_name}' not found in provided API keys (check secrets.toml).")

    messages_with_context = _format_context_for_prompt(messages, uploaded_file_context)
    api_messages = []
    system_prompt = None
    for m in messages_with_context:
        role = m.get("role")
        content = m.get("content")
        if role == "system" and not system_prompt:
            system_prompt = content
        elif role in ["user", "assistant"]:
            api_messages.append({"role": role, "content": content})

    response_text = ""
    generated_file_info = None

    try:
        # --- Branch based on API Provider logic ---
        # --- OpenAI ---
        if api_provider == "OpenAI":
            # (Same OpenAI logic as before, uses the correct OPENAI_API_KEY)
            st.warning("OpenAI API call logic not fully implemented in this example.")
            response_text = f"Simulated response for {model_display_name} (OpenAI)"

        # --- Google ---
        elif api_provider == "Google":
            # (Same Google logic as before, uses the correct GOOGLE_API_KEY)
            st.warning("Google GenAI API call logic not fully implemented in this example.")
            response_text = f"Simulated response for {model_display_name} (Google)"

        # --- Anthropic ---
        elif api_provider == "Anthropic":
            # (Same Anthropic logic as before, uses the correct ANTHROPIC_API_KEY)
            st.warning("Anthropic API call logic not fully implemented in this example.")
            response_text = f"Simulated response for {model_display_name} (Anthropic)"

        # --- Mistral ---
        elif api_provider == "Mistral":
            # (Same Mistral logic as before, uses the correct MISTRAL_API_KEY)
            st.warning("Mistral API call logic not fully implemented in this example.")
            response_text = f"Simulated response for {model_display_name} (Mistral)"

        # --- NVIDIA NIM API Call Logic ---
        elif api_provider == "NVIDIA":
            # NOTE: The logic here is the same, but 'api_key' now holds the
            # value specific to the selected NVIDIA model (e.g., the value of
            # NVIDIA_Mistral_Small_24B_Instruct from secrets.toml)
            invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}", # Uses the specific key fetched earlier
                "Accept": "application/json",
            }
            nvidia_messages = []
            if system_prompt:
                 nvidia_messages.append({"role": "system", "content": system_prompt})
            nvidia_messages.extend(api_messages)
            payload = {
                "model": internal_id, # Use the NVIDIA internal model ID
                "messages": nvidia_messages,
                "temperature": 0.5,
                "top_p": 1.0,
                "max_tokens": 1024,
                "stream": False,
            }
            try:
                api_response = requests.post(invoke_url, headers=headers, json=payload)
                api_response.raise_for_status()
                response_data = api_response.json()
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message")
                    if message and message.get("content"):
                        response_text = message["content"]
                    else:
                        response_text = f"Received empty message content from NVIDIA API for {model_display_name}."
                        st.warning(f"Empty content in NVIDIA API response choice: {message}")
                else:
                    response_text = f"Received unexpected response structure from NVIDIA API for {model_display_name}."
                    st.warning(f"Unexpected NVIDIA API response structure: {response_data}")
            except requests.exceptions.RequestException as e:
                st.error(f"Network error calling NVIDIA API for {model_display_name}: {e}")
                response_text = f"Sorry, network error connecting to NVIDIA for {model_display_name}: {e}"
            except json.JSONDecodeError as e:
                st.error(f"Failed to decode JSON response from NVIDIA API for {model_display_name}: {e}")
                response_text = f"Error parsing NVIDIA response: {e}. Response: {api_response.text[:500]}"
            except Exception as e:
                 st.error(f"NVIDIA API Error for {model_display_name}: {e}")
                 response_text = f"Sorry, an error occurred with the NVIDIA API for {model_display_name}: {e}"

        # --- Fallback ---
        else:
            st.warning(f"API Provider logic '{api_provider}' is not implemented yet.")
            response_text = f"Simulated response for {model_display_name} ({api_provider}) - Implementation Pending"

    except Exception as e:
        st.error(f"An unexpected error occurred in get_llm_response: {e}")
        response_text = f"Sorry, an unexpected error occurred: {e}"

    return response_text, generated_file_info
