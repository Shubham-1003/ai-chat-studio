# utils/llm_api.py

import requests
import json

API_URL = "http://localhost:11434/api/generate"

def check_llm_server() -> bool:
    """Check if LLM server is up and responding."""
    try:
        r = requests.get("http://localhost:11434/")
        return r.status_code == 200
    except Exception:
        return False

def get_llm_response(prompt: str, model: str = "meta/llama3-8b-instruct") -> str:
    """
    Sends a prompt to the selected LLM model and returns the response.
    """
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response found.")
    except requests.RequestException as e:
        return f"❌ Error communicating with LLM API: {e}"
