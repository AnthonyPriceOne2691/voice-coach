"""Remove DeepSeek R1 reasoning blocks before TTS/display (doc 20: empty result = hard fail)."""

import re

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_UNCLOSED_THINK = re.compile(r"<think>.*\Z", re.DOTALL)


def strip_thinking(text: str) -> str:
    """Strip <think>...</think> blocks, including an unclosed trailing block."""
    text = _THINK_BLOCK.sub("", text)
    text = _UNCLOSED_THINK.sub("", text)
    return text.strip()
