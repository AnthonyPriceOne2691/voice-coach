"""FastAPI application entrypoint — wiring only."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from app import __version__
from app.api.routes_health import router as health_router
from app.api.routes_sessions import router as sessions_router
from app.api.routes_settings import router as settings_router
from app.api.routes_talks import router as talks_router
from app.api.routes_vocabulary import router as vocabulary_router
from app.api.ws_voice import ws_session
from app.config import get_settings
from app.container import Container, build_container

logger = logging.getLogger(__name__)


#: Сколько гашение ждёт незакрытые ws-сессии. Тот же порядок, что таймаут уборки
#: в `ws_voice`, плюс запас: здесь их может быть несколько.
SHUTDOWN_DRAIN_TIMEOUT_S = 10.0


async def _drain(tasks: set[asyncio.Task[None]]) -> None:
    """Дождаться уборок ws-сессий перед закрытием движка.

    Молча бросить их нельзя: незавершённая уборка оставляет соединение вне пула,
    SQLAlchemy добивает его отдельной задачей, и закрытие цикла ждёт её вечно.
    Таймаут здесь — предохранитель, а не политика: если уборка не уложилась,
    честнее отпустить гашение и сказать об этом, чем висеть.

    Отпустить — значит ОТМЕНИТЬ уборку и ДОЖДАТЬСЯ отмены, два шага (L90). Без
    отмены движок гасился при живой уборке, державшей соединение (поставка
    shutdown-leaks, E2); без ожидания отмена только помечена, а выход из
    `async with db.session()` сам требует `await`. Ожидание — без срока: выход
    процесса этих задач всё равно дождётся, срок лишь пустил бы `dispose()`
    вперёд размотки (то же в `SummaryService.aclose()`).
    """
    if not tasks:
        return
    _, pending = await asyncio.wait(set(tasks), timeout=SHUTDOWN_DRAIN_TIMEOUT_S)
    if not pending:
        return
    logger.warning("shutdown: %d ws cleanup(s) did not finish in time — cancelling", len(pending))
    for task in pending:
        task.cancel()
    await asyncio.wait(pending)


def create_app(container: Container | None = None) -> FastAPI:
    resolved = container or build_container(get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await resolved.db.create_all()
        # Уборки отключившихся ws-сессий регистрируются здесь: гасить движок
        # раньше, чем они дописали статус, значит рвать соединение на середине —
        # именно так прогон и висел (delivery diagnosis.md).
        app.state.live_ws_cleanups = set()
        yield
        await _drain(app.state.live_ws_cleanups)
        await resolved.summaries.aclose()
        if resolved.ollama is not None:
            await resolved.ollama.aclose()
        await resolved.db.dispose()

    application = FastAPI(
        title="Voice Interview Coach",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.container = resolved
    application.include_router(health_router)
    application.include_router(sessions_router)
    application.include_router(vocabulary_router)
    application.include_router(settings_router)
    application.include_router(talks_router)

    @application.websocket("/ws/session")
    async def websocket_session(websocket: WebSocket) -> None:
        await ws_session(websocket)

    return application


app = create_app()
