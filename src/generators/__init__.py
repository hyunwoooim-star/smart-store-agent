"""생성기 모듈"""
from .gap_reporter import GapReporter, OpportunityReport, OpportunityScore
from .templates import ReportTemplate, MarkdownTemplate, HTMLTemplate, JSONTemplate
from .detail_page_generator import (
    DetailPageGenerator,
    MockDetailPageGenerator,
    DetailPageResult,
    ProductInput,
    create_generator as create_detail_generator,
)

__all__ = [
    "GapReporter",
    "OpportunityReport",
    "OpportunityScore",
    "ReportTemplate",
    "MarkdownTemplate",
    "HTMLTemplate",
    "JSONTemplate",
    # Phase 10: 상세페이지 생성기
    "DetailPageGenerator",
    "MockDetailPageGenerator",
    "DetailPageResult",
    "ProductInput",
    "create_detail_generator",
]
