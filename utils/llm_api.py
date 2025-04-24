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
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            # Construct the request body including generation config
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    # Add other parameters like topP, topK if needed
                    # "topP": 0.9,
                    # "topK": 40,
                },
                 # Optional: Add safety settings if needed
                 # "safetySettings": [
                 #   {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 #   {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                 #   # ... other categories
                 # ]
            }
            response = requests.post(url, headers=headers, json=data)

            # Check HTTP status code first
            if response.status_code != 200:
                try: error_details = response.json() # Try to parse error details
                except json.JSONDecodeError: error_details = response.text # Fallback to raw text
                raise APIError(f"❌ Gemini API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()

            # --- Robust checks for Gemini response structure ---
            if 'candidates' not in response_data:
                # Check for prompt feedback which often indicates blocking due to safety/other reasons
                if 'promptFeedback' in response_data:
                     feedback = response_data['promptFeedback']
                     block_reason = feedback.get('blockReason', 'Unknown')
                     safety_ratings = feedback.get('safetyRatings', [])
                     details = f"Reason: {block_reason}, Safety Ratings: {safety_ratings}"
                     # Provide specific feedback for blocked content
                     raise APIError(f"❌ Gemini Response Blocked: {details}. Try adjusting your prompt.")
                else:
                    # If no candidates and no feedback, it's an unexpected structure
                    raise APIError(f"❌ Gemini API Error: Unexpected response structure (missing 'candidates'). Response: {response_data}")

            # Check if candidates list is empty
            if not response_data['candidates']:
                 # Try to get a reason from promptFeedback if available
                 finish_reason = response_data.get('promptFeedback', {}).get('blockReason', 'Unknown reason, empty candidates list')
                 raise APIError(f"❌ Gemini API Error: Received empty 'candidates' list. Possible reason: {finish_reason}")

            # Safely access the nested structure within the first candidate
            try:
                 candidate = response_data['candidates'][0]
                 # Check if 'content' exists (might be missing if finishReason is SAFETY, RECITATION etc.)
                 if 'content' not in candidate:
                     finish_reason = candidate.get('finishReason', 'UNKNOWN')
                     safety_ratings = candidate.get('safetyRatings', [])
                     raise APIError(f"❌ Gemini response generation stopped or content missing. Finish Reason: {finish_reason}, Safety Ratings: {safety_ratings}")

                 # Check if 'parts' exists and is not empty
                 if not candidate['content'].get('parts'):
                    raise APIError(f"❌ Gemini API Error: 'parts' array is missing or empty in the response content. Candidate: {candidate}")

                 # Check if the first part has 'text'
                 if 'text' not in candidate['content']['parts'][0]:
                     raise APIError(f"❌ Gemini API Error: 'text' field missing in the first part of the response content. Part: {candidate['content']['parts'][0]}")

                 return candidate['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError) as e: # Catch potential parsing errors
                raise APIError(f"❌ Error parsing Gemini response structure: {type(e).__name__} - {e}. Response Data: {response_data}")


        elif model == "Claude":
            # Using Anthropic Claude API via requests
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01", # Keep updated or make configurable
                "content-type": "application/json"
            }
            data = {
                "model": "claude-3-opus-20240229", # Or other Claude models e.g., claude-3-sonnet..., claude-3-haiku...
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
                # You can add system prompts, etc. here if needed
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Claude API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                 # Check structure and content existence
                 if not response_data.get("content") or \
                    not isinstance(response_data["content"], list) or \
                    not response_data["content"][0].get("text"):
                     # More detailed error if structure is wrong
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
                "Accept": "application/json" # Good practice
            }
            data = {
                "model": "mistral-medium", # Or mistral-small, mistral-large etc.
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
                # Add safe_prompt etc. if needed
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Mistral API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                # Check structure (similar to OpenAI)
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
                # Specify Groq models like llama3-8b-8192, mixtral-8x7b-32768, gemma-7b-it
                "model": "mixtral-8x7b-32768",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try: error_details = response.json()
                except json.JSONDecodeError: error_details = response.text
                raise APIError(f"❌ Groq API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                # Check structure (same as OpenAI/Mistral)
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
        # Catch network errors (DNS failure, refused connection, timeout, etc.)
        raise APIError(f"❌ Network error communicating with {model} API: {e}") from e
    except OpenAIError as e:
        # Catch specific errors from the OpenAI library if used (like AuthenticationError)
        # This is specific to the `openai` library usage in the "OpenAI" model block
        raise APIError(f"❌ OpenAI Library Error: {type(e).__name__} - {e}") from e
    # Note: APIError and ValueError raised intentionally within the blocks are not caught here.
    # Consider adding a generic Exception catch if truly unexpected errors need handling,
    # but be specific about what it means.
    # except Exception as e:
    #     if not isinstance(e, (APIError, ValueError)): # Avoid recatching our specific errors
    #         # Log this unexpected error more thoroughly
    #         print(f"CRITICAL UNEXPECTED ERROR in get_response for {model}: {type(e).__name__} - {e}")
    #         traceback.print_exc() # For server logs
    #         raise APIError(f"❌ An critical internal error occurred processing the {model} request.") from e
    #     else:
    #         raise e # Re-raise the specific APIError/ValueError


# Example of how you might test this function (optional)
if __name__ == '__main__':
    # This block runs only when the script is executed directly (e.g., python utils/llm_api.py)
    # Remember to replace "YOUR_API_KEY" with actual keys for testing
    # and potentially handle keys more securely (e.g., environment variables)

    test_prompt = "Explain the concept of Large Language Models in simple terms."
    print(f"Testing with prompt: '{test_prompt}'\n")

    # --- Test OpenAI (replace with your key) ---
    try:
        print("--- Testing OpenAI ---")
        # key_openai = "YOUR_OPENAI_API_KEY"
        # response_openai = get_response(test_prompt, model="OpenAI", api_key=key_openai)
        # print(f"OpenAI Response:\n{response_openai}\n")
        print("OpenAI test skipped (requires key).")
    except APIError as e:
        print(f"OpenAI API Error: {e}\n")
    except Exception as e:
        print(f"OpenAI Unexpected Error: {e}\n")


    # --- Test Gemini (replace with your key) ---
    try:
        print("--- Testing Gemini ---")
        # key_gemini = "YOUR_GEMINI_API_KEY"
        # response_gemini = get_response(test_prompt, model="Gemini", api_key=key_gemini)
        # print(f"Gemini Response:\n{response_gemini}\n")
        print("Gemini test skipped (requires key).")
    except APIError as e:
        print(f"Gemini API Error: {e}\n")
    except Exception as e:
        print(f"Gemini Unexpected Error: {e}\n")


    # --- Test Claude (replace with your key) ---
    try:
        print("--- Testing Claude ---")
        # key_claude = "YOUR_CLAUDE_API_KEY"
        # response_claude = get_response(test_prompt, model="Claude", api_key=key_claude)
        # print(f"Claude Response:\n{response_claude}\n")
        print("Claude test skipped (requires key).")
    except APIError as e:
        print(f"Claude API Error: {e}\n")
    except Exception as e:
        print(f"Claude Unexpected Error: {e}\n")

    # --- Test Mistral (replace with your key) ---
    try:
        print("--- Testing Mistral ---")
        # key_mistral = "YOUR_MISTRAL_API_KEY"
        # response_mistral = get_response(test_prompt, model="Mistral", api_key=key_mistral)
        # print(f"Mistral Response:\n{response_mistral}\n")
        print("Mistral test skipped (requires key).")
    except APIError as e:
        print(f"Mistral API Error: {e}\n")
    except Exception as e:
        print(f"Mistral Unexpected Error: {e}\n")

    # --- Test Groq (replace with your key) ---
    try:
        print("--- Testing Groq ---")
        # key_groq = "YOUR_GROQ_API_KEY"
        # response_groq = get_response(test_prompt, model="Groq", api_key=key_groq)
        # print(f"Groq Response:\n{response_groq}\n")
        print("Groq test skipped (requires key).")
    except APIError as e:
        print(f"Groq API Error: {e}\n")
    except Exception as e:
        print(f"Groq Unexpected Error: {e}\n")
