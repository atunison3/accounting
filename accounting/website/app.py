from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH
from .routes import router

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"


def create_app() -> FastAPI:
    """Create the standalone website application."""
    app = FastAPI(title="Accounting Web Interface")
    app.state.db_path = DEFAULT_DATABASE_PATH
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(router)
    return app


app = create_app()
