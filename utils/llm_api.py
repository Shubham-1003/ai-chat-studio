# utils/llm_api.py (Complete Code with Fix)

import streamlit as st
import os
from typing import List, Dict, Any, Tuple
import io  # Added for BytesIO
import base64 # Added for base64 encoding
from PIL import Image # Added for Image type hint

# --- Placeholder LLM API Interaction Functions ---
# You MUST replace these with actual API calls using libraries like:
# openai, google-generativeai, anthropic, mistralai, requests, etc.

# --- Model Configuration ---
# Define models and their *potential* capabilities (you might need to refine this)
# Structure: "Display Name": {"provider": "internal_provider_name", "model_id": "api_model_name", "capabilities": ["text", "vision", "file_gen_text"]}
SUPPORTED_MODELS = {
    "OpenAI GPT-4o": {"provider": "openai", "model_id": "gpt-4o", "capabilities": ["text", "vision"]},
    "OpenAI GPT-4 Turbo": {"provider": "openai", "model_id": "gpt-4-turbo", "capabilities": ["text", "vision"]},
    "OpenAI GPT-3.5 Turbo": {"provider": "openai", "model_id": "gpt-3.5-turbo", "capabilities": ["text"]},
    "Google Gemini 1.5 Pro": {"provider": "google", "model_id": "gemini-1.5-pro-latest", "capabilities": ["text", "vision"]},
    "Google Gemini 1.0 Pro": {"provider": "google", "model_id": "gemini-1.0-pro", "capabilities": ["text", "vision"]}, # Check specific vision support
    "Anthropic Claude 3 Opus": {"provider": "anthropic", "model_id": "claude-3-opus-20240229", "capabilities": ["text", "vision"]},
    "Anthropic Claude 3 Sonnet": {"provider": "anthropic", "model_id": "claude-3-sonnet-20240229", "capabilities": ["text", "vision"]},
    "Anthropic Claude 3 Haiku": {"provider": "anthropic", "model_id": "claude-3-haiku-20240307", "capabilities": ["text", "vision"]},
    "Mistral Large": {"provider": "mistral", "model_id": "mistral-large-latest", "capabilities": ["text"]},
    "Mistral Small": {"provider": "mistral", "model_id": "mistral-small-latest", "capabilities": ["text"]},
    "Mistral 7B Instruct": {"provider": "mistral", "model_id": "open-mistral-7b", "capabilities": ["text"]}, # Often self-hosted or via specific APIs
    "DeepSeek Coder V2": {"provider": "deepseek", "model_id": "deepseek-coder", "capabilities": ["text"]}, # Check exact API name
    "Meta Llama 3 70B Instruct": {"provider": "meta", "model_id": "llama3-70b-instruct", "capabilities": ["text"]}, # Often via Groq, Together, etc.
    "Meta Llama 3 8B Instruct": {"provider": "meta", "model_id": "llama3-8b-instruct", "capabilities": ["text"]}, # Often via Groq, Together, etc.
}

# Mapping of provider names to required API keys (used in sidebar)
PROVIDER_API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY", # Often referred to as GEMINI_API_KEY
    "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY", # Placeholder, check actual key name
    "meta": "META_API_KEY", # Placeholder, depends on hosting provider (e.g., GROQ_API_KEY, TOGETHER_API_KEY)
}

def get_model_capabilities(model_display_name: str) -> List[str]:
    """Returns the declared capabilities for a given model."""
    # Handle case where model might not be found (e.g., during initial load)
    model_info = SUPPORTED_MODELS.get(model_display_name, {})
    return model_info.get("capabilities", ["text"])


def get_required_api_key_name(model_display_name: str) -> str | None:
    """Gets the environment variable/session state key name for the selected model's provider."""
    provider = SUPPORTED_MODELS.get(model_display_name, {}).get("provider")
    return PROVIDER_API_KEYS.get(provider) if provider else None

# --- Generic LLM Response Function ---

def get_llm_response(
    model_display_name: str,
    messages: List[Dict[str, str]],
    api_keys: Dict[str, str],
    uploaded_file_context: Dict[str, Any] = None, # Pass processed file context
    model_capabilities: List[str] = None
) -> Tuple[str, Dict[str, Any] | None]:
    """
    Main function to route request to the appropriate LLM API.

    Args:
        model_display_name: The user-selected model name.
        messages: Chat history (list of {"role": "user/assistant", "content": "..."}).
        api_keys: Dictionary containing API keys entered by the user.
        uploaded_file_context: Dictionary containing processed data from uploaded files.
                                Keys are filenames, values contain 'content' and 'metadata'.
        model_capabilities: List of capabilities like 'vision'.

    Returns:
        A tuple containing:
        - The text response from the LLM.
        - Optional dictionary with generated file info (e.g., {"filename": "summary.txt", "content": "..."})
    """
    if model_display_name not in SUPPORTED_MODELS:
         st.error(f"Model '{model_display_name}' not found in configuration.")
         return "Error: Selected model configuration not found.", None

    if model_capabilities is None:
        model_capabilities = get_model_capabilities(model_display_name)

    model_info = SUPPORTED_MODELS.get(model_display_name)
    if not model_info:
        return "Error: Model configuration not found.", None

    provider = model_info["provider"]
    model_id = model_info["model_id"]
    required_key_name = PROVIDER_API_KEYS.get(provider)

    # Check for API key *before* attempting to use it
    api_key = api_keys.get(required_key_name)
    if not required_key_name or not api_key:
        # Check if we *already* displayed the error in the sidebar (app.py)
        # Avoid showing duplicate errors if possible.
        # This assumes app.py handles the primary check.
        # If running directly, this check is still needed.
        # Let's return a clear error regardless.
        return f"Error: API Key for {provider.capitalize()} ({required_key_name}) is missing or not loaded.", None

    # --- Construct Prompt with Context ---
    # Combine chat history and file context into the prompt for the LLM
    prompt_content = [] # Will build a list of message parts
    file_prompt = ""    # Initialize file_prompt as empty string

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !! THE FIX IS HERE: Initialize image_files as empty list !!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    image_files = []

    # Add file context (simplified example)
    if uploaded_file_context:
        file_prompt = "The user has uploaded the following files (content summary included):\n"
        # image_files = [] # <<<=== REMOVED or COMMENTED OUT the original definition inside the 'if' block
        for filename, data in uploaded_file_context.items():
            metadata = data.get("metadata", {})
            content = data.get("content", "") # This might be text or just a description
            file_type = metadata.get("type", "unknown")
            image_obj = metadata.get("image_obj") # Get the PIL image object if it exists

            file_prompt += f"\n--- File: {filename} ({file_type}) ---\n"

            # Handle image data for vision models
            if 'vision' in model_capabilities and image_obj and isinstance(image_obj, Image.Image):
                try:
                    buffered = io.BytesIO()
                    # Save in a common format like PNG or JPEG
                    image_format = image_obj.format if image_obj.format in ["JPEG", "PNG", "WEBP"] else "PNG"
                    image_obj.save(buffered, format=image_format)
                    img_bytes = buffered.getvalue()
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                    # Store necessary info for different APIs
                    image_data_for_api = {
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{image_format.lower()}",
                            "data": img_base64
                        }
                    }
                    # OpenAI/Anthropic like base64 URLs within content
                    image_data_for_url_format = {
                         "type": "image_url",
                         "image_url": {
                             "url": f"data:image/{image_format.lower()};base64,{img_base64}",
                             "detail": "auto" # or low/high
                         }
                    }
                    # Gemini likes PIL Images or raw bytes/base64 dicts directly
                    image_data_for_gemini = image_obj # Pass PIL object

                    image_files.append({
                        "filename": filename,
                        "api_format": image_data_for_api, # For Anthropic
                        "url_format": image_data_for_url_format, # For OpenAI
                        "pil_object": image_data_for_gemini # For Gemini
                    })
                    file_prompt += f"[Content: Image data for '{filename}' prepared for vision model]\n"
                except Exception as e:
                    st.warning(f"Could not encode image {filename} for vision model: {e}")
                    file_prompt += f"[Content: Error encoding image '{filename}']\n"

            # Handle text content
            elif isinstance(content, str):
                # Truncate long text content to avoid exceeding token limits
                truncated_content = content[:2000] + ("..." if len(content) > 2000 else "")
                file_prompt += f"{truncated_content}\n"
            else:
                # Handle other types (like zip file summaries, etc.)
                file_prompt += f"[Content: {str(content)}]\n" # Convert non-string content to string

        file_prompt += "--- End of Files ---\n\n"

        # Prepend file context to the *first* user message in the history going to the LLM
        # Create a *copy* of messages to avoid modifying session state directly
        history_copy = [msg.copy() for msg in messages]
        first_user_msg_index = -1
        for i, msg in enumerate(history_copy):
            if msg["role"] == "user":
                first_user_msg_index = i
                break

        if first_user_msg_index != -1:
            history_copy[first_user_msg_index]['content'] = file_prompt + history_copy[first_user_msg_index]['content']
            messages_to_send = history_copy # Use the modified copy
        else:
            # If no user messages, we shouldn't really call the LLM yet
            # Or, maybe send the file prompt as the user message? Depends on desired UX.
             return "Please provide a prompt to interact with the uploaded files.", None
    else:
        # No files uploaded, use the original messages
        messages_to_send = messages


    # --- Format Messages and Call Specific API ---
    formatted_messages = [] # This will hold the final structure for the specific API

    try:
        # st.write(f"--- Debug: Calling {provider} ({model_id}) ---") # Debug

        if provider == "openai":
            # Requires `openai` library
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            openai_messages = []
            for msg in messages_to_send: # Use potentially modified messages
                role = msg["role"]
                content = msg["content"]
                # OpenAI expects content to be string OR list of dicts for multimodal
                if role == "user" and image_files and msg == messages_to_send[-1]: # Add images to last user msg
                    message_content = [{"type": "text", "text": content}]
                    for img_data in image_files:
                        message_content.append(img_data['url_format']) # Use base64 URL format
                else:
                     # If not last user message or no images, send text only
                     message_content = content # Should be string here

                openai_messages.append({"role": role, "content": message_content})

            # st.write("OpenAI Payload:", openai_messages) # Debug
            response = client.chat.completions.create(
                model=model_id,
                messages=openai_messages,
                max_tokens=2000 # Adjust as needed
            )
            text_response = response.choices[0].message.content
            return text_response, None # Placeholder for file generation

        elif provider == "google":
            # Requires `google-generativeai` library
            import google.generativeai as genai
            # Check if configured - might happen if key is missing but app didn't stop
            try:
                 genai.configure(api_key=api_key)
            except Exception as e:
                 return f"Error configuring Google Gemini: {e}", None

            model = genai.GenerativeModel(model_id)
            # Gemini API expects "parts" list within content, role "user" or "model"
            gemini_history = []
            for msg in messages_to_send[:-1]: # Process history except the last message
                role = "user" if msg["role"] == "user" else "model"
                # History typically doesn't include images for Gemini, just text
                gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})

            # Prepare the final prompt (last message + images)
            last_message = messages_to_send[-1]
            final_prompt_parts = [{"text": last_message["content"]}]
            if last_message["role"] == "user" and image_files and 'vision' in model_capabilities:
                for img_data in image_files:
                     # Gemini prefers PIL objects or dicts with inline_data
                     final_prompt_parts.append(img_data['pil_object']) # Add PIL image object

            # Filter out invalid history (e.g., starting with 'model')
            if gemini_history and gemini_history[0]['role'] == 'model':
                gemini_history = gemini_history[1:] # Adjust if needed

            # Create chat session with history
            chat = model.start_chat(history=gemini_history)

            # st.write("Gemini Final Prompt Parts:", final_prompt_parts) # Debug
            # st.write("Gemini History:", gemini_history) # Debug

            # Send the final prompt parts
            response = chat.send_message(final_prompt_parts)
            text_response = response.text
            return text_response, None

        elif provider == "anthropic":
            # Requires `anthropic` library
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            anthropic_messages = []
            system_prompt = "" # Optional: Define a system prompt here

            for msg in messages_to_send: # Use potentially modified messages
                role = msg["role"] # Should be 'user' or 'assistant'
                content = msg["content"]
                message_content = []

                # Add text part first
                message_content.append({"type": "text", "text": content})

                # Add images if it's the user message and images exist
                if role == "user" and image_files:
                     for img_data in image_files:
                          # Anthropic uses a dict format for images
                          message_content.append({
                              "type": "image",
                              "source": img_data['api_format']['source'] # Use the base64 dict format
                          })
                     # Clear image_files after adding to prevent adding to subsequent messages
                     # This assumes images are only relevant to the *first* user message they appear with
                     # image_files = [] # Reconsider if images should persist across turns

                anthropic_messages.append({"role": role, "content": message_content})

            # Ensure history alternates if needed (Anthropic is flexible but prefers it)
            # Basic check: remove leading assistant messages if any
            while anthropic_messages and anthropic_messages[0]['role'] == 'assistant':
                anthropic_messages.pop(0)

            if not anthropic_messages or anthropic_messages[-1]['role'] != 'user':
                 return "Error: Cannot send request to Claude without a final user message.", None

            # st.write("Anthropic Payload:", anthropic_messages) # Debug
            response = client.messages.create(
                model=model_id,
                max_tokens=2000,
                system=system_prompt if system_prompt else None,
                messages=anthropic_messages
            )
            text_response = ""
            # Handle potential block types in response
            for block in response.content:
                if block.type == "text":
                    text_response += block.text
            return text_response, None


        elif provider == "mistral":
            # Requires `mistralai` library
            from mistralai.client import MistralClient
            from mistralai.models.chat_completion import ChatMessage
            client = MistralClient(api_key=api_key)

            # Mistral format - expects text content only currently via official client
            # Vision models might exist via other endpoints (e.g., self-hosted, other providers)
            if image_files and 'vision' in model_capabilities:
                 st.warning("Mistral API via official client doesn't support images directly in chat history yet. Sending text only.")

            mistral_messages = [
                ChatMessage(role=msg["role"], content=msg["content"])
                for msg in messages_to_send if isinstance(msg.get("content"), str) # Ensure content is string
            ]

            # st.write("Mistral Payload:", mistral_messages) # Debug
            if not mistral_messages:
                 return "Error: No valid text messages to send to Mistral.", None

            response = client.chat(
                model=model_id,
                messages=mistral_messages,
            )
            text_response = response.choices[0].message.content
            return text_response, None

        # --- Add other providers (DeepSeek, Meta Llama via API) ---
        # These often require using `requests` or specific SDKs depending on the endpoint provider
        # Example structure for a generic API endpoint:
        # elif provider == "deepseek":
        #     # import requests
        #     # headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        #     # payload = {"model": model_id, "messages": formatted_messages, ...} # Adjust payload format
        #     # api_endpoint = "YOUR_DEEPSEEK_API_ENDPOINT"
        #     # response = requests.post(api_endpoint, headers=headers, json=payload)
        #     # response.raise_for_status() # Check for HTTP errors
        #     # result = response.json()
        #     # text_response = result['choices'][0]['message']['content'] # Adjust based on actual API response structure
        #     # return text_response, None
        #     st.warning("DeepSeek API call not implemented yet.")
        #     return "DeepSeek integration placeholder.", None

        # elif provider == "meta":
        #     # Depends on the hosting service (e.g., Groq, Together AI, Replicate)
        #     # Example using a hypothetical Groq client (install `groq`)
        #     # from groq import Groq
        #     # client = Groq(api_key=api_key) # Assuming GROQ_API_KEY was set
        #     # groq_messages = [...] # Format messages for Groq
        #     # response = client.chat.completions.create(model=model_id, messages=groq_messages, ...)
        #     # text_response = response.choices[0].message.content
        #     # return text_response, None
        #     st.warning("Meta Llama API call not implemented yet (depends on hosting provider).")
        #     return "Meta Llama integration placeholder.", None

        else:
            st.error(f"Provider '{provider}' logic is not implemented in llm_api.py.")
            return f"Error: Provider '{provider}' not implemented yet.", None

    except Exception as e:
        # Log the full error for debugging
        import traceback
        st.error(f"Error calling {provider} API: {e}")
        st.error(f"Traceback: {traceback.format_exc()}") # More detailed error for debugging
        return f"An error occurred while contacting the {provider} API.", None