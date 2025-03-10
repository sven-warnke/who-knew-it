import requests
import streamlit as st


def _get_key() -> str:
    return st.secrets["google_ai_studio"]

def prompt_model(prompt: str) -> str:
    key = _get_key()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"

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
