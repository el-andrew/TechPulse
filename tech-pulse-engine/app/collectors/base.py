from __future__ import annotations

from abc import ABC, abstractmethod
from logging import Logger

from app.config.settings import Settings
from app.notify.logging import get_source_logger
from app.parsers.models import CollectedItem, SourceConfig


class BaseCollector(ABC):
    def __init__(self, settings: Settings, source: SourceConfig) -> None:
        self.settings = settings
        self.source = source
        self.logger: Logger = get_source_logger(source.name, settings.log_level)

    @abstractmethod
    def collect(self) -> list[CollectedItem]:
        raise NotImplementedError
