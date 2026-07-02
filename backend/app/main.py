"""FastAPI application entrypoint — wiring only."""

from fastapi import FastAPI

from app import __version__

app = FastAPI(
    title="Voice Interview Coach",
    version=__version__,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
