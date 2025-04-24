# utils/llm_api.py

import requests
import json

def get_llm_response(prompt: str, model: str = "meta/llama3-8b-instruct") -> str:
    """
    Sends a prompt to the selected LLM model and returns the response.

    Parameters:
    - prompt: str : The user's input prompt to send to the LLM.
    - model: str : The model to use. Default is Meta's LLaMA 3 8B Instruct.

    Returns:
    - str: The response from the LLM.
    """
    url = "http://localhost:11434/api/generate"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response found.")
    except requests.RequestException as e:
        return f"Error communicating with LLM API: {e}"
