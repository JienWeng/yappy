from __future__ import annotations

import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiClient:
    """Thin wrapper around the google-genai SDK."""

    def __init__(self, model_name: str, temperature: float, max_output_tokens: int) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY environment variable is not set.")
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    def generate(self, prompt: str) -> str:
        """Generate text from a prompt. Returns the response text."""
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self._temperature,
                max_output_tokens=self._max_output_tokens,
            ),
        )
        text = response.text
        if not text:
            raise ValueError("Gemini returned an empty response.")
        return text.strip()
