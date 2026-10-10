"""JSON extraction, markdown cleanup, and single-retry repair logic."""
import json
import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def extract_json_from_text(raw_text: str) -> dict[str, Any]:
    """Extract first valid JSON object from LLM response text."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response string received from LLM.")

    text = raw_text.strip()

    # 1. Try markdown code blocks
    block_match = JSON_BLOCK_PATTERN.search(text)
    if block_match:
        try:
            return json.loads(block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 2. Try direct json.loads
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Find outermost curly braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Extracted string failed JSON parsing: {exc}") from exc

    raise ValueError("No JSON object structure found in response text.")


def parse_and_validate(raw_text: str, schema_cls: Type[T] | None = None) -> tuple[dict[str, Any], T | None]:
    """Parse JSON and validate against Pydantic schema if provided."""
    data = extract_json_from_text(raw_text)
    if schema_cls:
        validated = schema_cls.model_validate(data)
        return data, validated
    return data, None
