"""Utilities for configuring logging across the code-index tool."""
from __future__ import annotations

import logging
from typing import Dict, Iterable, Mapping, MutableMapping, Optional
from contextvars import ContextVar

__all__ = [
    "LoggingConfigurator",
    "push_logging_context",
    "reset_logging_context",
]

_CURRENT_FILE: ContextVar[Optional[str]] = ContextVar("code_index_current_file", default=None)
_CURRENT_LANGUAGE: ContextVar[Optional[str]] = ContextVar("code_index_current_language", default=None)

_NAME_TO_LEVEL: Mapping[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


class LoggingContextFilter(logging.Filter):
    """Injects contextual information (file, language) into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - standard logging signature
        record.current_file = _CURRENT_FILE.get() or "-"
        record.current_language = _CURRENT_LANGUAGE.get() or "-"
        return True


class LoggingConfigurator:
    """Central facility for logging configuration and contextual helpers."""

    _context_filter = LoggingContextFilter()

    @classmethod
    def ensure_context_filter(cls) -> None:
        """Ensure the global context filter is attached to the root logger and its handlers."""
        root = logging.getLogger()
        cls._attach_filter(root)
        for handler in root.handlers:
            cls._attach_filter_to_handler(handler)

    @classmethod
    def ensure_processing_logger(cls) -> None:
        """Create a dedicated handler for processing progress so it appears even in minimal mode."""
        logger = logging.getLogger("code_index.processing")
        logger.propagate = False
        cls._attach_filter(logger)

        for handler in logger.handlers:
            if getattr(handler, "_code_index_processing", False):
                handler.setLevel(logging.INFO)
                return

        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        setattr(handler, "_code_index_processing", True)
        cls._attach_filter_to_handler(handler)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    @classmethod
    def apply_component_levels(cls, component_levels: Mapping[str, object]) -> None:
        """Apply per-component logging levels, creating handlers when stricter than root."""
        if not component_levels:
            return

        normalized = cls.normalize_component_levels(component_levels)
        root_level = logging.getLogger().level

        for logger_name, level in normalized.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            cls._attach_filter(logger)
            if level < root_level:
                cls._ensure_component_handler(logger, level)

    @classmethod
    def normalize_component_levels(cls, component_levels: Mapping[str, object]) -> Dict[str, int]:
        """Return a dictionary with resolved numeric logging levels."""
        normalized: Dict[str, int] = {}
        for name, level in component_levels.items():
            normalized[name] = cls._coerce_level(level)
        return normalized

    @classmethod
    def _ensure_component_handler(cls, logger: logging.Logger, level: int) -> None:
        for handler in logger.handlers:
            if getattr(handler, "_code_index_component", False):
                handler.setLevel(level)
                cls._attach_filter_to_handler(handler)
                return

        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        setattr(handler, "_code_index_component", True)
        cls._attach_filter_to_handler(handler)
        logger.addHandler(handler)
        logger.propagate = False

    @classmethod
    def _coerce_level(cls, level: object) -> int:
        if isinstance(level, int):
            return level
        if isinstance(level, str):
            return _NAME_TO_LEVEL.get(level.upper(), logging.INFO)
        return logging.INFO

    @classmethod
    def _attach_filter(cls, logger: logging.Logger) -> None:
        if cls._context_filter not in getattr(logger, "filters", []):
            logger.addFilter(cls._context_filter)

    @classmethod
    def _attach_filter_to_handler(cls, handler: logging.Handler) -> None:
        if cls._context_filter not in getattr(handler, "filters", []):
            handler.addFilter(cls._context_filter)


def push_logging_context(file_path: Optional[str] = None, language: Optional[str] = None) -> Dict[str, ContextVar.Token]:
    """Push contextual information for downstream logging; returns tokens for reset."""
    tokens: Dict[str, ContextVar.Token] = {}
    if file_path is not None:
        tokens["file"] = _CURRENT_FILE.set(file_path)
    if language is not None:
        tokens["language"] = _CURRENT_LANGUAGE.set(language)
    return tokens


def reset_logging_context(tokens: Mapping[str, ContextVar.Token]) -> None:
    """Reset contextual information using tokens produced by ``push_logging_context``."""
    token = tokens.get("file")
    if token is not None:
        _CURRENT_FILE.reset(token)
    token = tokens.get("language")
    if token is not None:
        _CURRENT_LANGUAGE.reset(token)


def clear_logging_context() -> None:
    """Convenience helper to clear current logging context."""
    _CURRENT_FILE.set(None)
    _CURRENT_LANGUAGE.set(None)
