# utils/llm_api.py

import requests
import openai
import json
from openai import OpenAIError

class APIError(Exception):
    """Custom exception class for API related errors."""
    pass

def get_response(prompt: str, model: str = "OpenAI", temperature: float = 0.5, max_tokens: int = 512, api_key: str = None):
    """
    Communicates with various LLM APIs to get a response.
    # ... (docstring) ...
    """
    # --- Input Validation ---
    # Add the display names used in app.py here
    supported_models = [
        "OpenAI", "Gemini", "Claude", "Mistral", "Groq",
        "NVIDIA Mistral Small", "NVIDIA DeepSeek Qwen" # Added NVIDIA
        ]
    if model not in supported_models:
        # Use the actual model name passed from app.py in the error
        raise ValueError(f"❌ Unsupported model selected in get_response: '{model}'. Supported models are: {supported_models}")

    if not api_key:
         raise APIError(f"❌ API Key is required for the {model} model but was not provided to get_response.")

    # --- API Call Logic ---
    try:
        if model == "OpenAI":
           # ... (OpenAI code remains the same) ...
            client = openai.OpenAI(api_key=api_key)
            # ... rest of OpenAI code ...
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=temperature, max_tokens=max_tokens)
            if not response.choices or not response.choices[0].message or not response.choices[0].message.content: raise APIError(f"❌ OpenAI API Error: Unexpected response structure. Response: {response}")
            return response.choices[0].message.content.strip()

        elif model == "Gemini":
            # Ensure URL uses /v1/
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
            # ... (rest of Gemini code remains the same) ...
            headers = {"Content-Type": "application/json"}
            data = { "contents": [{"parts": [{"text": prompt}]}], "generationConfig": { "temperature": temperature, "maxOutputTokens": max_tokens, } }
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Gemini API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")
            response_data = response.json()
            # ... (Gemini response parsing) ...
            if 'candidates' not in response_data:
                if 'promptFeedback' in response_data: feedback = response_data['promptFeedback']; block_reason = feedback.get('blockReason', 'Unknown'); safety_ratings = feedback.get('safetyRatings', []); details = f"Reason: {block_reason}, Safety Ratings: {safety_ratings}"; raise APIError(f"❌ Gemini Response Blocked: {details}. Try adjusting your prompt.")
                else: raise APIError(f"❌ Gemini API Error: Unexpected structure (missing 'candidates'). Response: {response_data}")
            if not response_data['candidates']: finish_reason = response_data.get('promptFeedback', {}).get('blockReason', 'Unknown reason, empty candidates list'); raise APIError(f"❌ Gemini API Error: Received empty 'candidates' list. Reason: {finish_reason}")
            try:
                 candidate = response_data['candidates'][0]
                 if 'content' not in candidate: finish_reason = candidate.get('finishReason', 'UNKNOWN'); safety_ratings = candidate.get('safetyRatings', []); raise APIError(f"❌ Gemini response stopped/missing content. Finish Reason: {finish_reason}, Safety Ratings: {safety_ratings}")
                 if not candidate['content'].get('parts'): raise APIError(f"❌ Gemini API Error: 'parts' array missing/empty. Candidate: {candidate}")
                 if 'text' not in candidate['content']['parts'][0]: raise APIError(f"❌ Gemini API Error: 'text' field missing. Part: {candidate['content']['parts'][0]}")
                 return candidate['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Gemini response structure: {type(e).__name__} - {e}. Response Data: {response_data}")

        # ... (Claude, Mistral, Groq code remains the same) ...
        elif model == "Claude":
            # ... Claude code ...
             url = "https://api.anthropic.com/v1/messages"; headers = { "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json" }; data = { "model": "claude-3-opus-20240229", "max_tokens": max_tokens, "temperature": temperature, "messages": [{"role": "user", "content": prompt}] }; response = requests.post(url, headers=headers, json=data);
             if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ Claude API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")
             response_data = response.json();
             try:
                 if not response_data.get("content") or not isinstance(response_data["content"], list) or not response_data["content"][0].get("text"): error_info = "Missing 'content' list, list empty, or first item has no 'text'."; raise APIError(f"❌ Claude API Error: Unexpected structure. {error_info} Response: {response_data}")
                 return response_data["content"][0]["text"]
             except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Claude response structure: {type(e).__name__} - {e}. Response: {response_data}")

        elif model == "Mistral":
            # ... Mistral code ...
             url = "https://api.mistral.ai/v1/chat/completions"; headers = { "Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json" }; data = { "model": "mistral-medium", "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens }; response = requests.post(url, headers=headers, json=data);
             if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ Mistral API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")
             response_data = response.json();
             try:
                 if not response_data.get("choices") or not isinstance(response_data["choices"], list) or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"): raise APIError(f"❌ Mistral API Error: Unexpected structure. Response: {response_data}")
                 return response_data["choices"][0]["message"]["content"]
             except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Mistral response structure: {type(e).__name__} - {e}. Response: {response_data}")

        elif model == "Groq":
            # ... Groq code ...
             url = "https://api.groq.com/openai/v1/chat/completions"; headers = { "Authorization": f"Bearer {api_key}", "Content-Type": "application/json" }; data = { "model": "mixtral-8x7b-32768", "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens }; response = requests.post(url, headers=headers, json=data);
             if response.status_code != 200: try: error_details = response.json() except json.JSONDecodeError: error_details = response.text; raise APIError(f"❌ Groq API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")
             response_data = response.json();
             try:
                 if not response_data.get("choices") or not isinstance(response_data["choices"], list) or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"): raise APIError(f"❌ Groq API Error: Unexpected structure. Response: {response_data}")
                 return response_data["choices"][0]["message"]["content"]
             except (KeyError, IndexError, TypeError) as e: raise APIError(f"❌ Error parsing Groq response structure: {type(e).__name__} - {e}. Response: {response_data}")

        # --- ADD NVIDIA HANDLERS ---
        elif model == "NVIDIA Mistral Small":
            # !! IMPORTANT: You need to find the correct API endpoint, headers, and payload structure from NVIDIA documentation !!
            # Example Placeholder Structure (likely incorrect - REPLACE with actual API spec):
            nvidia_api_base = "https://ai.api.nvidia.com/v1/vlm" # Example Base URL - Check NVIDIA docs
            # Model name might need to be specific in URL or payload
            model_identifier = "mistralai/mistral-7b-instruct-v0.2" # Example - Check NVIDIA docs
            url = f"{nvidia_api_base}/{model_identifier}" # Example URL - Check NVIDIA docs

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                # "Content-Type": "application/json" # Often needed for POST
            }
            # Payload structure depends entirely on NVIDIA's API spec
            data = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False # Example parameter
            }

            # Make the request (POST is common)
            response = requests.post(url, headers=headers, json=data) # Use json=data if Content-Type is json

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ NVIDIA API Error ({model}): Status Code {response.status_code} from URL {url}. Details: {error_details}")

            response_data = response.json()
            # --- Parse the NVIDIA response ---
            # This depends entirely on the actual response structure from NVIDIA
            # Example Placeholder (likely incorrect - REPLACE):
            try:
                if not response_data.get("choices") or not response_data["choices"][0].get("message"):
                    raise APIError(f"❌ NVIDIA API Error ({model}): Unexpected response structure. Response: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                 raise APIError(f"❌ Error parsing NVIDIA response ({model}): {type(e).__name__} - {e}. Response: {response_data}")

        elif model == "NVIDIA DeepSeek Qwen":
            # !! Repeat the process above for this model !!
            # Find the correct endpoint, headers, payload structure for DeepSeek Qwen from NVIDIA docs
            # You might need a different model_identifier or even a different base URL
            # Example Placeholder:
            nvidia_api_base = "https://ai.api.nvidia.com/v1/..." # CHECK DOCS
            model_identifier = "deepseek-ai/deepseek-coder-..." # CHECK DOCS
            url = f"{nvidia_api_base}/{model_identifier}" # CHECK DOCS
            headers = { "Authorization": f"Bearer {api_key}", "Accept": "application/json",}
            data = { "messages": [...], "temperature": temperature, "max_tokens": max_tokens } # CHECK DOCS

            response = requests.post(url, headers=headers, json=data) # CHECK DOCS

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ NVIDIA API Error ({model}): Status Code {response.status_code} from URL {url}. Details: {error_details}")

            response_data = response.json()
            # --- Parse the NVIDIA response ---
            # Example Placeholder (REPLACE):
            try:
                # Add parsing logic specific to this NVIDIA model's response format
                return response_data["choices"][0]["message"]["content"] # Example
            except (KeyError, IndexError, TypeError) as e:
                 raise APIError(f"❌ Error parsing NVIDIA response ({model}): {type(e).__name__} - {e}. Response: {response_data}")


    # --- Global Error Handling ---
    except requests.exceptions.RequestException as e:
        raise APIError(f"❌ Network error communicating with {model} API: {e}") from e
    except OpenAIError as e:
        raise APIError(f"❌ OpenAI Library Error: {type(e).__name__} - {e}") from e

# Optional test block (remains unchanged)
if __name__ == '__main__':
    pass # Keep or remove test code
