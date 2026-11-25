"""Application factory. Run with: uvicorn belegfluss.main:create_app --factory"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from belegfluss import __version__
from belegfluss.auth import JwksKeySource, TokenVerifier
from belegfluss.db import make_session_factory
from belegfluss.errors import AppError, handle_app_error
from belegfluss.queue import DocumentQueue
from belegfluss.routes import documents, export, me
from belegfluss.schemas import HealthOut
from belegfluss.settings import Settings
from belegfluss.storage import BlobStore

# Log format without request bodies. Rule for all code: never log file names or invoice content.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app(settings: Settings | None = None, verifier: TokenVerifier | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Belegfluss API", version=__version__)

    app.state.settings = settings
    app.state.engine, app.state.session_factory = make_session_factory(
        settings.database_url, settings.database_entra_auth
    )
    app.state.blob_store = BlobStore.from_settings(settings)
    app.state.queue = DocumentQueue.from_settings(settings)
    app.state.verifier = verifier or TokenVerifier(
        JwksKeySource(settings.auth_jwks_url),
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        required_scope=settings.auth_required_scope,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_exception_handler(AppError, handle_app_error)

    @app.get("/health", response_model=HealthOut, tags=["health"])
    def health() -> HealthOut:
        return HealthOut(status="ok")

    app.include_router(me.router)
    app.include_router(documents.router)
    app.include_router(export.router)
    return app
