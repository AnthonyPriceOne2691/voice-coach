"""Просьба о проверке речи (D3a.2): префикс разговора тот же, схема ответа — своя."""

from app.config import REPO_ROOT
from app.knowledge.prompts import PromptLibrary
from app.orchestrator.tips import CANDIDATE_SCHEMA
from app.voice.language_check import ask_candidate, check_messages
from tests.fakes import FakeLlm


def test_request_goes_last_and_the_conversation_prefix_is_untouched() -> None:
    """C8: история уходит как есть, просьба — последним сообщением (кэш префикса цел)."""
    history = [
        {"role": "system", "content": "talk system"},
        {"role": "user", "content": "Yesterday I go to the office."},
        {"role": "assistant", "content": "Oh, how did it go?"},
    ]
    messages = check_messages(history, "check it")
    assert messages[:-1] == history
    assert messages[-1] == {"role": "user", "content": "check it"}
    assert len(history) == 3  # исходная история не тронута


async def test_candidate_is_asked_with_the_schema_and_collected_whole() -> None:
    """C8: проверка зовётся со схемой ответа и собирается целиком."""
    llm = FakeLlm(['{"kind": ', '"none", "said": "", "better": "", "why": ""}'])
    raw = await ask_candidate(
        llm, [{"role": "user", "content": "x"}], model="m", temperature=0.0, max_tokens=120
    )
    assert raw == '{"kind": "none", "said": "", "better": "", "why": ""}'
    assert llm.schemas == [CANDIDATE_SCHEMA]
    assert llm.last_num_ctx is None  # тот же num_ctx клиента, что у реплики


def test_request_quotes_the_utterance_verbatim() -> None:
    """C6: модель видит реплику дословно — иначе ей нечего цитировать."""
    prompts = PromptLibrary(REPO_ROOT / "data" / "prompts", REPO_ROOT / "data" / "knowledge")
    request = prompts.language_check("Yesterday I go to the office.")
    assert '"Yesterday I go to the office."' in request
    assert "{{" not in request
    assert request.startswith("[Request from the app, not from Anton.")
