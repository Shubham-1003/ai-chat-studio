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

    Args:
        prompt (str): The user's input prompt.
        model (str): The name of the LLM model to use.
                     Options: "OpenAI", "Gemini", "Claude", "Mistral", "Groq".
        temperature (float): The sampling temperature (0.0 to 1.0).
        max_tokens (int): The maximum number of tokens to generate.
        api_key (str): The API key for the selected service. Required for all models.

    Returns:
        str: The LLM's response text.

    Raises:
        APIError: If communication with the API fails, returns an error status,
                  has an unexpected response structure, or if the API key is missing.
        ValueError: If an unsupported model is selected.
        requests.exceptions.RequestException: For network-level errors during the request.
        OpenAIError: For specific errors from the OpenAI library.
    """
    # --- Input Validation ---
    supported_models = ["OpenAI", "Gemini", "Claude", "Mistral", "Groq"]
    if model not in supported_models:
        raise ValueError(f"❌ Unsupported model selected: '{model}'. Supported models are: {supported_models}")

    if not api_key:
         # Raise APIError for missing key as it's an API interaction requirement
         raise APIError(f"❌ API Key is required for the {model} model but was not provided.")

    # --- API Call Logic ---
    try:
        if model == "OpenAI":
            # Using OpenAI Python client v1.x+
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # Consider making this a parameter if needed
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            # Check if response structure is as expected
            if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
                 raise APIError(f"❌ OpenAI API Error: Unexpected response structure. Response: {response}")
            return response.choices[0].message.content.strip()

        elif model == "Gemini":
            # Using Google AI Gemini REST API via requests

            # --- THIS IS THE LINE TO CHANGE ---
            # Old: url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            # New: Use v1 instead of v1beta
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
            # --- END OF CHANGE ---

            headers = {"Content-Type": "application/json"}
            # Construct the request body including generation config
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
                 # Optional: Add safety settings if needed
                 # "safetySettings": [ ... ]
            }
            response = requests.post(url, headers=headers, json=data)

            # Check HTTP status code first
            if response.status_code != 200:
                try: error_details = response.json() # Try to parse error details
                except json.JSONDecodeError: error_details = response.text # Fallback to raw text
                # Include the URL in the error message for easier debugging
                raise APIError(f"❌ Gemini API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")

            response_data = response.json()

            # --- Robust checks for Gemini response structure ---
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
                    raise APIError(f"❌ Gemini API Error: 'parts' array is missing or empty in the response content. Candidate: {candidate}")

                 if 'text' not in candidate['content']['parts'][0]:
                     raise APIError(f"❌ Gemini API Error: 'text' field missing in the first part of the response content. Part: {candidate['content']['parts'][0]}")

                 return candidate['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError) as e:
                raise APIError(f"❌ Error parsing Gemini response structure: {type(e).__name__} - {e}. Response Data: {response_data}")


        elif model == "Claude":
            # Using Anthropic Claude API via requests
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": "claude-3-opus-20240229",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Claude API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")

            response_data = response.json()
            try:
                 if not response_data.get("content") or \
                    not isinstance(response_data["content"], list) or \
                    not response_data["content"][0].get("text"):
                     error_info = "Missing 'content' list, list empty, or first item has no 'text'."
                     raise APIError(f"❌ Claude API Error: Unexpected response structure. {error_info} Response: {response_data}")
                 return response_data["content"][0]["text"]
            except (KeyError, IndexError, TypeError) as e:
                 raise APIError(f"❌ Error parsing Claude response structure: {type(e).__name__} - {e}. Response: {response_data}")


        elif model == "Mistral":
            # Using Mistral AI API via requests
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            data = {
                "model": "mistral-medium",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Mistral API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")

            response_data = response.json()
            try:
                if not response_data.get("choices") or \
                   not isinstance(response_data["choices"], list) or \
                   not response_data["choices"][0].get("message") or \
                   not response_data["choices"][0]["message"].get("content"):
                    raise APIError(f"❌ Mistral API Error: Unexpected response structure. Response: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                raise APIError(f"❌ Error parsing Mistral response structure: {type(e).__name__} - {e}. Response: {response_data}")


        elif model == "Groq":
             # Using Groq API (OpenAI compatible endpoint) via requests
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "mixtral-8x7b-32768",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Groq API Error: Status Code {response.status_code} from URL {url}. Details: {error_details}")

            response_data = response.json()
            try:
                if not response_data.get("choices") or \
                   not isinstance(response_data["choices"], list) or \
                   not response_data["choices"][0].get("message") or \
                   not response_data["choices"][0]["message"].get("content"):
                     raise APIError(f"❌ Groq API Error: Unexpected response structure. Response: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                raise APIError(f"❌ Error parsing Groq response structure: {type(e).__name__} - {e}. Response: {response_data}")


    # --- Global Error Handling for API Calls ---
    except requests.exceptions.RequestException as e:
        raise APIError(f"❌ Network error communicating with {model} API: {e}") from e
    except OpenAIError as e:
        raise APIError(f"❌ OpenAI Library Error: {type(e).__name__} - {e}") from e
    # Note: Other exceptions like APIError/ValueError raised above will propagate naturally


# Optional test block (remains unchanged)
if __name__ == '__main__':
    # ... (test code as before) ...
    test_prompt = "Explain the concept of Large Language Models in simple terms."
    print(f"Testing with prompt: '{test_prompt}'\n")
    # ... (individual model test blocks skipped for brevity) ...
    print("Testing skipped (requires API keys).")
