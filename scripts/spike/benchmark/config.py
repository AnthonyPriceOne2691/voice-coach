"""Пути, адреса и образцы текста для бенчмарка."""

from pathlib import Path

# parents[3], а не [2]: файл уехал на уровень глубже (scripts/spike/benchmark/).
REPO_ROOT = Path(__file__).resolve().parents[3]
SPIKE_DIR = Path(__file__).resolve().parents[1]
RESULTS_PATH = SPIKE_DIR / "results.jsonl"


DEFAULT_OLLAMA = "http://127.0.0.1:11434"


DEFAULT_INTERVIEW_MODEL = "qwen2.5:14b-instruct"


DEFAULT_REVIEW_MODEL = "deepseek-r1:14b"


SAMPLE_USER_TEXT = (
    "I built an internal inbound reply pipeline for our link-building team. "
    "It uses separate queues for inbound messages and OpenAI API calls, "
    "with a human-in-the-loop step before anything gets sent automatically. "
    "We reduced the team from five people to one and cut the cycle time significantly."
)


SAMPLE_INTERVIEWER_PROMPT = """You are a supportive senior colleague running a mock technical interview.
The candidate just answered about their project. Ask ONE short follow-up question (max 2 sentences).
English only. No coaching or praise.

Candidate answer:
{transcript}

Your follow-up:"""


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)
