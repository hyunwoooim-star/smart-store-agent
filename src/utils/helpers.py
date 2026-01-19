"""
helpers.py - 헬퍼 유틸리티 (v3.1)
"""

from typing import Optional


def format_currency(amount: int, symbol: str = "원") -> str:
    """통화 포맷"""
    return f"{amount:,}{symbol}"


def format_percent(value: float, decimals: int = 1) -> str:
    """퍼센트 포맷"""
    return f"{value:.{decimals}f}%"


def format_weight(kg: float) -> str:
    """무게 포맷"""
    return f"{kg:.2f}kg"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """안전한 나눗셈"""
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_val: float, max_val: float) -> float:
    """값을 범위 내로 제한"""
    return max(min_val, min(value, max_val))


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """텍스트 자르기"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
