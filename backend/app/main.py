"""FastAPI application entrypoint — wiring only."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from app import __version__
from app.api.routes_health import router as health_router
from app.api.ws_voice import ws_session
from app.config import get_settings
from app.container import Container, build_container


def create_app(container: Container | None = None) -> FastAPI:
    resolved = container or build_container(get_settings())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if resolved.ollama is not None:
            await resolved.ollama.aclose()

    application = FastAPI(
        title="Voice Interview Coach",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.container = resolved
    application.include_router(health_router)

    @application.websocket("/ws/session")
    async def websocket_session(websocket: WebSocket) -> None:
        await ws_session(websocket)

    return application


app = create_app()
