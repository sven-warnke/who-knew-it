import requests
from pathlib import Path


def prompt_model(prompt: str) -> str:
    key_file = (
        Path(__file__).parent.parent.parent.parent / "api_keys" / "google-ai-studio.txt"
    )
    with open(key_file) as f:
        key = f.read()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"

    response = requests.post(
        url=url,
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
    )

    if response.status_code == 200:
        response_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        response.raise_for_status()

    return response_text
