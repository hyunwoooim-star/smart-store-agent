"""
naver_uploader.py - 네이버 커머스 API 업로더 (v4.0)

네이버 스마트스토어 상품 등록 자동화

주의: 실제 사용 시 네이버 커머스 API 인증 필요
- 네이버 커머스 API: https://developers.naver.com/docs/commerce/
- 인증: OAuth 2.0 기반
- 권한: 상품 등록/수정/삭제

현재 상태: Mock 모드 (API 연동 미완료)
"""

import os
import hmac
import hashlib
import base64
import time
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from src.domain.crawler_models import SourcingCandidate, DetailPageContent, UploadHistory


@dataclass
class NaverUploaderConfig:
    """네이버 업로더 설정"""
    client_id: str = ""
    client_secret: str = ""
    store_id: str = ""
    use_mock: bool = True               # Mock 모드


@dataclass
class UploadResult:
    """등록 결과"""
    success: bool
    product_id: str = ""
    product_url: str = ""
    error_message: str = ""
    raw_response: Dict[str, Any] = None


class NaverUploader:
    """네이버 커머스 API 업로더"""

    BASE_URL = "https://api.commerce.naver.com/external/v1"

    def __init__(self, config: NaverUploaderConfig = None):
        self.config = config or NaverUploaderConfig(
            client_id=os.getenv("NAVER_COMMERCE_CLIENT_ID", ""),
            client_secret=os.getenv("NAVER_COMMERCE_CLIENT_SECRET", ""),
            store_id=os.getenv("NAVER_STORE_ID", ""),
        )

        # 인증 정보 없으면 Mock 모드
        if not all([self.config.client_id, self.config.client_secret, self.config.store_id]):
            self.config.use_mock = True
            print("[NaverUploader] 인증 정보 없음. Mock 모드 활성화")

    async def upload_product(
        self,
        candidate: SourcingCandidate,
        content: DetailPageContent
    ) -> UploadResult:
        """상품 등록

        Args:
            candidate: 소싱 후보
            content: 상세페이지 콘텐츠

        Returns:
            UploadResult: 등록 결과
        """
        if self.config.use_mock:
            return await self._mock_upload(candidate, content)
        else:
            return await self._real_upload(candidate, content)

    async def _mock_upload(
        self,
        candidate: SourcingCandidate,
        content: DetailPageContent
    ) -> UploadResult:
        """Mock 등록 (테스트용)

        Args:
            candidate: 소싱 후보
            content: 상세페이지 콘텐츠

        Returns:
            UploadResult: Mock 등록 결과
        """
        import random
        import asyncio

        # 등록 시뮬레이션 (1~3초 대기)
        await asyncio.sleep(random.uniform(1, 3))

        # 90% 성공률 시뮬레이션
        if random.random() < 0.9:
            product_id = f"MOCK_{int(time.time())}_{random.randint(1000, 9999)}"
            return UploadResult(
                success=True,
                product_id=product_id,
                product_url=f"https://smartstore.naver.com/{self.config.store_id or 'mystore'}/products/{product_id}",
                raw_response={
                    "status": "success",
                    "productId": product_id,
                    "message": "Mock 등록 완료",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return UploadResult(
                success=False,
                error_message="Mock 등록 실패: 시뮬레이션 오류",
                raw_response={
                    "status": "error",
                    "message": "Random failure simulation",
                }
            )

    async def _real_upload(
        self,
        candidate: SourcingCandidate,
        content: DetailPageContent
    ) -> UploadResult:
        """실제 API 등록

        Args:
            candidate: 소싱 후보
            content: 상세페이지 콘텐츠

        Returns:
            UploadResult: 실제 등록 결과
        """
        try:
            import aiohttp

            # 1. 인증 헤더 생성
            headers = self._generate_auth_headers("/products")

            # 2. 이미지 업로드 (먼저 수행)
            image_urls = await self._upload_images(candidate.source_images)

            # 3. 상품 등록 페이로드 생성
            payload = self._build_product_payload(candidate, content, image_urls)

            # 4. API 호출
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/products",
                    headers=headers,
                    json=payload
                ) as response:
                    data = await response.json()

                    if response.status == 200:
                        product_id = data.get("productId", "")
                        return UploadResult(
                            success=True,
                            product_id=product_id,
                            product_url=f"https://smartstore.naver.com/{self.config.store_id}/products/{product_id}",
                            raw_response=data
                        )
                    else:
                        return UploadResult(
                            success=False,
                            error_message=data.get("message", "Unknown error"),
                            raw_response=data
                        )

        except ImportError:
            print("[NaverUploader] aiohttp 패키지 없음")
            return UploadResult(
                success=False,
                error_message="aiohttp 패키지가 필요합니다."
            )
        except Exception as e:
            print(f"[NaverUploader] 등록 실패: {e}")
            return UploadResult(
                success=False,
                error_message=str(e)
            )

    def _generate_auth_headers(self, path: str) -> Dict[str, str]:
        """네이버 커머스 API 인증 헤더 생성

        Args:
            path: API 경로

        Returns:
            Dict: 인증 헤더
        """
        timestamp = str(int(time.time() * 1000))
        method = "POST"

        # HMAC 서명 생성
        message = f"{timestamp}.{method}.{path}"
        signature = base64.b64encode(
            hmac.new(
                self.config.client_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')

        return {
            "Content-Type": "application/json",
            "X-Naver-Client-Id": self.config.client_id,
            "X-Naver-Client-Secret": self.config.client_secret,
            "X-NCP-APIGW-Timestamp": timestamp,
            "X-NCP-APIGW-Signature-V2": signature,
        }

    def _build_product_payload(
        self,
        candidate: SourcingCandidate,
        content: DetailPageContent,
        image_urls: List[str]
    ) -> Dict[str, Any]:
        """상품 등록 페이로드 생성

        Args:
            candidate: 소싱 후보
            content: 상세페이지 콘텐츠
            image_urls: 업로드된 이미지 URL 리스트

        Returns:
            Dict: API 페이로드
        """
        return {
            "originProduct": {
                "statusType": "SALE",
                "saleType": "NEW",
                "leafCategoryId": "",  # 카테고리 ID (실제 구현 시 매핑 필요)
                "name": content.title or candidate.title_kr,
                "detailContent": content.to_html(),
                "images": {
                    "representativeImage": {
                        "url": image_urls[0] if image_urls else ""
                    },
                    "optionalImages": [
                        {"url": url} for url in image_urls[1:5]
                    ] if len(image_urls) > 1 else []
                },
                "salePrice": candidate.recommended_price,
                "stockQuantity": 999,
                "deliveryInfo": {
                    "deliveryType": "DELIVERY",
                    "deliveryAttributeType": "NORMAL",
                    "deliveryFee": {
                        "deliveryFeeType": "FREE",
                        "baseFee": 0
                    },
                    "claimDeliveryInfo": {
                        "returnDeliveryFee": 3000,
                        "exchangeDeliveryFee": 6000
                    }
                },
                "detailAttribute": {
                    "naverShoppingSearchInfo": {
                        "manufacturerName": "해외",
                        "brandName": "자체제작",
                        "modelName": content.title[:50] if content.title else candidate.title_kr[:50]
                    },
                    "afterServiceInfo": {
                        "afterServiceTelephoneNumber": "010-0000-0000",
                        "afterServiceGuideContent": "교환/반품은 상품 수령 후 7일 이내 가능합니다."
                    },
                    "originAreaInfo": {
                        "originAreaCode": "03",  # 중국
                        "content": "중국 (국내 검수 후 발송)"
                    },
                    "seoInfo": {
                        "pageTitle": content.title,
                        "metaDescription": content.solution[:150] if content.solution else "",
                        "sellerTags": content.seo_keywords[:10]
                    }
                }
            }
        }

    async def _upload_images(self, image_urls: List[str]) -> List[str]:
        """이미지 업로드 (네이버 이미지 호스팅)

        Args:
            image_urls: 원본 이미지 URL 리스트

        Returns:
            List[str]: 업로드된 이미지 URL 리스트
        """
        # 실제 구현 시 네이버 이미지 업로드 API 사용
        # 현재는 원본 URL 그대로 반환 (Mock)
        return image_urls[:5]  # 최대 5개

    def upload_sync(
        self,
        candidate: SourcingCandidate,
        content: DetailPageContent
    ) -> UploadResult:
        """동기 버전 등록 (Streamlit용)

        Args:
            candidate: 소싱 후보
            content: 상세페이지 콘텐츠

        Returns:
            UploadResult: 등록 결과
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.upload_product(candidate, content)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.upload_product(candidate, content))
        except RuntimeError:
            return asyncio.run(self.upload_product(candidate, content))
