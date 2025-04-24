import requests
import openai
import json # Import json for potential error parsing

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
    if not api_key and model != "Unsupported": # Check if API key is needed and provided
         raise APIError(f"❌ API Key is required for the {model} model but was not provided.")

    try:
        if model == "OpenAI":
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", # Consider making this configurable too
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()

        elif model == "Gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            # Include generationConfig for temperature and max_tokens
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    # You might want to add topP, topK etc. here if needed
                }
            }
            response = requests.post(url, headers=headers, json=data)

            # --- Start Gemini Error Handling ---
            if response.status_code != 200:
                try:
                    error_details = response.json()
                except json.JSONDecodeError:
                    error_details = response.text # Fallback if response is not JSON
                raise APIError(f"❌ Gemini API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()

            # Check if candidates key exists - it might be missing due to safety filters etc.
            if 'candidates' not in response_data:
                # Check for prompt feedback which often indicates blocking
                if 'promptFeedback' in response_data:
                     feedback = response_data['promptFeedback']
                     block_reason = feedback.get('blockReason', 'Unknown')
                     safety_ratings = feedback.get('safetyRatings', [])
                     details = f"Reason: {block_reason}, Safety Ratings: {safety_ratings}"
                     raise APIError(f"❌ Gemini response blocked. {details}. Please modify your prompt.")
                else:
                    # If no candidates and no feedback, it's an unexpected structure
                    raise APIError(f"❌ Gemini API Error: Unexpected response structure (missing 'candidates'). Response: {response_data}")

            # Check if candidates list is empty
            if not response_data['candidates']:
                 raise APIError("❌ Gemini API Error: Received empty 'candidates' list.")

            # Safely access the nested structure
            try:
                # Gemini Pro sometimes might not have 'content' if finishReason is SAFETY/OTHER
                if 'content' not in response_data['candidates'][0]:
                    finish_reason = response_data['candidates'][0].get('finishReason', 'UNKNOWN')
                    safety_ratings = response_data['candidates'][0].get('safetyRatings', [])
                    raise APIError(f"❌ Gemini response generation stopped. Finish Reason: {finish_reason}, Safety Ratings: {safety_ratings}")

                return response_data['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError) as e:
                raise APIError(f"❌ Error parsing Gemini response structure: {e}. Response: {response_data}")
            # --- End Gemini Error Handling ---


        elif model == "Claude":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01", # Keep updated if needed
                "content-type": "application/json"
            }
            data = {
                "model": "claude-3-opus-20240229", # Or other Claude models
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try:
                    error_details = response.json()
                except json.JSONDecodeError:
                    error_details = response.text
                raise APIError(f"❌ Claude API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                 # Check if content list is empty or structure is wrong
                 if not response_data.get("content") or not isinstance(response_data["content"], list) or not response_data["content"][0].get("text"):
                     raise APIError(f"❌ Claude API Error: Unexpected response structure. Response: {response_data}")
                 return response_data["content"][0]["text"]
            except (KeyError, IndexError) as e:
                 raise APIError(f"❌ Error parsing Claude response structure: {e}. Response: {response_data}")


        elif model == "Mistral":
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json" # Good practice
            }
            data = {
                "model": "mistral-medium", # Or other Mistral models
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try:
                    error_details = response.json()
                except json.JSONDecodeError:
                    error_details = response.text
                raise APIError(f"❌ Mistral API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                # Check structure
                if not response_data.get("choices") or not isinstance(response_data["choices"], list) or \
                   not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"):
                    raise APIError(f"❌ Mistral API Error: Unexpected response structure. Response: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise APIError(f"❌ Error parsing Mistral response structure: {e}. Response: {response_data}")


        elif model == "Groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "mixtral-8x7b-32768", # Or other Groq models
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                try:
                    error_details = response.json()
                except json.JSONDecodeError:
                    error_details = response.text
                raise APIError(f"❌ Groq API Error: Status Code {response.status_code}, Details: {error_details}")

            response_data = response.json()
            try:
                # Check structure (similar to OpenAI)
                if not response_data.get("choices") or not isinstance(response_data["choices"], list) or \
                   not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"):
                     raise APIError(f"❌ Groq API Error: Unexpected response structure. Response: {response_data}")
                return response_data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise APIError(f"❌ Error parsing Groq response structure: {e}. Response: {response_data}")


        else:
            # Use ValueError for fundamentally incorrect input like unsupported model
            raise ValueError("❌ Unsupported model selected.")

    # Catch potential network/request errors
    except requests.exceptions.RequestException as e:
        raise APIError(f"❌ Network error communicating with {model} API: {e}")
    # Catch OpenAI specific errors if using that library
    except openai.error.OpenAIError as e:
         raise APIError(f"❌ OpenAI API Error: {e}")
    # Catch other unexpected errors during the process
    except Exception as e:
        # Re-raise as APIError or a more specific custom error if desired
        # This helps distinguish API interaction issues from other code bugs
        raise APIError(f"❌ An unexpected error occurred in get_response for {model}: {type(e).__name__} - {e}")
