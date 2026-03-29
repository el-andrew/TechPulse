from __future__ import annotations

import logging
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "logs"
try:
    LOG_DIR.mkdir(exist_ok=True)
except OSError:
    # Bind-mounted directories inside containers may be owned by the host user.
    pass


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def get_source_logger(source_name: str, level: str = "INFO") -> logging.Logger:
    logger_name = f"tech_pulse.source.{slugify(source_name)}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        try:
            file_handler = logging.FileHandler(LOG_DIR / f"{slugify(source_name)}.log")
        except OSError as exc:
            logging.getLogger("tech_pulse.logging").warning(
                "Falling back to stdout logging for %s: %s",
                source_name,
                exc,
            )
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
            )
            logger.addHandler(file_handler)
    return logger


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
