import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH
from .routes import router
from .income_statement import router as income_statement_router

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
LOGGER = logging.getLogger("accounting.api.website")


def create_app() -> FastAPI:
    """Create the standalone website application."""
    debug = os.getenv("FASTAPI_ENV", "").lower() == "development"
    LOGGER.setLevel(logging.DEBUG if debug else logging.INFO)
    LOGGER.info("Creating Accounting web application debug=%s", debug)
    app = FastAPI(title="Accounting Web Interface", debug=debug)
    app.state.db_path = DEFAULT_DATABASE_PATH
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    LOGGER.info("Mounted web static files directory=%s", STATIC_DIR)
    app.include_router(router)
    app.include_router(income_statement_router)
    LOGGER.info("Registered Accounting web routes")
    return app


app = create_app()
