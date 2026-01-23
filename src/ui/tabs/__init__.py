"""Streamlit 탭 모듈 (v4.0)"""
from . import margin_tab
from . import scraping_tab
from . import preflight_tab
from . import review_tab
from . import price_tab
from . import oneclick_tab
from . import morning_tab  # v4.0 NEW!

__all__ = [
    "margin_tab",
    "scraping_tab",
    "preflight_tab",
    "review_tab",
    "price_tab",
    "oneclick_tab",
    "morning_tab",
]
