"""Streamlit 탭 모듈 (v4.1 - UI 통합)

v4.1 변경사항:
- 7탭 → 4탭 통합
- oneclick_tab, margin_tab, preflight_tab → sourcing_tab 통합
- scraping_tab, price_tab → 삭제 (백업: src_backup/tabs_v4.0/)
- settings_tab 신규 추가 (환율, 키워드 관리)
"""
from . import morning_tab
from . import sourcing_tab  # NEW: 통합 소싱 분석
from . import review_tab
from . import settings_tab  # NEW: 설정

__all__ = [
    "morning_tab",
    "sourcing_tab",
    "review_tab",
    "settings_tab",
]
