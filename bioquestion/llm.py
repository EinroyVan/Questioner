"""Google Gemini API client with JSON structured output."""

from __future__ import annotations

import json
import os
import re
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from bioquestion import load_project_env

load_project_env()

T = TypeVar("T", bound=BaseModel)

_JSON_RETRY_HINT = (
    "\n\n[Important] Previous output was invalid JSON. Reply again with: "
    "1) strictly valid JSON; 2) escaped double quotes inside strings; "
    "3) no trailing commas; 4) source_quote max 200 characters."
)


def _extract_json_blob(text: str) -> str:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        return fence_match.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _parse_json_text(text: str) -> dict | list:
    blob = _extract_json_blob(text)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        try:
            import json_repair

            return json_repair.loads(blob)
        except Exception as exc:
            raise json.JSONDecodeError(
                f"Could not parse model JSON output: {exc}",
                blob,
                0,
            ) from exc


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self.model = model or os.getenv("GOOGLE_MODEL", "gemini-3.5-flash")
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not configured. Copy .env.example to .env and set your key, "
                "or set the environment variable."
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        return response.text or "{}"

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
        *,
        max_retries: int = 2,
    ) -> T:
        last_error: Exception | None = None
        prompt = user_prompt

        for attempt in range(max_retries + 1):
            try:
                content = self._generate(system_prompt, prompt)
                data = _parse_json_text(content)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                if attempt < max_retries:
                    prompt = user_prompt + _JSON_RETRY_HINT
                continue

        raise RuntimeError(f"Model JSON could not be parsed or validated (retried {max_retries} times)") from last_error
