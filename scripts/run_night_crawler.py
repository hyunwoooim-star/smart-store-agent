#!/usr/bin/env python
"""
run_night_crawler.py - Night Crawler 실행 스크립트

사용법:
    python scripts/run_night_crawler.py
    python scripts/run_night_crawler.py --mock
    python scripts/run_night_crawler.py --keywords 3

옵션:
    --mock      Mock 모드 (실제 API 호출 안 함)
    --keywords  크롤링할 키워드 수 (기본: 5)
    --notify    알림 전송
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 로딩
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.crawler.night_crawler import NightCrawler, CrawlerConfig
from src.crawler.repository import CandidateRepository
from src.notifications.slack_notifier import SlackNotifier
from src.notifications.kakao_notifier import KakaoNotifier


def parse_args():
    """명령행 인자 파싱"""
    parser = argparse.ArgumentParser(description="Night Crawler - 밤샘 소싱 봇")
    parser.add_argument("--mock", action="store_true", help="Mock 모드 사용")
    parser.add_argument("--keywords", type=int, default=5, help="크롤링할 키워드 수")
    parser.add_argument("--notify", action="store_true", help="알림 전송")
    parser.add_argument("--seed", action="store_true", help="기본 키워드 시드")
    return parser.parse_args()


async def main():
    """메인 함수"""
    args = parse_args()

    print("=" * 60)
    print("Night Crawler v4.0 - 밤샘 소싱 봇")
    print("=" * 60)
    print(f"Mock 모드: {args.mock}")
    print(f"키워드 수: {args.keywords}")
    print(f"알림 전송: {args.notify}")
    print("=" * 60)

    # 키워드 시드 (필요시)
    if args.seed:
        from src.crawler.keyword_manager import KeywordManager
        km = KeywordManager()
        keywords = km.seed_default_keywords()
        print(f"기본 키워드 {len(keywords)}개 추가됨")

    # 크롤러 설정
    config = CrawlerConfig(
        use_mock=args.mock,
        max_keywords_per_run=args.keywords
    )

    # 크롤러 실행
    crawler = NightCrawler(config=config)
    stats = await crawler.run_nightly_job()

    # 알림 전송
    if args.notify:
        print("\n알림 전송 중...")

        # 슬랙
        slack = SlackNotifier()
        slack.send_crawl_complete(stats)

        # 카카오톡
        kakao = KakaoNotifier()
        kakao.send_crawl_complete(stats)

        print("알림 전송 완료!")

    # 결과 요약
    print("\n" + "=" * 60)
    print("최종 결과")
    print("=" * 60)
    print(f"처리 키워드: {stats.crawled_keywords}/{stats.total_keywords}")
    print(f"발견 상품: {stats.total_products_found}")
    print(f"저장된 후보: {stats.saved_candidates}")
    print(f"소요 시간: {stats.duration_minutes:.1f}분")
    if stats.errors:
        print(f"오류: {len(stats.errors)}건")
    print("=" * 60)

    return stats


if __name__ == "__main__":
    asyncio.run(main())
