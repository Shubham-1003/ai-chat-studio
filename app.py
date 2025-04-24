import requests
import openai # Import the main library
import json

# Import specific errors from the newer openai versions if needed,
# or just catch the base error.
from openai import OpenAIError # Import the base error class

# Define custom exception for API errors for clarity
class APIError(Exception):
    pass

def get_response(prompt, model="OpenAI", temperature=0.5, max_tokens=512, api_key=None):
    """
    Communicates with various LLM APIs to get a response.

    Args:
        prompt (str): The user's input prompt.
        model (str): The name of the LLM model to use.
        temperature (float): The sampling temperature.
        max_tokens (int): The maximum number of tokens to generate.
        api_key (str): The API key for the selected service.

    Returns:
        str: The LLM's response text.

    Raises:
        APIError: If communication with the API fails or returns an error.
        ValueError: If an unsupported model is selected.
    """
    # It's good practice to check for API key presence early for relevant models
    if not api_key and model in ["OpenAI", "Gemini", "Claude", "Mistral", "Groq"]:
         raise APIError(f"❌ API Key is required for the {model} model but was not provided.")

    try:
        if model == "OpenAI":
            # For openai v1.x+, you instantiate a client
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # Or other models like gpt-4
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            # Accessing the response content is also slightly different
            return response.choices[0].message.content.strip()

        elif model == "Gemini":
            # Ensure API key is included in the URL (or headers if preferred by API docs)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                }
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try:
                    error_details = response.json()
                except json.JSONDecodeError:
                    error_details = response.text
                raise APIError(f"❌ Gemini API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()

            if 'candidates' not in response_data:
                if 'promptFeedback' in response_data:
                     feedback = response_data['promptFeedback']
                     block_reason = feedback.get('blockReason', 'Unknown')
                     safety_ratings = feedback.get('safetyRatings', [])
                     details = f"Reason: {block_reason}, Safety Ratings: {safety_ratings}"
                     # Use a more specific message for blocked content
                     raise APIError(f"❌ Gemini Response Blocked: {details}. Try adjusting your prompt.")
                else:
                    raise APIError(f"❌ Gemini API Error: Unexpected response structure (missing 'candidates'). Response: {response_data}")

            if not response_data['candidates']:
                 # Handle cases where candidates list is present but empty
                 finish_reason = response_data.get('promptFeedback', {}).get('blockReason', 'Unknown reason, empty candidates')
                 raise APIError(f"❌ Gemini API Error: Received empty 'candidates' list. Possible reason: {finish_reason}")


            try:
                 # Check for content within the first candidate
                 candidate = response_data['candidates'][0]
                 if 'content' not in candidate:
                     finish_reason = candidate.get('finishReason', 'UNKNOWN')
                     safety_ratings = candidate.get('safetyRatings', [])
                     # Provide more context if content is missing
                     raise APIError(f"❌ Gemini response generation stopped or content missing. Finish Reason: {finish_reason}, Safety Ratings: {safety_ratings}")

                 # Safely access parts - check if 'parts' exists and is not empty
                 if not candidate['content'].get('parts'):
                    raise APIError(f"❌ Gemini API Error: 'parts' array is missing or empty in the response content. Candidate: {candidate}")

                 return candidate['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError) as e: # Added TypeError for safety
                raise APIError(f"❌ Error parsing Gemini response structure: {e}. Response Data: {response_data}")


        elif model == "Claude":
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
                raise APIError(f"❌ Claude API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                 if not response_data.get("content") or not isinstance(response_data["content"], list) or not response_data["content"][0].get("text"):
                     raise APIError(f"❌ Claude API Error: Unexpected response structure. Response: {response_data}")
                 return response_data["content"][0]["text"]
            except (KeyError, IndexError, TypeError) as e:
                 raise APIError(f"❌ Error parsing Claude response structure: {e}. Response: {response_data}")


        elif model == "Mistral":
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
                raise APIError(f"❌ Mistral API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                if not response_data.get("choices") or not isinstance(response_data["choices"], list) or \
                   not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"):
                    raise APIError(f"❌ Mistral API Error: Unexpected response structure. Response: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                raise APIError(f"❌ Error parsing Mistral response structure: {e}. Response: {response_data}")


        elif model == "Groq":
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
                raise APIError(f"❌ Groq API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                if not response_data.get("choices") or not isinstance(response_data["choices"], list) or \
                   not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"):
                     raise APIError(f"❌ Groq API Error: Unexpected response structure. Response: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                raise APIError(f"❌ Error parsing Groq response structure: {e}. Response: {response_data}")


        else:
            raise ValueError("❌ Unsupported model selected.")

    except requests.exceptions.RequestException as e:
        raise APIError(f"❌ Network error communicating with {model} API: {e}")
    # --- THIS IS THE UPDATED LINE ---
    except OpenAIError as e: # Catch the base error from openai v1.x+
         # You can potentially catch more specific errors like openai.AuthenticationError if needed
         raise APIError(f"❌ OpenAI API Error: {type(e).__name__} - {e}")
    # --- END OF UPDATE ---
    except Exception as e:
        # Catch any other unexpected error during the API call logic
        # Avoid catching the APIError/ValueError raised intentionally above
        if not isinstance(e, (APIError, ValueError)):
             raise APIError(f"❌ An unexpected error occurred processing the {model} request: {type(e).__name__} - {e}")
        else:
             raise e # Re-raise the intentionally raised APIError or ValueError
