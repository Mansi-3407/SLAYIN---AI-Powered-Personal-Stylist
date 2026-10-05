"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        description="AI-Powered Personal Styling System",
        version="0.1.0",
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    logger.info("SLAYIN API initialised (env=%s)", settings.app_env)
    return app


app = create_app()
