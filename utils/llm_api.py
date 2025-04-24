# utils/llm_api.py

import requests
import openai # For OpenAI API
import json # For parsing JSON responses and errors
from openai import OpenAIError # Import the base error class for openai v1.x+

# Define custom exception for API errors for clarity
class APIError(Exception):
    """Custom exception class for API related errors."""
    pass

def get_response(prompt: str, model: str = "OpenAI", temperature: float = 0.5, max_tokens: int = 512, api_key: str = None):
    """
    Communicates with various LLM APIs to get a response.
    # ... (rest of the docstring) ...
    """
    # --- Input Validation ---
    supported_models = ["OpenAI", "Gemini", "Claude", "Mistral", "Groq"]
    if model not in supported_models:
        raise ValueError(f"❌ Unsupported model selected: '{model}'. Supported models are: {supported_models}")

    if not api_key:
         raise APIError(f"❌ API Key is required for the {model} model but was not provided (received by get_response).")

    # --- API Call Logic ---
    try:
        if model == "OpenAI":
            # ... (OpenAI code remains the same) ...
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
                 raise APIError(f"❌ OpenAI API Error: Unexpected response structure. Response: {response}")
            return response.choices[0].message.content.strip()


        elif model == "Gemini":
            # --- ENSURE THIS URL IS CORRECT ---
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
            # --- END URL CHECK ---

            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                # Include URL in error
                raise APIError(f"❌ Gemini API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")

            response_data = response.json()

            # ... (Gemini response parsing remains the same) ...
            if 'candidates' not in response_data:
                if 'promptFeedback' in response_data:
                     feedback = response_data['promptFeedback']
                     block_reason = feedback.get('blockReason', 'Unknown')
                     safety_ratings = feedback.get('safetyRatings', [])
                     details = f"Reason: {block_reason}, Safety Ratings: {safety_ratings}"
                     raise APIError(f"❌ Gemini Response Blocked: {details}. Try adjusting your prompt.")
                else:
                    raise APIError(f"❌ Gemini API Error: Unexpected response structure (missing 'candidates'). Response: {response_data}")
            if not response_data['candidates']:
                 finish_reason = response_data.get('promptFeedback', {}).get('blockReason', 'Unknown reason, empty candidates list')
                 raise APIError(f"❌ Gemini API Error: Received empty 'candidates' list. Possible reason: {finish_reason}")
            try:
                 candidate = response_data['candidates'][0]
                 if 'content' not in candidate:
                     finish_reason = candidate.get('finishReason', 'UNKNOWN')
                     safety_ratings = candidate.get('safetyRatings', [])
                     raise APIError(f"❌ Gemini response generation stopped or content missing. Finish Reason: {finish_reason}, Safety Ratings: {safety_ratings}")
                 if not candidate['content'].get('parts'):
                    raise APIError(f"❌ Gemini API Error: 'parts' array is missing or empty. Candidate: {candidate}")
                 if 'text' not in candidate['content']['parts'][0]:
                     raise APIError(f"❌ Gemini API Error: 'text' field missing. Part: {candidate['content']['parts'][0]}")
                 return candidate['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError) as e:
                raise APIError(f"❌ Error parsing Gemini response structure: {type(e).__name__} - {e}. Response Data: {response_data}")

        # ... (Code for Claude, Mistral, Groq remains the same) ...
        elif model == "Claude":
            # ... Claude code ...
             url = "https://api.anthropic.com/v1/messages"
             headers = { "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json" }
             data = { "model": "claude-3-opus-20240229", "max_tokens": max_tokens, "temperature": temperature, "messages": [{"role": "user", "content": prompt}] }
             response = requests.post(url, headers=headers, json=data)
             if response.status_code != 200:
                 try: error_details = response.json()
                 except json.JSONDecodeError: error_details = response.text
                 raise APIError(f"❌ Claude API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")
             response_data = response.json()
             try:
                 if not response_data.get("content") or not isinstance(response_data["content"], list) or not response_data["content"][0].get("text"):
                      error_info = "Missing 'content' list, list empty, or first item has no 'text'."
                      raise APIError(f"❌ Claude API Error: Unexpected response structure. {error_info} Response: {response_data}")
                 return response_data["content"][0]["text"]
             except (KeyError, IndexError, TypeError) as e:
                  raise APIError(f"❌ Error parsing Claude response structure: {type(e).__name__} - {e}. Response: {response_data}")

        elif model == "Mistral":
            # ... Mistral code ...
             url = "https://api.mistral.ai/v1/chat/completions"
             headers = { "Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json" }
             data = { "model": "mistral-medium", "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens }
             response = requests.post(url, headers=headers, json=data)
             if response.status_code != 200:
                 try: error_details = response.json()
                 except json.JSONDecodeError: error_details = response.text
                 raise APIError(f"❌ Mistral API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")
             response_data = response.json()
             try:
                 if not response_data.get("choices") or not isinstance(response_data["choices"], list) or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"):
                     raise APIError(f"❌ Mistral API Error: Unexpected response structure. Response: {response_data}")
                 return response_data["choices"][0]["message"]["content"]
             except (KeyError, IndexError, TypeError) as e:
                 raise APIError(f"❌ Error parsing Mistral response structure: {type(e).__name__} - {e}. Response: {response_data}")

        elif model == "Groq":
            # ... Groq code ...
             url = "https://api.groq.com/openai/v1/chat/completions"
             headers = { "Authorization": f"Bearer {api_key}", "Content-Type": "application/json" }
             data = { "model": "mixtral-8x7b-32768", "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens }
             response = requests.post(url, headers=headers, json=data)
             if response.status_code != 200:
                 try: error_details = response.json()
                 except json.JSONDecodeError: error_details = response.text
                 raise APIError(f"❌ Groq API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")
             response_data = response.json()
             try:
                 if not response_data.get("choices") or not isinstance(response_data["choices"], list) or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"):
                      raise APIError(f"❌ Groq API Error: Unexpected response structure. Response: {response_data}")
                 return response_data["choices"][0]["message"]["content"]
             except (KeyError, IndexError, TypeError) as e:
                 raise APIError(f"❌ Error parsing Groq response structure: {type(e).__name__} - {e}. Response: {response_data}")


    # --- Global Error Handling ---
    except requests.exceptions.RequestException as e:
        raise APIError(f"❌ Network error communicating with {model} API: {e}") from e
    except OpenAIError as e:
        raise APIError(f"❌ OpenAI Library Error: {type(e).__name__} - {e}") from e

# Optional test block (remains unchanged)
if __name__ == '__main__':
    # ... (test code as before) ...
    pass # Keep test code or remove if not needed
