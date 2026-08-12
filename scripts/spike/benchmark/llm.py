"""Стадия LLM: стрим Ollama и проверка доступности."""

from __future__ import annotations

import json
import re
import sys
import time

import httpx


def strip_thinking(text: str) -> str:
    """Remove DeepSeek R1 reasoning blocks before TTS/display."""
    open_tag = "<" + "think" + ">"
    close_tag = "</" + "think" + ">"
    pattern = re.escape(open_tag) + r".*?" + re.escape(close_tag)
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def ollama_chat_stream(
    *,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.75,
    max_tokens: int = 220,
) -> tuple[str, float, float]:
    """Returns (full_text, ttft_ms, total_ms)."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": 8192,
        },
    }
    t0 = time.perf_counter()
    ttft_ms: float | None = None
    chunks: list[str] = []

    with httpx.Client(timeout=120.0) as client:
        with client.stream(
            "POST", f"{base_url}/api/generate", json=payload
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("response", "")
                if token and ttft_ms is None:
                    ttft_ms = (time.perf_counter() - t0) * 1000
                if token:
                    chunks.append(token)
                if data.get("done"):
                    break

    total_ms = (time.perf_counter() - t0) * 1000
    text = strip_thinking("".join(chunks))
    return text, ttft_ms or total_ms, total_ms


def check_ollama(base_url: str) -> None:
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ERROR: Ollama not reachable at {base_url}. Run: ollama serve\n  {exc}")
        sys.exit(1)
