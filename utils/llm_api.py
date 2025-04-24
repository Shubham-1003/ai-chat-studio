# utils/llm_api.py

import requests
import openai # For OpenAI API
import json # For parsing JSON responses and errors
from openai import OpenAIError # Import the base error class for openai v1.x+
import traceback # For printing stack trace on unexpected errors

# Define custom exception for API errors for clarity
class APIError(Exception):
    """Custom exception class for API related errors."""
    pass

def get_response(prompt: str, model: str = "OpenAI", temperature: float = 0.5, max_tokens: int = 512, api_key: str = None):
    """
    Communicates with various LLM APIs to get a response.

    Args:
        prompt (str): The user's input prompt.
        model (str): The display name of the LLM model selected in the UI.
                     Should match keys in app.py's SECRETS_KEY_MAPPING.
        temperature (float): The sampling temperature (0.0 to 1.0).
        max_tokens (int): The maximum number of tokens to generate.
        api_key (str): The API key retrieved from st.secrets.

    Returns:
        str: The LLM's response text.

    Raises:
        APIError, ValueError, requests.exceptions.RequestException, OpenAIError
    """
    # --- Input Validation ---
    # Map display names to internal logic/API model names if needed, or handle directly
    supported_models = [
        "OpenAI", "Gemini", "Claude", "Mistral", "Groq",
        "NVIDIA Mistral Small", "NVIDIA DeepSeek Qwen"
        ]
    if model not in supported_models:
        raise ValueError(f"❌ Unsupported model selected in get_response: '{model}'. Check app.py and llm_api.py consistency.")

    if not api_key:
         raise APIError(f"❌ API Key was not provided to get_response function for model {model}.")

    # --- API Call Logic ---
    try:
        # === OpenAI ===
        if model == "OpenAI":
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature, max_tokens=max_tokens
            )
            if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
                 raise APIError(f"❌ OpenAI API Error: Unexpected response structure. Response: {response}")
            return response.choices[0].message.content.strip()

        # === Google Gemini ===
        elif model == "Gemini":
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}" # Use v1
            headers = {"Content-Type": "application/json"}
            data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Gemini API Error: Status {response.status_code} from {url}. Details: {error_details}")

            response_data = response.json()
            # Parse Gemini response carefully
            if 'candidates' not in response_data:
                if 'promptFeedback' in response_data: feedback = response_data['promptFeedback']; block_reason = feedback.get('blockReason', 'Unknown'); details = f"Reason: {block_reason}"; raise APIError(f"❌ Gemini Response Blocked. {details}")
                else: raise APIError(f"❌ Gemini API Error: Unexpected structure (no 'candidates'). Response: {response_data}")
            if not response_data['candidates']: reason = response_data.get('promptFeedback', {}).get('blockReason', 'empty list'); raise APIError(f"❌ Gemini API Error: Empty 'candidates' list. Reason: {reason}")
            try:
                 candidate = response_data['candidates'][0]
                 if 'content' not in candidate: reason = candidate.get('finishReason', 'Unknown'); raise APIError(f"❌ Gemini Error: No 'content' in candidate. Finish Reason: {reason}")
                 if not candidate['content'].get('parts'): raise APIError(f"❌ Gemini Error: No 'parts' in content.")
                 if 'text' not in candidate['content']['parts'][0]: raise APIError(f"❌ Gemini Error: No 'text' in first part.")
                 return candidate['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Gemini response: {e}. Data: {response_data}")

        # === Anthropic Claude ===
        elif model == "Claude":
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            data = {"model": "claude-3-opus-20240229", "max_tokens": max_tokens, "temperature": temperature, "messages": [{"role": "user", "content": prompt}]}
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ Claude API Error: Status {response.status_code} from {url}. Details: {error_details}")
            response_data = response.json()
            try:
                 if not response_data.get("content") or not response_data["content"][0].get("text"): raise APIError(f"❌ Claude Error: Unexpected structure. Resp: {response_data}")
                 return response_data["content"][0]["text"]
            except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Claude response: {e}. Resp: {response_data}")

        # === Mistral AI ===
        elif model == "Mistral":
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"}
            data = {"model": "mistral-medium", "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens}
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ Mistral API Error: Status {response.status_code} from {url}. Details: {error_details}")
            response_data = response.json()
            try:
                 if not response_data.get("choices") or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"): raise APIError(f"❌ Mistral Error: Unexpected structure. Resp: {response_data}")
                 return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Mistral response: {e}. Resp: {response_data}")

        # === Groq ===
        elif model == "Groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {"model": "mixtral-8x7b-32768", "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens}
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ Groq API Error: Status {response.status_code} from {url}. Details: {error_details}")
            response_data = response.json()
            try:
                 if not response_data.get("choices") or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"): raise APIError(f"❌ Groq Error: Unexpected structure. Resp: {response_data}")
                 return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Groq response: {e}. Resp: {response_data}")

        # === NVIDIA Mistral Small ===
        elif model == "NVIDIA Mistral Small":
            # --- Placeholder - Needs actual NVIDIA API details ---
            # Consult NVIDIA AI Playground / API Documentation for correct values
            print(f"--- Attempting NVIDIA call for {model} ---") # Debug print
            # Example (Likely Needs Correction):
            url = "https://ai.api.nvidia.com/v1/chat/completions" # Check endpoint
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json", "Content-Type": "application/json"}
            # Payload needs to specify the *exact* NVIDIA model identifier
            payload = {
                "model": "mistralai/mistral-7b-instruct-v0.2", # Check NVIDIA model list
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                 "stream": False
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ NVIDIA API Error ({model}): Status {response.status_code} from {url}. Details: {error_details}")
            response_data = response.json()
            # Parsing needs to match NVIDIA response structure (often OpenAI compatible)
            try:
                if not response_data.get("choices") or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"): raise APIError(f"❌ NVIDIA Error ({model}): Unexpected structure. Resp: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing NVIDIA ({model}) response: {e}. Resp: {response_data}")
            # --- End Placeholder ---

        # === NVIDIA DeepSeek Qwen ===
        elif model == "NVIDIA DeepSeek Qwen":
            # --- Placeholder - Needs actual NVIDIA API details ---
            # Consult NVIDIA AI Playground / API Documentation for correct values
            print(f"--- Attempting NVIDIA call for {model} ---") # Debug print
            url = "https://ai.api.nvidia.com/v1/chat/completions" # Check endpoint
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-ai/deepseek-coder-33b-instruct", # Check NVIDIA model list for correct ID
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ NVIDIA API Error ({model}): Status {response.status_code} from {url}. Details: {error_details}")
            response_data = response.json()
            try:
                if not response_data.get("choices") or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"): raise APIError(f"❌ NVIDIA Error ({model}): Unexpected structure. Resp: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing NVIDIA ({model}) response: {e}. Resp: {response_data}")
            # --- End Placeholder ---

        else:
            # This case should not be reached if app.py filtering is correct
            raise ValueError(f"Model '{model}' selected but not handled in get_response.")

    # --- Global Error Handling ---
    except requests.exceptions.RequestException as e:
        raise APIError(f"❌ Network error for {model}: {e}") from e
    except OpenAIError as e: # Specific to OpenAI library usage
        raise APIError(f"❌ OpenAI Library Error: {e}") from e
    except Exception as e:
        # Catch other unexpected errors within the API call logic
        if not isinstance(e, (APIError, ValueError)): # Don't re-wrap known errors
             print(f"--- UNEXPECTED Error in get_response for {model} ---")
             traceback.print_exc() # Log details
             raise APIError(f"❌ Unexpected internal error processing {model} request: {type(e).__name__}") from e
        else:
             raise e # Re-raise the specific APIError/ValueError

# Optional test block
if __name__ == '__main__':
    print("llm_api.py executed directly (for testing).")
    # Add test calls here if needed, handling API keys securely
