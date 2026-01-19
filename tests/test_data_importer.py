"""data_importer.py 테스트"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from importers.data_importer import (
    DataImporter,
    KeywordData,
    ImportResult
)


class TestDataImporter:
    """데이터 임포터 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.importer = DataImporter(min_search_volume=500, max_competition_rate=10.0)

    def test_keyword_data_creation(self):
        """KeywordData 생성 테스트"""
        kw = KeywordData(
            keyword="테스트 키워드",
            monthly_search_volume=10000,
            monthly_search_volume_pc=3000,
            monthly_search_volume_mobile=7000,
            total_products=5000,
            competition_rate=0.5
        )

        assert kw.keyword == "테스트 키워드"
        assert kw.monthly_search_volume == 10000
        assert kw.competition_rate == 0.5

    def test_opportunity_score_calculation(self):
        """기회 점수 계산 테스트"""
        kw = KeywordData(
            keyword="테스트",
            monthly_search_volume=10000,
            monthly_search_volume_pc=3000,
            monthly_search_volume_mobile=7000,
            total_products=5000,
            competition_rate=0.5
        )

        score = kw.calculate_opportunity_score()

        # 공식: (검색량 / 1000) / (경쟁강도 + 0.1)
        # (10000 / 1000) / (0.5 + 0.1) = 10 / 0.6 = 16.67
        assert score > 0
        assert abs(score - 16.67) < 0.1

    def test_opportunity_score_zero_competition(self):
        """경쟁강도 0일 때 기회 점수 테스트"""
        kw = KeywordData(
            keyword="테스트",
            monthly_search_volume=5000,
            monthly_search_volume_pc=1500,
            monthly_search_volume_mobile=3500,
            total_products=0,
            competition_rate=0
        )

        score = kw.calculate_opportunity_score()

        # 경쟁강도 0이면 검색량 / 1000
        assert score == 5.0

    def test_importer_settings(self):
        """임포터 설정값 테스트"""
        assert self.importer.min_search_volume == 500
        assert self.importer.max_competition_rate == 10.0

    def test_default_importer_settings(self):
        """기본 임포터 설정값 테스트"""
        default_importer = DataImporter()

        assert default_importer.min_search_volume == 1000
        assert default_importer.max_competition_rate == 5.0

    def test_import_result_structure(self):
        """ImportResult 구조 테스트"""
        result = ImportResult(
            success=True,
            total_rows=100,
            valid_rows=80,
            filtered_rows=20,
            file_path="test.xlsx"
        )

        assert result.success == True
        assert result.total_rows == 100
        assert result.valid_rows == 80
        assert result.filtered_rows == 20
        assert len(result.keywords) == 0
        assert len(result.errors) == 0

    def test_import_nonexistent_file(self):
        """존재하지 않는 파일 임포트 테스트"""
        result = self.importer.import_from_excel("nonexistent_file.xlsx")

        assert result.success == False
        assert len(result.errors) > 0
        assert "찾을 수 없습니다" in result.errors[0]

    def test_to_dict_list(self):
        """딕셔너리 리스트 변환 테스트"""
        keywords = [
            KeywordData(
                keyword="테스트1",
                monthly_search_volume=5000,
                monthly_search_volume_pc=1500,
                monthly_search_volume_mobile=3500,
                total_products=2000,
                competition_rate=0.4,
                avg_price=30000
            ),
            KeywordData(
                keyword="테스트2",
                monthly_search_volume=3000,
                monthly_search_volume_pc=900,
                monthly_search_volume_mobile=2100,
                total_products=1500,
                competition_rate=0.5
            ),
        ]

        for kw in keywords:
            kw.calculate_opportunity_score()

        dict_list = self.importer.to_dict_list(keywords)

        assert len(dict_list) == 2
        assert dict_list[0]["keyword"] == "테스트1"
        assert dict_list[0]["monthly_search_volume"] == 5000
        assert dict_list[0]["avg_price"] == 30000
        assert dict_list[1]["avg_price"] is None

    def test_get_top_opportunities(self):
        """상위 기회 키워드 테스트"""
        result = ImportResult(
            success=True,
            total_rows=10,
            valid_rows=10,
            filtered_rows=0
        )

        # 키워드 추가
        for i in range(10):
            kw = KeywordData(
                keyword=f"테스트{i}",
                monthly_search_volume=1000 * (10 - i),
                monthly_search_volume_pc=300 * (10 - i),
                monthly_search_volume_mobile=700 * (10 - i),
                total_products=500 * (i + 1),
                competition_rate=0.1 * (i + 1)
            )
            kw.calculate_opportunity_score()
            result.keywords.append(kw)

        # 점수순 정렬
        result.keywords.sort(key=lambda x: x.opportunity_score, reverse=True)

        top5 = self.importer.get_top_opportunities(result, top_n=5)

        assert len(top5) == 5
        # 첫 번째가 가장 높은 점수
        assert top5[0].opportunity_score >= top5[1].opportunity_score

    def test_column_mapping(self):
        """컬럼 매핑 테스트"""
        assert "키워드" in DataImporter.COLUMN_MAPPING
        assert "월간검색량" in DataImporter.COLUMN_MAPPING
        assert "상품수" in DataImporter.COLUMN_MAPPING

    def test_alternative_columns(self):
        """대체 컬럼명 테스트"""
        assert "keyword" in DataImporter.ALTERNATIVE_COLUMNS
        assert "키워드" in DataImporter.ALTERNATIVE_COLUMNS["keyword"]
        assert "검색어" in DataImporter.ALTERNATIVE_COLUMNS["keyword"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
