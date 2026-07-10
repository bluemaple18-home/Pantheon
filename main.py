from app.api.routes import router
from app.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https://(www\.)?mysticpantheon\.com|https://[a-z0-9-]+\.pages\.dev",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router, prefix="/api/v1")
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/personality", include_in_schema=False)
    def personality_page() -> FileResponse:
        return FileResponse(WEB_DIR / "personality.html")

    @app.get("/strategy", include_in_schema=False)
    def strategy_page() -> FileResponse:
        return FileResponse(WEB_DIR / "strategy.html")

    @app.get("/effects-demo", include_in_schema=False)
    def effects_demo_page() -> FileResponse:
        return FileResponse(WEB_DIR / "effects-demo.html")

    @app.get("/articles", include_in_schema=False)
    def articles_page() -> FileResponse:
        return FileResponse(WEB_DIR / "article.html")

    @app.get("/articles/intents/{intent}", include_in_schema=False)
    def article_intent_page(intent: str) -> FileResponse:
        return FileResponse(WEB_DIR / "article.html")

    @app.get("/articles/{product}", include_in_schema=False)
    def article_product_page(product: str) -> FileResponse:
        return FileResponse(WEB_DIR / "article.html")

    @app.get("/articles/{product}/{slug}", include_in_schema=False)
    def article_page(product: str, slug: str) -> FileResponse:
        return FileResponse(WEB_DIR / "article.html")

    @app.get("/article-admin", include_in_schema=False)
    def article_admin_page() -> FileResponse:
        return FileResponse(WEB_DIR / "article-admin.html")

    @app.get("/robots.txt", include_in_schema=False)
    def robots_txt() -> FileResponse:
        return FileResponse(WEB_DIR / "robots.txt")

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap_xml() -> FileResponse:
        return FileResponse(WEB_DIR / "sitemap.xml")

    return app


app = create_app()
