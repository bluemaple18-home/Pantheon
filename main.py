from app.api.routes import router
from app.core.config import settings
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path


WEB_DIR = Path(__file__).parent / "app" / "web"


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Pure Python modular divination engine.",
    )
    app.include_router(router, prefix="/api/v1")
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/personality", include_in_schema=False)
    def personality_page() -> FileResponse:
        return FileResponse(WEB_DIR / "personality.html")

    return app


app = create_app()
