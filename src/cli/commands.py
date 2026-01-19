"""
CLI 명령어 처리 모듈

향상된 CLI 인터페이스:
- 서브커맨드 지원 (analyze, calc, filter, report)
- 인터랙티브 모드
- 프로그레스 바 지원
- 컬러 출력
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CLIConfig:
    """CLI 설정"""
    verbose: bool = False
    output_dir: str = "output"
    use_mock: bool = True
    no_color: bool = False


class ColorOutput:
    """컬러 출력 유틸리티"""

    COLORS = {
        "reset": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
    }

    def __init__(self, enabled: bool = True):
        self.enabled = enabled and sys.stdout.isatty()

    def colorize(self, text: str, color: str) -> str:
        """텍스트에 색상 적용"""
        if not self.enabled or color not in self.COLORS:
            return text
        return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"

    def success(self, text: str) -> str:
        return self.colorize(text, "green")

    def error(self, text: str) -> str:
        return self.colorize(text, "red")

    def warning(self, text: str) -> str:
        return self.colorize(text, "yellow")

    def info(self, text: str) -> str:
        return self.colorize(text, "cyan")

    def bold(self, text: str) -> str:
        return self.colorize(text, "bold")


class ProgressBar:
    """간단한 프로그레스 바"""

    def __init__(self, total: int, width: int = 40, color: ColorOutput = None):
        self.total = total
        self.width = width
        self.current = 0
        self.color = color or ColorOutput()

    def update(self, current: int = None, message: str = ""):
        """프로그레스 업데이트"""
        if current is not None:
            self.current = current
        else:
            self.current += 1

        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        line = f"\r  [{bar}] {percent*100:.0f}% {message}"
        sys.stdout.write(line)
        sys.stdout.flush()

        if self.current >= self.total:
            print()

    def complete(self, message: str = "완료"):
        """완료 표시"""
        self.update(self.total, self.color.success(message))


class CLI:
    """Smart Store Agent CLI"""

    VERSION = "3.1.0"

    def __init__(self, config: CLIConfig = None):
        self.config = config or CLIConfig()
        self.color = ColorOutput(enabled=not self.config.no_color)

    def banner(self):
        """배너 출력"""
        banner_text = f"""
╔══════════════════════════════════════════════════════════════╗
║      Smart Store Agent v{self.VERSION}                             ║
║      AI 기반 네이버 스마트스토어 자동화 시스템                ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(self.color.bold(banner_text))

    def print_header(self, title: str):
        """섹션 헤더 출력"""
        print(f"\n{self.color.bold('='*60)}")
        print(f"  {self.color.info(title)}")
        print(f"{self.color.bold('='*60)}\n")

    def print_step(self, step: int, total: int, message: str):
        """단계 출력"""
        prefix = f"[{step}/{total}]"
        print(f"\n{self.color.info(prefix)} {message}")

    def print_result(self, key: str, value: Any, indent: int = 2):
        """결과 출력"""
        spaces = " " * indent
        print(f"{spaces}{key}: {self.color.bold(str(value))}")

    def print_success(self, message: str):
        """성공 메시지"""
        print(f"\n✅ {self.color.success(message)}")

    def print_error(self, message: str):
        """에러 메시지"""
        print(f"\n❌ {self.color.error(message)}", file=sys.stderr)

    def print_warning(self, message: str):
        """경고 메시지"""
        print(f"\n⚠️ {self.color.warning(message)}")

    def confirm(self, message: str, default: bool = True) -> bool:
        """확인 프롬프트"""
        suffix = "[Y/n]" if default else "[y/N]"
        try:
            response = input(f"{message} {suffix}: ").strip().lower()
            if not response:
                return default
            return response in ("y", "yes", "예")
        except (EOFError, KeyboardInterrupt):
            return False

    def prompt(self, message: str, default: str = "") -> str:
        """입력 프롬프트"""
        suffix = f" [{default}]" if default else ""
        try:
            response = input(f"{message}{suffix}: ").strip()
            return response if response else default
        except (EOFError, KeyboardInterrupt):
            return default

    def select(self, message: str, options: List[str], default: int = 0) -> int:
        """선택 프롬프트"""
        print(f"\n{message}")
        for i, opt in enumerate(options):
            prefix = ">" if i == default else " "
            print(f"  {prefix} {i+1}. {opt}")

        try:
            response = input(f"선택 [1-{len(options)}]: ").strip()
            if not response:
                return default
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return idx
            return default
        except (ValueError, EOFError, KeyboardInterrupt):
            return default


def create_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성"""
    parser = argparse.ArgumentParser(
        prog="smart-store-agent",
        description="AI 기반 네이버 스마트스토어 자동화 시스템 v3.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 데모 실행
  %(prog)s demo

  # 마진 계산
  %(prog)s calc --price-cny 45 --weight 2.5 --dimensions 80x20x15 --target-price 45000

  # 상품 분석
  %(prog)s analyze --product "캠핑의자" --category "캠핑/레저" --price-cny 45 --target-price 45000

  # 리뷰 필터링
  %(prog)s filter --input reviews.json --output filtered.json

  # 리포트 생성
  %(prog)s report --input analysis.json --format markdown
"""
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 출력 모드"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="컬러 출력 비활성화"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="출력 디렉토리 (기본: output)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {CLI.VERSION}"
    )

    # 서브커맨드
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # demo 커맨드
    demo_parser = subparsers.add_parser("demo", help="데모 모드 실행")
    demo_parser.add_argument(
        "--product",
        default="캠핑의자",
        help="데모 상품명 (기본: 캠핑의자)"
    )

    # calc 커맨드 (마진 계산)
    calc_parser = subparsers.add_parser("calc", help="마진 계산")
    calc_parser.add_argument("--price-cny", type=float, required=True, help="도매가 (위안)")
    calc_parser.add_argument("--weight", type=float, required=True, help="실무게 (kg)")
    calc_parser.add_argument("--dimensions", type=str, required=True, help="박스 크기 '가로x세로x높이' (cm)")
    calc_parser.add_argument("--target-price", type=int, required=True, help="목표 판매가 (원)")
    calc_parser.add_argument("--category", default="기타", help="카테고리")
    calc_parser.add_argument("--moq", type=int, default=10, help="최소 주문 수량")
    calc_parser.add_argument("--shipping", choices=["항공", "해운"], default="항공", help="배송 방식")
    calc_parser.add_argument("--no-ad", action="store_true", help="광고비 제외")

    # analyze 커맨드 (종합 분석)
    analyze_parser = subparsers.add_parser("analyze", help="상품 종합 분석")
    analyze_parser.add_argument("--product", type=str, required=True, help="상품명")
    analyze_parser.add_argument("--category", type=str, default="기타", help="카테고리")
    analyze_parser.add_argument("--price-cny", type=float, required=True, help="도매가 (위안)")
    analyze_parser.add_argument("--weight", type=float, default=1.0, help="무게 (kg)")
    analyze_parser.add_argument("--dimensions", type=str, default="30x30x30", help="박스 크기 (cm)")
    analyze_parser.add_argument("--moq", type=int, default=10, help="최소 주문 수량")
    analyze_parser.add_argument("--target-price", type=int, required=True, help="목표 판매가 (원)")
    analyze_parser.add_argument("--keywords", type=str, help="키워드 파일 (Excel/CSV)")
    analyze_parser.add_argument("--reviews", type=str, help="리뷰 파일 (JSON)")
    analyze_parser.add_argument("--mock", action="store_true", default=True, help="Mock Gemini 사용")

    # filter 커맨드 (리뷰 필터링)
    filter_parser = subparsers.add_parser("filter", help="리뷰 키워드 필터링")
    filter_parser.add_argument("--input", type=str, required=True, help="입력 리뷰 파일")
    filter_parser.add_argument("--output", type=str, help="출력 파일")
    filter_parser.add_argument("--format", choices=["json", "csv", "text"], default="json", help="출력 형식")

    # report 커맨드 (리포트 생성)
    report_parser = subparsers.add_parser("report", help="리포트 생성")
    report_parser.add_argument("--input", type=str, required=True, help="분석 결과 파일")
    report_parser.add_argument("--format", choices=["markdown", "json", "html"], default="markdown", help="출력 형식")
    report_parser.add_argument("--output", type=str, help="출력 파일")

    # validate 커맨드 (스펙 검증)
    validate_parser = subparsers.add_parser("validate", help="카피 스펙 검증")
    validate_parser.add_argument("--copy", type=str, required=True, help="검증할 카피 텍스트 또는 파일")
    validate_parser.add_argument("--spec", type=str, required=True, help="스펙 데이터 파일 (JSON)")

    return parser


def parse_dimensions(dims_str: str) -> tuple:
    """박스 크기 문자열 파싱"""
    try:
        parts = dims_str.lower().replace(" ", "").split("x")
        if len(parts) != 3:
            raise ValueError("형식 오류")
        return tuple(float(p) for p in parts)
    except (ValueError, AttributeError):
        return (30, 30, 30)


def cmd_demo(args, cli: CLI):
    """데모 명령어 실행"""
    cli.banner()
    cli.print_header(f"🎮 데모 모드 - {args.product}")

    # 동적 임포트
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from sourcing.margin_calculator import MarginCalculator, SourcingInput, ProductDimensions
    from analyzers.keyword_filter import KeywordFilter, ReviewData
    from analyzers.gemini_analyzer import MockGeminiAnalyzer
    from generators.gap_reporter import GapReporter

    # 데모 데이터
    demo_products = {
        "캠핑의자": {
            "category": "캠핑/레저",
            "price_cny": 45,
            "weight": 2.5,
            "dimensions": (80, 20, 15),
            "moq": 50,
            "target_price": 45000
        },
        "LED 캠핑 랜턴": {
            "category": "캠핑/레저",
            "price_cny": 25,
            "weight": 0.5,
            "dimensions": (12, 12, 20),
            "moq": 100,
            "target_price": 25000
        },
        "접이식 테이블": {
            "category": "캠핑/레저",
            "price_cny": 65,
            "weight": 4.0,
            "dimensions": (60, 40, 10),
            "moq": 30,
            "target_price": 55000
        }
    }

    product = args.product if args.product in demo_products else "캠핑의자"
    data = demo_products[product]

    # 1. 마진 계산
    progress = ProgressBar(5, color=cli.color)
    cli.print_step(1, 5, "마진 분석 중...")

    calc = MarginCalculator()
    input_data = SourcingInput(
        product_name=product,
        wholesale_price_cny=data["price_cny"],
        actual_weight_kg=data["weight"],
        dimensions=ProductDimensions(*data["dimensions"]),
        moq=data["moq"],
        target_price_krw=data["target_price"],
        category=data["category"]
    )
    result = calc.calculate(input_data)
    progress.update(1)

    # 2. 결과 출력
    cli.print_step(2, 5, "결과 분석 중...")
    progress.update(2)

    print(f"\n  📦 무게 정보:")
    cli.print_result("실무게", f"{result.actual_weight_kg}kg", 4)
    cli.print_result("부피무게", f"{result.volume_weight_kg}kg", 4)
    cli.print_result("청구무게", f"{result.billable_weight_kg}kg", 4)

    print(f"\n  💰 비용 내역:")
    cli.print_result("상품원가", f"{result.product_cost_krw:,}원", 4)
    cli.print_result("관세", f"{result.tariff_krw:,}원", 4)
    cli.print_result("부가세", f"{result.vat_krw:,}원", 4)
    cli.print_result("배대지비용", f"{result.shipping_agency_fee_krw:,}원", 4)
    cli.print_result("국내택배", f"{result.domestic_shipping_krw:,}원", 4)
    cli.print_result("네이버수수료", f"{result.platform_fee_krw:,}원", 4)
    cli.print_result("반품충당금", f"{result.return_allowance_krw:,}원", 4)
    cli.print_result("광고비", f"{result.ad_cost_krw:,}원", 4)

    progress.update(3)

    # 3. 리뷰 분석
    cli.print_step(3, 5, "리뷰 분석 중...")
    filter_engine = KeywordFilter()
    sample_reviews = [
        ReviewData(review_id="1", content="품질이 너무 별로예요.", rating=1),
        ReviewData(review_id="2", content="배송 빠르고 좋아요!", rating=5),
        ReviewData(review_id="3", content="냄새가 심해요.", rating=2),
    ]
    filter_result = filter_engine.filter_reviews(sample_reviews)
    progress.update(4)

    # 4. AI 분석
    cli.print_step(4, 5, "AI 분석 중...")
    analyzer = MockGeminiAnalyzer()
    reviews_text = filter_engine.get_complaints_for_gemini(filter_result)
    ai_result = analyzer.analyze_complaints(reviews_text)
    progress.update(5, "완료!")

    # 5. 최종 결과
    print(f"\n  📊 분석 결과:")
    cli.print_result("총 비용", f"{result.total_cost_krw:,}원", 4)
    cli.print_result("순이익", f"{result.profit_krw:,}원", 4)
    cli.print_result("마진율", f"{result.margin_percent}%", 4)

    if result.is_viable:
        cli.print_success(f"수익성 양호 - {result.recommendation}")
    else:
        cli.print_warning(f"수익성 부족 - {result.recommendation}")

    print(f"\n  💡 손익분기 분석:")
    cli.print_result("손익분기 판매가", f"{result.breakeven_price_krw:,}원", 4)
    cli.print_result("목표마진(30%) 판매가", f"{result.target_margin_price_krw:,}원", 4)

    print(f"\n  🤖 AI 분석 결과:")
    for insight in ai_result.key_insights[:3]:
        print(f"    • {insight}")

    cli.print_success("데모 완료!")


def cmd_calc(args, cli: CLI):
    """마진 계산 명령어 실행"""
    cli.banner()
    cli.print_header("💰 마진 계산기 v3.1")

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from sourcing.margin_calculator import MarginCalculator, SourcingInput, ProductDimensions

    dims = parse_dimensions(args.dimensions)

    calc = MarginCalculator()
    input_data = SourcingInput(
        product_name="분석 대상",
        wholesale_price_cny=args.price_cny,
        actual_weight_kg=args.weight,
        dimensions=ProductDimensions(*dims),
        moq=args.moq,
        target_price_krw=args.target_price,
        category=args.category
    )

    result = calc.calculate(
        input_data,
        shipping_method=args.shipping,
        include_ad_cost=not args.no_ad
    )

    print(f"\n  📦 무게 정보:")
    cli.print_result("실무게", f"{result.actual_weight_kg}kg", 4)
    cli.print_result("부피무게", f"{result.volume_weight_kg}kg", 4)
    cli.print_result("청구무게", f"{result.billable_weight_kg}kg", 4)

    print(f"\n  💰 비용 내역:")
    cli.print_result("상품원가", f"{result.product_cost_krw:,}원", 4)
    cli.print_result("관세", f"{result.tariff_krw:,}원", 4)
    cli.print_result("부가세", f"{result.vat_krw:,}원", 4)
    cli.print_result("배대지비용", f"{result.shipping_agency_fee_krw:,}원", 4)
    cli.print_result("국내택배", f"{result.domestic_shipping_krw:,}원", 4)
    cli.print_result("네이버수수료", f"{result.platform_fee_krw:,}원", 4)
    cli.print_result("반품충당금", f"{result.return_allowance_krw:,}원", 4)
    if not args.no_ad:
        cli.print_result("광고비", f"{result.ad_cost_krw:,}원", 4)

    print(f"\n  📊 분석 결과:")
    cli.print_result("총 비용", f"{result.total_cost_krw:,}원", 4)
    cli.print_result("순이익", f"{result.profit_krw:,}원", 4)
    cli.print_result("마진율", f"{result.margin_percent}%", 4)
    cli.print_result("리스크 등급", result.risk_level, 4)

    print(f"\n  💡 손익분기 분석:")
    cli.print_result("손익분기 판매가", f"{result.breakeven_price_krw:,}원", 4)
    cli.print_result("목표마진(30%) 판매가", f"{result.target_margin_price_krw:,}원", 4)

    print(f"\n  🎯 추천:")
    print(f"    {result.recommendation}")

    if result.is_viable:
        cli.print_success("수익성 분석 완료 - 사업 가능")
    else:
        cli.print_warning("수익성 분석 완료 - 가격 재검토 필요")


def cmd_analyze(args, cli: CLI):
    """상품 분석 명령어 실행"""
    cli.banner()
    cli.print_header(f"🔍 상품 종합 분석: {args.product}")

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from main import SmartStoreAgent

    dims = parse_dimensions(args.dimensions)

    agent = SmartStoreAgent(
        use_mock_gemini=args.mock,
        output_dir=cli.config.output_dir
    )

    agent.analyze_product(
        product_name=args.product,
        category=args.category,
        wholesale_price_cny=args.price_cny,
        actual_weight_kg=args.weight,
        dimensions=dims,
        moq=args.moq,
        target_price_krw=args.target_price,
        keywords_file=args.keywords
    )

    cli.print_success("상품 분석 완료!")


def cmd_filter(args, cli: CLI):
    """리뷰 필터링 명령어 실행"""
    cli.banner()
    cli.print_header("📝 리뷰 필터링")

    import json
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analyzers.keyword_filter import KeywordFilter, ReviewData

    # 입력 파일 로드
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        cli.print_error(f"파일을 찾을 수 없습니다: {args.input}")
        return
    except json.JSONDecodeError:
        cli.print_error("JSON 파싱 오류")
        return

    # ReviewData 변환
    reviews = []
    for item in data:
        reviews.append(ReviewData(
            review_id=str(item.get("id", "")),
            content=item.get("content", ""),
            rating=item.get("rating", 3)
        ))

    print(f"  로드된 리뷰: {len(reviews)}건")

    # 필터링
    filter_engine = KeywordFilter()
    result = filter_engine.filter_reviews(reviews)

    print(f"\n  📊 필터링 결과:")
    cli.print_result("전체 리뷰", result.total_reviews, 4)
    cli.print_result("불만 리뷰", result.complaint_reviews, 4)
    cli.print_result("긍정 리뷰", result.positive_reviews, 4)
    cli.print_result("중립 리뷰", result.neutral_reviews, 4)

    if result.complaint_categories:
        print(f"\n  📌 불만 카테고리:")
        for cat, count in sorted(result.complaint_categories.items(), key=lambda x: -x[1])[:5]:
            cli.print_result(cat, f"{count}건", 4)

    # 출력
    if args.output:
        output_data = {
            "summary": {
                "total": result.total_reviews,
                "complaints": result.complaint_reviews,
                "positive": result.positive_reviews,
                "categories": result.complaint_categories
            },
            "complaints": [
                {
                    "id": c.review.review_id,
                    "content": c.review.content,
                    "rating": c.review.rating,
                    "sentiment": c.sentiment.value,
                    "categories": list(c.complaint_categories),
                    "keywords": c.matched_negative_keywords
                }
                for c in result.complaints
            ]
        }

        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        cli.print_success(f"결과 저장: {args.output}")
    else:
        cli.print_success("필터링 완료!")


def cmd_validate(args, cli: CLI):
    """스펙 검증 명령어 실행"""
    cli.banner()
    cli.print_header("✅ 카피 스펙 검증")

    import json
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analyzers.spec_validator import SpecValidator, SpecData

    # 카피 로드
    copy_text = args.copy
    if os.path.exists(args.copy):
        with open(args.copy, 'r', encoding='utf-8') as f:
            copy_text = f.read()

    # 스펙 로드
    try:
        with open(args.spec, 'r', encoding='utf-8') as f:
            spec_data = json.load(f)
    except FileNotFoundError:
        cli.print_error(f"스펙 파일을 찾을 수 없습니다: {args.spec}")
        return

    spec = SpecData(
        product_name=spec_data.get("name", ""),
        category=spec_data.get("category", ""),
        weight_kg=spec_data.get("weight"),
        dimensions_cm=tuple(spec_data.get("dimensions", [])) or None,
        max_load_kg=spec_data.get("max_load"),
        material=spec_data.get("material")
    )

    print(f"  검증할 카피: {copy_text[:50]}...")
    print(f"  상품 스펙: {spec.product_name}")

    # 검증
    validator = SpecValidator()
    result = validator.validate(copy_text, spec)

    print(f"\n  📊 검증 결과:")
    cli.print_result("전체 항목", result.total_claims, 4)
    cli.print_result("통과", result.passed, 4)
    cli.print_result("경고", result.warnings, 4)
    cli.print_result("실패", result.failed, 4)
    cli.print_result("미확인", result.unverified, 4)
    cli.print_result("리스크 등급", result.risk_level, 4)

    if result.failed > 0:
        cli.print_error("스펙 불일치 발견 - 카피 수정 필요")
    elif result.warnings > 0:
        cli.print_warning("경고 항목 존재 - 검토 권장")
    else:
        cli.print_success("검증 통과!")


def run_cli():
    """CLI 실행"""
    parser = create_parser()
    args = parser.parse_args()

    # CLI 설정
    config = CLIConfig(
        verbose=args.verbose,
        output_dir=args.output_dir,
        no_color=args.no_color
    )
    cli = CLI(config)

    # 명령어 라우팅
    if args.command == "demo":
        cmd_demo(args, cli)
    elif args.command == "calc":
        cmd_calc(args, cli)
    elif args.command == "analyze":
        cmd_analyze(args, cli)
    elif args.command == "filter":
        cmd_filter(args, cli)
    elif args.command == "validate":
        cmd_validate(args, cli)
    else:
        # 명령어 없으면 도움말
        cli.banner()
        parser.print_help()


if __name__ == "__main__":
    run_cli()
