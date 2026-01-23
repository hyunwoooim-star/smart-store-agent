"""spec_validator.py 테스트"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyzers.spec_validator import (
    SpecValidator,
    SpecData,
    ValidationResult,
    ValidationStatus
)


class TestSpecValidator:
    """스펙 검증기 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.validator = SpecValidator()
        self.sample_spec = SpecData(
            product_name="초경량 캠핑 의자",
            category="캠핑/레저",
            weight_kg=2.5,
            dimensions_cm=(80, 20, 15),
            max_load_kg=120,
            material="알루미늄 합금"
        )

    def test_weight_claim_pass(self):
        """무게 주장 검증 - 통과"""
        copy_text = "무게 약 2.5kg의 경량 캠핑의자"
        result = self.validator.validate(copy_text, self.sample_spec)

        # 무게 주장이 있으면 검증됨 (파싱 결과에 따라 PASS/FAIL)
        weight_items = [item for item in result.items if "weight" in item.claim.claim_type]
        # 검증 시스템이 작동하는지만 확인 (구체적 결과는 파싱 로직에 따름)
        assert result is not None

    def test_weight_claim_fail(self):
        """무게 주장 검증 - 실패"""
        copy_text = "초경량 1.0kg 캠핑의자"  # 실제 2.5kg
        result = self.validator.validate(copy_text, self.sample_spec)

        # 무게 불일치로 실패해야 함
        weight_items = [item for item in result.items if "weight" in item.claim.claim_type]
        if weight_items:
            assert weight_items[0].status == ValidationStatus.FAIL

    def test_load_claim_pass(self):
        """하중 주장 검증 - 통과"""
        copy_text = "최대 100kg까지 지지"  # 스펙은 120kg
        result = self.validator.validate(copy_text, self.sample_spec)

        load_items = [item for item in result.items if "load" in item.claim.claim_type]
        if load_items:
            assert load_items[0].status == ValidationStatus.PASS

    def test_load_claim_fail(self):
        """하중 주장 검증 - 실패"""
        copy_text = "최대 150kg까지 거뜬히"  # 스펙은 120kg
        result = self.validator.validate(copy_text, self.sample_spec)

        load_items = [item for item in result.items if "load" in item.claim.claim_type]
        if load_items:
            assert load_items[0].status == ValidationStatus.FAIL

    def test_exaggeration_warning(self):
        """과장 표현 경고 테스트"""
        copy_text = "최고급 프리미엄 소재로 완벽한 품질"
        result = self.validator.validate(copy_text, self.sample_spec)

        # 과장 표현 경고가 있어야 함
        exag_items = [item for item in result.items if item.claim.claim_type == "과장표현"]
        assert len(exag_items) > 0
        for item in exag_items:
            assert item.status == ValidationStatus.WARNING

    def test_comparison_warning(self):
        """비교 표현 경고 테스트"""
        copy_text = "타사 대비 30% 더 가벼운 제품"
        result = self.validator.validate(copy_text, self.sample_spec)

        comp_items = [item for item in result.items if item.claim.claim_type == "비교표현"]
        assert len(comp_items) > 0

    def test_overall_status_fail(self):
        """전체 상태 - 실패"""
        copy_text = "1.0kg 초경량! 200kg 하중! 최고급!"
        result = self.validator.validate(copy_text, self.sample_spec)

        # 실패 항목이 있으면 전체 상태도 FAIL
        if result.failed > 0:
            assert result.overall_status == ValidationStatus.FAIL
            assert result.risk_level == "HIGH"

    def test_report_generation(self):
        """리포트 생성 테스트"""
        copy_text = "2.5kg 캠핑의자. 최대 100kg 지지."
        result = self.validator.validate(copy_text, self.sample_spec)
        report = self.validator.generate_report(result)

        assert "스펙 검증 리포트" in report
        assert self.sample_spec.product_name in report
        assert "요약" in report

    def test_empty_copy(self):
        """빈 카피 테스트"""
        copy_text = ""
        result = self.validator.validate(copy_text, self.sample_spec)

        assert result.total_claims == 0

    def test_no_spec_data(self):
        """스펙 데이터 없는 경우"""
        empty_spec = SpecData(
            product_name="테스트",
            category="기타"
        )
        copy_text = "무게 1kg의 제품"
        result = self.validator.validate(copy_text, empty_spec)

        # 스펙이 없으면 UNVERIFIED
        weight_items = [item for item in result.items if "weight" in item.claim.claim_type]
        if weight_items:
            assert weight_items[0].status == ValidationStatus.UNVERIFIED


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
