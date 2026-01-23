"""
crawler_models.py - Night Crawler v4.0 도메인 모델

소싱 자동화 시스템용 데이터 클래스
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class CandidateStatus(Enum):
    """소싱 후보 상태"""
    PENDING = "pending"         # 검토 대기
    APPROVED = "approved"       # 승인됨
    REJECTED = "rejected"       # 반려됨
    UPLOADED = "uploaded"       # 등록 완료
    FAILED = "failed"           # 등록 실패


class CrawlRiskLevel(Enum):
    """크롤링 리스크 레벨"""
    SAFE = "safe"               # 안전 (리스크 없음)
    WARNING = "warning"         # 주의 (KC인증 등)
    DANGER = "danger"           # 위험 (브랜드/금지품목)


@dataclass
class SourcingKeyword:
    """소싱 키워드"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    keyword: str = ""
    category: str = ""
    is_active: bool = True
    priority: int = 5           # 1(높음) ~ 10(낮음)
    last_crawled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "keyword": self.keyword,
            "category": self.category,
            "is_active": self.is_active,
            "priority": self.priority,
            "last_crawled_at": self.last_crawled_at.isoformat() if self.last_crawled_at else None,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourcingKeyword":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            keyword=data.get("keyword", ""),
            category=data.get("category", ""),
            is_active=data.get("is_active", True),
            priority=data.get("priority", 5),
            last_crawled_at=datetime.fromisoformat(data["last_crawled_at"]) if data.get("last_crawled_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )


@dataclass
class SourcingCandidate:
    """소싱 후보 상품"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 원본 정보
    source_url: str = ""
    source_title: str = ""              # 원본 제목 (중국어)
    source_price_cny: float = 0.0       # 원가 (위안)
    source_images: List[str] = field(default_factory=list)
    source_shop_name: str = ""
    source_shop_rating: float = 0.0
    source_sales_count: int = 0

    # AI 분석 결과
    title_kr: str = ""                  # AI 번역 제목
    estimated_cost_krw: int = 0         # 예상 총원가 (원)
    estimated_margin_rate: float = 0.0  # 예상 마진율 (%)
    recommended_price: int = 0          # 추천 판매가
    breakeven_price: int = 0            # 손익분기 판매가
    risk_level: CrawlRiskLevel = CrawlRiskLevel.SAFE
    risk_reasons: List[str] = field(default_factory=list)

    # 경쟁사 분석
    naver_min_price: int = 0            # 네이버 최저가
    naver_avg_price: int = 0            # 네이버 평균가
    naver_max_price: int = 0            # 네이버 최고가
    competitor_count: int = 0           # 경쟁사 수

    # 상태 관리
    status: CandidateStatus = CandidateStatus.PENDING
    approved_at: Optional[datetime] = None
    rejected_reason: str = ""

    # 등록 정보
    naver_product_id: str = ""
    naver_product_url: str = ""
    uploaded_at: Optional[datetime] = None

    # 메타
    keyword_id: str = ""
    keyword: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "source_price_cny": self.source_price_cny,
            "source_images": self.source_images,
            "source_shop_name": self.source_shop_name,
            "source_shop_rating": self.source_shop_rating,
            "source_sales_count": self.source_sales_count,
            "title_kr": self.title_kr,
            "estimated_cost_krw": self.estimated_cost_krw,
            "estimated_margin_rate": self.estimated_margin_rate,
            "recommended_price": self.recommended_price,
            "breakeven_price": self.breakeven_price,
            "risk_level": self.risk_level.value,
            "risk_reasons": self.risk_reasons,
            "naver_min_price": self.naver_min_price,
            "naver_avg_price": self.naver_avg_price,
            "naver_max_price": self.naver_max_price,
            "competitor_count": self.competitor_count,
            "status": self.status.value,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_reason": self.rejected_reason,
            "naver_product_id": self.naver_product_id,
            "naver_product_url": self.naver_product_url,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "keyword_id": self.keyword_id,
            "keyword": self.keyword,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourcingCandidate":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_url=data.get("source_url", ""),
            source_title=data.get("source_title", ""),
            source_price_cny=data.get("source_price_cny", 0.0),
            source_images=data.get("source_images", []),
            source_shop_name=data.get("source_shop_name", ""),
            source_shop_rating=data.get("source_shop_rating", 0.0),
            source_sales_count=data.get("source_sales_count", 0),
            title_kr=data.get("title_kr", ""),
            estimated_cost_krw=data.get("estimated_cost_krw", 0),
            estimated_margin_rate=data.get("estimated_margin_rate", 0.0),
            recommended_price=data.get("recommended_price", 0),
            breakeven_price=data.get("breakeven_price", 0),
            risk_level=CrawlRiskLevel(data.get("risk_level", "safe")),
            risk_reasons=data.get("risk_reasons", []),
            naver_min_price=data.get("naver_min_price", 0),
            naver_avg_price=data.get("naver_avg_price", 0),
            naver_max_price=data.get("naver_max_price", 0),
            competitor_count=data.get("competitor_count", 0),
            status=CandidateStatus(data.get("status", "pending")),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            rejected_reason=data.get("rejected_reason", ""),
            naver_product_id=data.get("naver_product_id", ""),
            naver_product_url=data.get("naver_product_url", ""),
            uploaded_at=datetime.fromisoformat(data["uploaded_at"]) if data.get("uploaded_at") else None,
            keyword_id=data.get("keyword_id", ""),
            keyword=data.get("keyword", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class UploadHistory:
    """등록 히스토리"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    candidate_id: str = ""
    platform: str = "naver"             # naver/coupang
    status: str = "pending"             # success/failed/pending
    response_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "platform": self.platform,
            "status": self.status,
            "response_data": self.response_data,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UploadHistory":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            candidate_id=data.get("candidate_id", ""),
            platform=data.get("platform", "naver"),
            status=data.get("status", "pending"),
            response_data=data.get("response_data", {}),
            error_message=data.get("error_message", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )


@dataclass
class CrawlStats:
    """크롤링 통계"""
    total_keywords: int = 0
    crawled_keywords: int = 0
    total_products_found: int = 0
    filtered_products: int = 0
    saved_candidates: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    @property
    def duration_minutes(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_keywords": self.total_keywords,
            "crawled_keywords": self.crawled_keywords,
            "total_products_found": self.total_products_found,
            "filtered_products": self.filtered_products,
            "saved_candidates": self.saved_candidates,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "errors": self.errors
        }


@dataclass
class DetailPageContent:
    """상세페이지 콘텐츠 (PAS 프레임워크)"""
    title: str = ""                     # 상품 제목
    headline: str = ""                  # 헤드라인 (후킹)

    # PAS 프레임워크
    problem: str = ""                   # 문제점
    agitation: str = ""                 # 자극
    solution: str = ""                  # 해결책

    # 상세 내용
    features: List[str] = field(default_factory=list)       # 특징/장점
    specs: Dict[str, str] = field(default_factory=dict)     # 스펙 테이블
    faq: List[Dict[str, str]] = field(default_factory=list) # FAQ

    # 메타 정보
    seo_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "headline": self.headline,
            "problem": self.problem,
            "agitation": self.agitation,
            "solution": self.solution,
            "features": self.features,
            "specs": self.specs,
            "faq": self.faq,
            "seo_keywords": self.seo_keywords
        }

    def to_html(self) -> str:
        """네이버 상세페이지용 HTML 생성"""
        html_parts = []

        # 헤드라인
        if self.headline:
            html_parts.append(f'<div style="text-align:center;font-size:24px;font-weight:bold;margin:20px 0;">{self.headline}</div>')

        # PAS 섹션
        if self.problem:
            html_parts.append(f'<div style="background:#fff3cd;padding:15px;margin:10px 0;border-radius:8px;"><strong>이런 고민 있으시죠?</strong><br>{self.problem}</div>')

        if self.agitation:
            html_parts.append(f'<div style="background:#f8d7da;padding:15px;margin:10px 0;border-radius:8px;">{self.agitation}</div>')

        if self.solution:
            html_parts.append(f'<div style="background:#d4edda;padding:15px;margin:10px 0;border-radius:8px;"><strong>해결책</strong><br>{self.solution}</div>')

        # 특징
        if self.features:
            features_html = '<ul style="padding-left:20px;">'
            for feature in self.features:
                features_html += f'<li style="margin:8px 0;">{feature}</li>'
            features_html += '</ul>'
            html_parts.append(f'<div style="margin:20px 0;"><strong>주요 특징</strong>{features_html}</div>')

        # 스펙 테이블
        if self.specs:
            specs_html = '<table style="width:100%;border-collapse:collapse;margin:10px 0;">'
            for key, value in self.specs.items():
                specs_html += f'<tr><td style="border:1px solid #ddd;padding:8px;background:#f5f5f5;width:30%;">{key}</td><td style="border:1px solid #ddd;padding:8px;">{value}</td></tr>'
            specs_html += '</table>'
            html_parts.append(specs_html)

        # FAQ
        if self.faq:
            faq_html = '<div style="margin:20px 0;"><strong>자주 묻는 질문</strong>'
            for item in self.faq:
                faq_html += f'<div style="margin:10px 0;padding:10px;background:#f9f9f9;border-radius:5px;"><strong>Q. {item.get("q", "")}</strong><br>A. {item.get("a", "")}</div>'
            faq_html += '</div>'
            html_parts.append(faq_html)

        return '\n'.join(html_parts)
