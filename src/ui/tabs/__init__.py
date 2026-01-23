"""Streamlit 탭 모듈"""
from .margin_tab import render as render_margin
from .scraping_tab import render as render_scraping
from .preflight_tab import render as render_preflight
from .review_tab import render as render_review
from .price_tab import render as render_price
from .oneclick_tab import render as render_oneclick

__all__ = [
    "render_margin",
    "render_scraping",
    "render_preflight",
    "render_review",
    "render_price",
    "render_oneclick",
]
