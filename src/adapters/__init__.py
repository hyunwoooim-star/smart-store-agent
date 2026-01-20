"""어댑터 모듈 (v3.3)

외부 시스템과의 연동을 담당
- 1688 스크래핑
- Gemini API
- Supabase
"""

from .alibaba_scraper import (
    AlibabaScraper,
    MockAlibabaScraper,
    ScrapedProduct,
    scrape_1688,
)

__all__ = [
    "AlibabaScraper",
    "MockAlibabaScraper",
    "ScrapedProduct",
    "scrape_1688",
]
