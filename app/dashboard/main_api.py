"""Client for the main OneHealthAI API."""

import os

import requests
import streamlit as st


API_BASE_URL = os.environ.get("ONEHEALTH_API_URL", os.environ.get("ONE_HEALTH_API_URL", "http://127.0.0.1:8000")).rstrip("/")


def api_get(
    endpoint: str,
    params: dict | None = None,
):
    try:
        response = requests.get(
            f"{API_BASE_URL}{endpoint}",
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        st.error(
            f"Errore di comunicazione con FastAPI: {exc}"
        )
        return None
