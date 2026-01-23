"""
test_preflight_checker.py - PreFlightChecker 단위 테스트 (Phase 6-2)

테스트 항목:
1. 의료/건강 효능 주장 탐지
2. 최상급/과장 표현 탐지
3. KC 인증 필요 제품 탐지
4. 지식재산권 침해 탐지
5. 전기/배터리 제품 탐지 (Gemini CTO 피드백)
"""

import pytest
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzers.preflight_check import (
    PreFlightChecker,
    ViolationType,
    preflight_check,
)


class TestMedicalClaims:
    """의료/건강 효능 주장 탐지"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_cancer_prevention_claim(self):
        """암 예방 주장 탐지"""
        result = self.checker.check("암 예방에 탁월한 효과!")
        assert not result.passed
        assert any(v.type == ViolationType.MEDICAL_CLAIM for v in result.violations)

    def test_diabetes_treatment_claim(self):
        """당뇨 치료 주장 탐지"""
        result = self.checker.check("당뇨 개선에 효과적인 건강식품")
        assert not result.passed
        assert any(v.type == ViolationType.MEDICAL_CLAIM for v in result.violations)

    def test_weight_loss_claim(self):
        """체중 감량 효능 탐지"""
        result = self.checker.check("살빠지는 다이어트 효과 100%")
        assert not result.passed
        violations = [v for v in result.violations if v.type == ViolationType.MEDICAL_CLAIM]
        assert len(violations) >= 1

    def test_immune_boost_claim(self):
        """면역력 강화 주장 탐지"""
        result = self.checker.check("면역력 강화에 좋은 영양제")
        assert not result.passed
        assert any(v.type == ViolationType.MEDICAL_CLAIM for v in result.violations)

    def test_safe_health_description(self):
        """안전한 건강 관련 표현"""
        result = self.checker.check("건강한 생활 습관 도움")
        # 구체적 효능 주장 없으면 통과
        medical_violations = [v for v in result.violations if v.type == ViolationType.MEDICAL_CLAIM]
        assert len(medical_violations) == 0


class TestSuperlativeExpressions:
    """최상급/과장 표현 탐지"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_best_claim(self):
        """최고 표현 탐지"""
        result = self.checker.check("최고의 품질!")
        assert not result.passed
        assert any(v.type == ViolationType.SUPERLATIVE for v in result.violations)

    def test_first_claim(self):
        """최초 표현 탐지"""
        result = self.checker.check("세계 최초 개발!")
        assert not result.passed
        assert any(v.type == ViolationType.SUPERLATIVE for v in result.violations)

    def test_number_one_claim(self):
        """1위 표현 탐지"""
        result = self.checker.check("판매량 1위 상품")
        assert not result.passed
        assert any(v.type == ViolationType.SUPERLATIVE for v in result.violations)

    def test_perfect_claim(self):
        """완벽 표현 탐지"""
        result = self.checker.check("완벽한 마감 처리")
        assert not result.passed
        assert any(v.type == ViolationType.SUPERLATIVE for v in result.violations)

    def test_safe_quality_description(self):
        """안전한 품질 표현"""
        result = self.checker.check("고품질 소재 사용")
        superlative_violations = [v for v in result.violations if v.type == ViolationType.SUPERLATIVE]
        assert len(superlative_violations) == 0


class TestGuaranteeExpressions:
    """효과 보장 표현 탐지"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_100_percent_guarantee(self):
        """100% 보장 탐지"""
        result = self.checker.check("100% 효과 보장!")
        assert not result.passed
        assert any(v.type == ViolationType.GUARANTEE for v in result.violations)

    def test_unconditional_effect(self):
        """무조건 효과 탐지"""
        result = self.checker.check("무조건 효과 있습니다")
        assert not result.passed
        assert any(v.type == ViolationType.GUARANTEE for v in result.violations)

    def test_money_guarantee(self):
        """수익 보장 탐지"""
        result = self.checker.check("수익 보장 확실합니다")
        assert not result.passed
        assert any(v.type == ViolationType.GUARANTEE for v in result.violations)


class TestKCCertificationProducts:
    """KC 인증 필요 제품 탐지 (아동용)"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_children_toy(self):
        """아동용 완구 탐지"""
        result = self.checker.check("어린이 장난감 세트")
        assert not result.passed
        assert any(v.type == ViolationType.CHILDREN_PRODUCT for v in result.violations)

    def test_baby_product(self):
        """유아용 제품 탐지"""
        result = self.checker.check("아기용 로션 크림")
        assert not result.passed
        assert any(v.type == ViolationType.CHILDREN_PRODUCT for v in result.violations)

    def test_kids_food(self):
        """아동용 식품 탐지"""
        result = self.checker.check("어린이 간식 세트")
        assert not result.passed
        assert any(v.type == ViolationType.CHILDREN_PRODUCT for v in result.violations)

    def test_age_indication(self):
        """사용 연령 표시 탐지"""
        result = self.checker.check("36개월 이상 사용 가능")
        assert not result.passed
        assert any(v.type == ViolationType.CHILDREN_PRODUCT for v in result.violations)


class TestElectricalProducts:
    """전기/전자 제품 탐지 (Gemini CTO 피드백)"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_battery_product(self):
        """배터리 제품 탐지"""
        result = self.checker.check("리튬 배터리 내장")
        assert not result.passed
        assert any(v.type == ViolationType.ELECTRICAL_PRODUCT for v in result.violations)

    def test_rechargeable_product(self):
        """충전식 제품 탐지"""
        result = self.checker.check("USB 충전식 LED 랜턴")
        assert not result.passed
        electrical = [v for v in result.violations if v.type == ViolationType.ELECTRICAL_PRODUCT]
        assert len(electrical) >= 1

    def test_power_adapter(self):
        """전원 어댑터 탐지"""
        result = self.checker.check("220V 어댑터 포함")
        assert not result.passed
        assert any(v.type == ViolationType.ELECTRICAL_PRODUCT for v in result.violations)

    def test_led_lighting(self):
        """LED 조명 탐지"""
        result = self.checker.check("LED 전구 세트")
        assert not result.passed
        assert any(v.type == ViolationType.ELECTRICAL_PRODUCT for v in result.violations)

    def test_bluetooth_device(self):
        """블루투스 기기 탐지"""
        result = self.checker.check("블루투스 무선 이어폰")
        assert not result.passed
        assert any(v.type == ViolationType.ELECTRICAL_PRODUCT for v in result.violations)

    def test_heater_product(self):
        """발열 제품 탐지"""
        result = self.checker.check("온열 찜질팩 히터")
        assert not result.passed
        assert any(v.type == ViolationType.ELECTRICAL_PRODUCT for v in result.violations)


class TestIntellectualProperty:
    """지식재산권 침해 탐지"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_disney_character(self):
        """디즈니 캐릭터 탐지"""
        result = self.checker.check("디즈니 미키마우스 인형")
        assert not result.passed
        assert any(v.type == ViolationType.INTELLECTUAL_PROPERTY for v in result.violations)

    def test_sanrio_character(self):
        """산리오 캐릭터 탐지"""
        result = self.checker.check("헬로키티 파우치")
        assert not result.passed
        assert any(v.type == ViolationType.INTELLECTUAL_PROPERTY for v in result.violations)

    def test_kakao_character(self):
        """카카오 캐릭터 탐지"""
        result = self.checker.check("라이언 인형 쿠션")
        assert not result.passed
        assert any(v.type == ViolationType.INTELLECTUAL_PROPERTY for v in result.violations)

    def test_replica_keyword(self):
        """레플리카 키워드 탐지"""
        result = self.checker.check("레플리카 시계")
        assert not result.passed
        assert any(v.type == ViolationType.INTELLECTUAL_PROPERTY for v in result.violations)


class TestMedicalDevice:
    """의료기기 오인 표현 탐지"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_pain_relief_claim(self):
        """통증 완화 주장 탐지"""
        result = self.checker.check("어깨통증 완화에 효과적")
        assert not result.passed
        assert any(v.type == ViolationType.MEDICAL_DEVICE for v in result.violations)

    def test_posture_correction(self):
        """자세 교정 주장 탐지"""
        result = self.checker.check("거북목 교정 쿠션")
        assert not result.passed
        assert any(v.type == ViolationType.MEDICAL_DEVICE for v in result.violations)

    def test_blood_circulation(self):
        """혈액순환 개선 탐지"""
        result = self.checker.check("혈액순환 개선에 도움")
        assert not result.passed
        assert any(v.type == ViolationType.MEDICAL_DEVICE for v in result.violations)

    def test_safe_comfort_description(self):
        """안전한 편안함 표현"""
        result = self.checker.check("편안한 사용감의 쿠션")
        medical_device_violations = [v for v in result.violations if v.type == ViolationType.MEDICAL_DEVICE]
        assert len(medical_device_violations) == 0


class TestTrademarkViolations:
    """상표권 침해 탐지"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_luxury_brand(self):
        """명품 브랜드 언급 탐지"""
        result = self.checker.check("샤넬 스타일 가방")
        assert not result.passed
        assert any(v.type == ViolationType.TRADEMARK for v in result.violations)

    def test_sports_brand(self):
        """스포츠 브랜드 언급 탐지"""
        result = self.checker.check("나이키 스타일 운동화")
        assert not result.passed
        assert any(v.type == ViolationType.TRADEMARK for v in result.violations)

    def test_not_genuine_label(self):
        """정품 아님 표시 탐지"""
        result = self.checker.check("정품 아님 주의")
        assert not result.passed
        assert any(v.type == ViolationType.TRADEMARK for v in result.violations)


class TestNaverProhibitedWords:
    """네이버 금지 키워드 탐지"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_competitor_platform(self):
        """경쟁 플랫폼 언급 탐지"""
        result = self.checker.check("쿠팡보다 저렴해요")
        assert not result.passed
        assert any(v.type == ViolationType.PROHIBITED_WORD for v in result.violations)

    def test_social_media(self):
        """SNS 언급 탐지"""
        result = self.checker.check("인스타그램에서 인기")
        assert not result.passed
        assert any(v.type == ViolationType.PROHIBITED_WORD for v in result.violations)

    def test_direct_transaction(self):
        """직거래 유도 탐지"""
        result = self.checker.check("직거래 환영합니다")
        assert not result.passed
        assert any(v.type == ViolationType.PROHIBITED_WORD for v in result.violations)


class TestSafeAlternatives:
    """안전한 대안 제시 테스트"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_alternatives_for_superlative(self):
        """최상급 표현 대안"""
        result = self.checker.check("최고의 품질")
        violation = next(v for v in result.violations if v.type == ViolationType.SUPERLATIVE)
        alternatives = self.checker.get_safe_alternatives(violation)

        assert len(alternatives) > 0
        assert "고품질" in alternatives or "프리미엄" in alternatives

    def test_alternatives_for_medical_device(self):
        """의료기기 표현 대안"""
        result = self.checker.check("통증 완화")
        violation = next(v for v in result.violations if v.type == ViolationType.MEDICAL_DEVICE)
        alternatives = self.checker.get_safe_alternatives(violation)

        assert len(alternatives) > 0
        assert any("케어" in alt or "도움" in alt for alt in alternatives)


class TestReportFormatting:
    """리포트 포맷팅 테스트"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_report_passed(self):
        """통과 리포트"""
        result = self.checker.check("고품질 면 소재 티셔츠")
        report = self.checker.format_report(result)

        # 중립적인 표현이면 통과할 수 있음
        if result.passed:
            assert "통과" in report

    def test_report_failed(self):
        """실패 리포트"""
        result = self.checker.check("암 예방 최고의 효과 100% 보장!")
        report = self.checker.format_report(result)

        assert "실패" in report
        assert "오류" in report or "경고" in report

    def test_report_contains_violations(self):
        """리포트에 위반 사항 포함"""
        result = self.checker.check("암 예방 효과")
        report = self.checker.format_report(result)

        assert "의료" in report or "건강" in report
        assert "매칭" in report


class TestStrictModeToggle:
    """엄격 모드 토글 테스트"""

    def test_strict_mode_fails_on_warning(self):
        """엄격 모드: 경고도 실패 처리"""
        checker = PreFlightChecker(strict_mode=True)
        result = checker.check("최고의 품질")  # medium severity

        assert not result.passed

    def test_lenient_mode_passes_on_warning(self):
        """관대 모드: 경고는 통과"""
        checker = PreFlightChecker(strict_mode=False)
        # medium만 있고 high가 없는 텍스트
        result = checker.check("최고의")

        # error_count가 0이면 통과
        if result.error_count == 0:
            assert result.passed


class TestConvenienceFunction:
    """편의 함수 테스트"""

    def test_preflight_check_function(self):
        """preflight_check() 편의 함수"""
        result = preflight_check("암 예방 효과")

        assert not result.passed
        assert len(result.violations) > 0


class TestComplexTexts:
    """복합 텍스트 테스트"""

    def setup_method(self):
        self.checker = PreFlightChecker(strict_mode=True)

    def test_multiple_violations(self):
        """여러 위반이 있는 텍스트"""
        text = "최고의 암 예방 효과! 100% 보장! 디즈니 캐릭터 포함!"
        result = self.checker.check(text)

        assert not result.passed
        # 최소 3가지 유형의 위반
        violation_types = set(v.type for v in result.violations)
        assert len(violation_types) >= 3

    def test_real_product_name_safe(self):
        """실제 안전한 상품명"""
        text = "편안한 면 소재 라운드넥 반팔 티셔츠 화이트 M사이즈"
        result = self.checker.check(text)

        # 브랜드/효능 주장 없으면 통과 가능
        high_violations = [v for v in result.violations if v.severity == "high"]
        # 엄격 모드에서도 high 없으면 통과 가능성 있음
        if len(high_violations) == 0:
            assert result.error_count == 0

    def test_real_product_name_risky(self):
        """실제 위험한 상품명"""
        text = "나이키st 운동화 면역력 강화 최초 개발 배터리 내장"
        result = self.checker.check(text)

        assert not result.passed
        assert len(result.violations) >= 3


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
