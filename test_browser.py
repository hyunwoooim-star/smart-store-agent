#!/usr/bin/env python3
"""
test_browser.py - 1688 스크래퍼 테스트 스크립트

사용법:
    # Mock 테스트 (API 키 없이)
    python test_browser.py --mock

    # 실제 테스트 (Gemini API 키 필요)
    python test_browser.py --url "https://detail.1688.com/offer/xxx.html"

    # 헤드리스 모드 끄기 (브라우저 창 보기)
    python test_browser.py --url "..." --show-browser
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


console = Console()


async def test_mock_scraper():
    """Mock 스크래퍼 테스트 (API 키 없이)"""
    from src.adapters.alibaba_scraper import MockAlibabaScraper, scrape_1688
    from src.domain.logic import LandedCostCalculator
    from src.domain.models import MarketType

    console.print("\n[bold cyan]🧪 Mock 스크래퍼 테스트 시작[/bold cyan]\n")

    # 1. Mock 데이터 추출
    test_url = "https://detail.1688.com/offer/mock-test.html"
    console.print(f"📦 URL: {test_url}")

    scraped = await scrape_1688(test_url, use_mock=True)

    # 2. 추출 결과 표시
    table = Table(title="🇨🇳 1688 추출 결과")
    table.add_column("항목", style="cyan")
    table.add_column("값", style="green")

    table.add_row("상품명", scraped.name)
    table.add_row("가격", f"¥{scraped.price_cny}")
    table.add_row("무게", f"{scraped.weight_kg} kg")
    table.add_row("사이즈", f"{scraped.length_cm} x {scraped.width_cm} x {scraped.height_cm} cm")
    table.add_row("MOQ", f"{scraped.moq}개")
    table.add_row("이미지", scraped.image_url or "없음")

    console.print(table)

    # 3. 원본 스펙 테이블
    if scraped.raw_specs:
        console.print("\n[bold]📋 원본 스펙 테이블:[/bold]")
        for key, value in scraped.raw_specs.items():
            console.print(f"  - {key}: {value}")

    # 4. 도메인 모델 변환 및 마진 계산
    console.print("\n[bold yellow]💰 마진 계산 테스트[/bold yellow]\n")

    mock_scraper = MockAlibabaScraper()
    product = mock_scraper.to_domain_product(scraped, category="캠핑/레저")

    calculator = LandedCostCalculator()
    result = calculator.calculate(
        product=product,
        target_price=45000,  # 목표 판매가 45,000원
        market=MarketType.NAVER,
        shipping_method="항공",
        include_ad_cost=True,
    )

    # 5. 마진 분석 결과
    result_table = Table(title="📊 마진 분석 결과")
    result_table.add_column("항목", style="cyan")
    result_table.add_column("값", style="green")

    risk_emoji = {"safe": "🟢", "warning": "🟡", "danger": "🔴"}
    emoji = risk_emoji.get(result.risk_level.value, "❓")

    result_table.add_row("목표 판매가", f"{result.target_price:,}원")
    result_table.add_row("총 비용", f"{result.total_cost:,}원")
    result_table.add_row("예상 수익", f"{result.profit:,}원")
    result_table.add_row("마진율", f"{emoji} {result.margin_percent}%")
    result_table.add_row("손익분기점", f"{result.breakeven_price:,}원")
    result_table.add_row("30% 마진 달성가", f"{result.target_margin_price:,}원")

    console.print(result_table)

    # 6. AI 추천
    console.print(Panel(result.recommendation, title="🤖 AI 판정", border_style="blue"))

    console.print("\n[bold green]✅ Mock 테스트 완료![/bold green]")
    return True


async def test_real_scraper(url: str, headless: bool = True):
    """실제 1688 스크래퍼 테스트 (API 키 필요)"""
    from src.adapters.alibaba_scraper import AlibabaScraper
    from src.domain.logic import LandedCostCalculator
    from src.domain.models import MarketType

    console.print("\n[bold cyan]🌐 실제 스크래퍼 테스트 시작[/bold cyan]\n")
    console.print(f"📦 URL: {url}")
    console.print(f"🖥️  Headless: {'Yes' if headless else 'No (브라우저 창 표시)'}")

    try:
        scraper = AlibabaScraper(headless=headless)
    except ValueError as e:
        console.print(f"[red]❌ 오류: {e}[/red]")
        console.print("\n[yellow]💡 해결 방법:[/yellow]")
        console.print("1. .env 파일에 GEMINI_API_KEY 추가")
        console.print("2. 또는 --mock 옵션으로 테스트")
        return False

    console.print("\n[yellow]⏳ AI 에이전트가 페이지를 분석 중... (30초~1분 소요)[/yellow]")

    try:
        scraped = await scraper.scrape(url)
    except ImportError as e:
        console.print(f"[red]❌ 패키지 오류: {e}[/red]")
        console.print("\n[yellow]💡 해결 방법:[/yellow]")
        console.print("1. Python 3.11+ 확인: python --version")
        console.print("2. 패키지 설치: pip install browser-use langchain-google-genai playwright")
        console.print("3. Playwright 브라우저 설치: playwright install")
        return False

    # 결과 표시
    table = Table(title="🇨🇳 1688 추출 결과")
    table.add_column("항목", style="cyan")
    table.add_column("값", style="green")

    table.add_row("상품명", scraped.name)
    table.add_row("가격", f"¥{scraped.price_cny}")
    table.add_row("무게", f"{scraped.weight_kg or '추출 실패'} kg")
    table.add_row("사이즈", f"{scraped.length_cm or '?'} x {scraped.width_cm or '?'} x {scraped.height_cm or '?'} cm")
    table.add_row("MOQ", f"{scraped.moq}개")

    console.print(table)

    # 마진 계산
    if scraped.price_cny > 0:
        product = scraper.to_domain_product(scraped, category="캠핑/레저")

        calculator = LandedCostCalculator()
        result = calculator.calculate(
            product=product,
            target_price=45000,
            market=MarketType.NAVER,
            shipping_method="항공",
            include_ad_cost=True,
        )

        console.print(Panel(result.recommendation, title="🤖 AI 판정", border_style="blue"))

    console.print("\n[bold green]✅ 실제 테스트 완료![/bold green]")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="1688 스크래퍼 테스트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
    python test_browser.py --mock                      # Mock 테스트
    python test_browser.py --url "https://..."         # 실제 URL 테스트
    python test_browser.py --url "https://..." --show  # 브라우저 창 보기
        """
    )
    parser.add_argument("--mock", action="store_true", help="Mock 데이터로 테스트 (API 키 불필요)")
    parser.add_argument("--url", type=str, help="1688 상품 URL")
    parser.add_argument("--show", "--show-browser", action="store_true", help="브라우저 창 표시 (headless 끄기)")

    args = parser.parse_args()

    # 배너
    console.print(Panel.fit(
        "[bold blue]Smart Store Agent v3.3[/bold blue]\n"
        "[cyan]1688 스크래퍼 테스트[/cyan]",
        border_style="blue"
    ))

    if args.mock:
        asyncio.run(test_mock_scraper())
    elif args.url:
        asyncio.run(test_real_scraper(args.url, headless=not args.show))
    else:
        console.print("[yellow]사용법: python test_browser.py --mock 또는 --url <URL>[/yellow]")
        console.print("\n[cyan]--mock 옵션으로 먼저 테스트해보세요![/cyan]")
        # 기본으로 Mock 테스트 실행
        asyncio.run(test_mock_scraper())


if __name__ == "__main__":
    main()
