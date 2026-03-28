from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


ROOT_DIR = Path(__file__).resolve().parents[2]


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_database(database_url: str) -> None:
    command.upgrade(build_alembic_config(database_url), "head")
