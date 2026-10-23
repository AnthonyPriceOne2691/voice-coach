"""Проверка речи Антона (D3a.2): кандидат у модели — в префиксе того же разговора.

⚠ Почему просьба дописывается В КОНЕЦ истории, а не идёт своим промптом. У Ollama
один слот, и KV-кэш переиспользуется по общему префиксу. Отдельный системный промпт
проверки вытеснил бы из кэша системный промпт Генри с профилем и всю историю, и
следующий ход разговора снова платил бы полный prefill — 8.7 s до первого звука
(класс L78/L80). Здесь префикс — ровно то, что модель только что прочла и
сгенерировала: системный промпт, окно, реплика Антона, ответ Генри; дочитывается
одна просьба. Тот же клиент, та же модель и тот же `num_ctx` — иначе перезагрузка.
"""

from app.common.interfaces import ChatMessage, LlmClient
from app.orchestrator.tips import CANDIDATE_SCHEMA


def check_messages(history: list[ChatMessage], request: str) -> list[ChatMessage]:
    """История разговора как есть + просьба о проверке последним сообщением."""
    return [*history, {"role": "user", "content": request}]


async def ask_candidate(
    llm: LlmClient,
    messages: list[ChatMessage],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Сырой ответ модели; разбирает и решает `orchestrator.tips`, не этот модуль."""
    chunks: list[str] = []
    async for token in llm.stream_chat(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_schema=CANDIDATE_SCHEMA,
    ):
        chunks.append(token)
    return "".join(chunks)
