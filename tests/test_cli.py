"""CLI 모듈 테스트"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.commands import (
    CLI,
    CLIConfig,
    ColorOutput,
    ProgressBar,
    create_parser,
    parse_dimensions,
)


class TestCLIConfig:
    """CLIConfig 테스트"""

    def test_default_config(self):
        """기본 설정"""
        config = CLIConfig()
        assert config.verbose == False
        assert config.output_dir == "output"
        assert config.use_mock == True
        assert config.no_color == False

    def test_custom_config(self):
        """커스텀 설정"""
        config = CLIConfig(
            verbose=True,
            output_dir="custom_output",
            use_mock=False,
            no_color=True
        )
        assert config.verbose == True
        assert config.output_dir == "custom_output"
        assert config.use_mock == False
        assert config.no_color == True


class TestColorOutput:
    """ColorOutput 테스트"""

    def test_colorize_enabled(self):
        """컬러 활성화"""
        color = ColorOutput(enabled=True)
        # TTY가 아니면 비활성화됨
        text = color.colorize("test", "green")
        assert "test" in text

    def test_colorize_disabled(self):
        """컬러 비활성화"""
        color = ColorOutput(enabled=False)
        text = color.colorize("test", "green")
        assert text == "test"

    def test_success(self):
        """성공 메시지"""
        color = ColorOutput(enabled=False)
        text = color.success("완료")
        assert text == "완료"

    def test_error(self):
        """에러 메시지"""
        color = ColorOutput(enabled=False)
        text = color.error("오류")
        assert text == "오류"

    def test_warning(self):
        """경고 메시지"""
        color = ColorOutput(enabled=False)
        text = color.warning("주의")
        assert text == "주의"


class TestProgressBar:
    """ProgressBar 테스트"""

    def test_initialization(self):
        """초기화"""
        bar = ProgressBar(total=10, width=20)
        assert bar.total == 10
        assert bar.width == 20
        assert bar.current == 0

    def test_update(self):
        """업데이트"""
        bar = ProgressBar(total=10)
        bar.update(5)
        assert bar.current == 5

    def test_update_increment(self):
        """증가 업데이트"""
        bar = ProgressBar(total=10)
        bar.update()
        bar.update()
        assert bar.current == 2


class TestCLI:
    """CLI 테스트"""

    def test_version(self):
        """버전 확인"""
        assert CLI.VERSION == "3.1.0"

    def test_cli_initialization(self):
        """CLI 초기화"""
        cli = CLI()
        assert cli.config is not None
        assert cli.color is not None

    def test_cli_with_config(self):
        """설정 포함 CLI 초기화"""
        config = CLIConfig(verbose=True)
        cli = CLI(config)
        assert cli.config.verbose == True


class TestParser:
    """Parser 테스트"""

    def test_create_parser(self):
        """파서 생성"""
        parser = create_parser()
        assert parser is not None

    def test_demo_command(self):
        """demo 명령어 파싱"""
        parser = create_parser()
        args = parser.parse_args(["demo"])
        assert args.command == "demo"

    def test_demo_with_product(self):
        """demo 명령어 + 상품명"""
        parser = create_parser()
        args = parser.parse_args(["demo", "--product", "LED 랜턴"])
        assert args.command == "demo"
        assert args.product == "LED 랜턴"

    def test_calc_command(self):
        """calc 명령어 파싱"""
        parser = create_parser()
        args = parser.parse_args([
            "calc",
            "--price-cny", "45",
            "--weight", "2.5",
            "--dimensions", "80x20x15",
            "--target-price", "45000"
        ])
        assert args.command == "calc"
        assert args.price_cny == 45
        assert args.weight == 2.5
        assert args.dimensions == "80x20x15"
        assert args.target_price == 45000

    def test_calc_with_options(self):
        """calc 명령어 + 옵션"""
        parser = create_parser()
        args = parser.parse_args([
            "calc",
            "--price-cny", "45",
            "--weight", "2.5",
            "--dimensions", "80x20x15",
            "--target-price", "45000",
            "--category", "캠핑/레저",
            "--shipping", "해운",
            "--no-ad"
        ])
        assert args.category == "캠핑/레저"
        assert args.shipping == "해운"
        assert args.no_ad == True

    def test_analyze_command(self):
        """analyze 명령어 파싱"""
        parser = create_parser()
        args = parser.parse_args([
            "analyze",
            "--product", "캠핑의자",
            "--price-cny", "45",
            "--target-price", "45000"
        ])
        assert args.command == "analyze"
        assert args.product == "캠핑의자"

    def test_filter_command(self):
        """filter 명령어 파싱"""
        parser = create_parser()
        args = parser.parse_args([
            "filter",
            "--input", "reviews.json"
        ])
        assert args.command == "filter"
        assert args.input == "reviews.json"

    def test_validate_command(self):
        """validate 명령어 파싱"""
        parser = create_parser()
        args = parser.parse_args([
            "validate",
            "--copy", "무게 2kg의 경량 제품",
            "--spec", "spec.json"
        ])
        assert args.command == "validate"
        assert args.copy == "무게 2kg의 경량 제품"

    def test_verbose_flag(self):
        """verbose 플래그"""
        parser = create_parser()
        args = parser.parse_args(["-v", "demo"])
        assert args.verbose == True

    def test_no_color_flag(self):
        """no-color 플래그"""
        parser = create_parser()
        args = parser.parse_args(["--no-color", "demo"])
        assert args.no_color == True

    def test_output_dir(self):
        """output-dir 옵션"""
        parser = create_parser()
        args = parser.parse_args(["-o", "custom", "demo"])
        assert args.output_dir == "custom"


class TestParseDimensions:
    """parse_dimensions 함수 테스트"""

    def test_valid_dimensions(self):
        """유효한 크기"""
        result = parse_dimensions("80x20x15")
        assert result == (80.0, 20.0, 15.0)

    def test_dimensions_with_spaces(self):
        """공백 포함"""
        result = parse_dimensions("80 x 20 x 15")
        assert result == (80.0, 20.0, 15.0)

    def test_dimensions_uppercase(self):
        """대문자 X"""
        result = parse_dimensions("80X20X15")
        assert result == (80.0, 20.0, 15.0)

    def test_dimensions_with_decimals(self):
        """소수점 포함"""
        result = parse_dimensions("80.5x20.5x15.5")
        assert result == (80.5, 20.5, 15.5)

    def test_invalid_dimensions(self):
        """잘못된 형식"""
        result = parse_dimensions("invalid")
        assert result == (30, 30, 30)  # 기본값

    def test_incomplete_dimensions(self):
        """불완전한 크기"""
        result = parse_dimensions("80x20")
        assert result == (30, 30, 30)  # 기본값


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
