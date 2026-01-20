"""
logging.py - 로깅 설정
"""

import logging
from rich.logging import RichHandler


def setup_logger(name: str = "smart_store", level: int = logging.INFO) -> logging.Logger:
    """Rich 포맷 로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger
