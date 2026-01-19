"""
data_importer.py - 아이템스카우트 엑셀 데이터 임포터 (v3.1)

핵심 기능:
1. 아이템스카우트 엑셀 파일 파싱
2. 키워드, 검색량, 경쟁강도, 상품수 등 추출
3. 기본 필터링 (검색량 최소값, 경쟁강도 등)
4. 데이터 정규화 및 구조화
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

# pandas는 requirements.txt에 포함되어 있음
try:
    import pandas as pd
except ImportError:
    pd = None  # 테스트 시 pandas 없이도 구조 확인 가능


@dataclass
class KeywordData:
    """키워드 분석 데이터"""
    keyword: str                        # 키워드
    monthly_search_volume: int          # 월간 검색량
    monthly_search_volume_pc: int       # PC 검색량
    monthly_search_volume_mobile: int   # 모바일 검색량
    total_products: int                 # 총 상품수
    competition_rate: float             # 경쟁강도 (상품수/검색량)
    avg_price: Optional[int] = None     # 평균 판매가
    click_rate: Optional[float] = None  # 클릭률
    conversion_rate: Optional[float] = None  # 전환율

    # 계산된 지표
    opportunity_score: float = 0.0      # 기회 점수 (높을수록 좋음)

    def calculate_opportunity_score(self) -> float:
        """
        기회 점수 계산
        - 검색량 높고 경쟁강도 낮을수록 좋음
        - 공식: (검색량 / 1000) / (경쟁강도 + 0.1)
        """
        if self.competition_rate <= 0:
            self.opportunity_score = self.monthly_search_volume / 1000
        else:
            self.opportunity_score = (self.monthly_search_volume / 1000) / (self.competition_rate + 0.1)
        return self.opportunity_score


@dataclass
class ImportResult:
    """임포트 결과"""
    success: bool
    total_rows: int
    valid_rows: int
    filtered_rows: int
    keywords: List[KeywordData] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    file_path: str = ""


class DataImporter:
    """아이템스카우트 엑셀 데이터 임포터"""

    # 아이템스카우트 엑셀 컬럼 매핑 (실제 컬럼명에 맞게 조정 필요)
    COLUMN_MAPPING = {
        "키워드": "keyword",
        "월간검색량": "monthly_search_volume",
        "월간검색량(PC)": "monthly_search_volume_pc",
        "월간검색량(모바일)": "monthly_search_volume_mobile",
        "상품수": "total_products",
        "경쟁강도": "competition_rate",
        "평균가격": "avg_price",
        "클릭률": "click_rate",
        "전환율": "conversion_rate",
    }

    # 대체 컬럼명 (아이템스카우트 버전에 따라 다를 수 있음)
    ALTERNATIVE_COLUMNS = {
        "keyword": ["키워드", "검색어", "Keyword"],
        "monthly_search_volume": ["월간검색량", "월검색량", "검색량", "Monthly Search"],
        "monthly_search_volume_pc": ["월간검색량(PC)", "PC검색량", "PC"],
        "monthly_search_volume_mobile": ["월간검색량(모바일)", "모바일검색량", "Mobile"],
        "total_products": ["상품수", "총상품수", "Products"],
        "competition_rate": ["경쟁강도", "경쟁률", "Competition"],
        "avg_price": ["평균가격", "평균판매가", "Avg Price"],
    }

    def __init__(self, min_search_volume: int = 1000, max_competition_rate: float = 5.0):
        """
        Args:
            min_search_volume: 최소 월간 검색량 (기본 1000)
            max_competition_rate: 최대 경쟁강도 (기본 5.0)
        """
        self.min_search_volume = min_search_volume
        self.max_competition_rate = max_competition_rate

    def _find_column(self, df_columns: List[str], target: str) -> Optional[str]:
        """데이터프레임에서 대상 컬럼 찾기"""
        alternatives = self.ALTERNATIVE_COLUMNS.get(target, [])
        for col in alternatives:
            if col in df_columns:
                return col
        return None

    def _parse_number(self, value: Any) -> int:
        """숫자 파싱 (쉼표, 문자열 처리)"""
        if pd is None:
            return 0
        if pd.isna(value):
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        try:
            # 쉼표 제거 후 파싱
            cleaned = str(value).replace(",", "").replace(" ", "")
            return int(float(cleaned))
        except (ValueError, TypeError):
            return 0

    def _parse_float(self, value: Any) -> float:
        """실수 파싱"""
        if pd is None:
            return 0.0
        if pd.isna(value):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace(",", "").replace(" ", "").replace("%", "")
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    def import_from_excel(self, file_path: str, sheet_name: Optional[str] = None) -> ImportResult:
        """
        엑셀 파일에서 데이터 임포트

        Args:
            file_path: 엑셀 파일 경로
            sheet_name: 시트명 (None이면 첫 번째 시트)

        Returns:
            ImportResult: 임포트 결과
        """
        result = ImportResult(
            success=False,
            total_rows=0,
            valid_rows=0,
            filtered_rows=0,
            file_path=file_path
        )

        # pandas 체크
        if pd is None:
            result.errors.append("pandas가 설치되지 않았습니다. pip install pandas openpyxl")
            return result

        # 파일 존재 확인
        if not os.path.exists(file_path):
            result.errors.append(f"파일을 찾을 수 없습니다: {file_path}")
            return result

        try:
            # 엑셀 파일 읽기
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)

            result.total_rows = len(df)

            # 컬럼 매핑
            columns = list(df.columns)
            keyword_col = self._find_column(columns, "keyword")
            search_vol_col = self._find_column(columns, "monthly_search_volume")
            search_vol_pc_col = self._find_column(columns, "monthly_search_volume_pc")
            search_vol_mobile_col = self._find_column(columns, "monthly_search_volume_mobile")
            products_col = self._find_column(columns, "total_products")
            competition_col = self._find_column(columns, "competition_rate")
            price_col = self._find_column(columns, "avg_price")

            # 필수 컬럼 확인
            if not keyword_col:
                result.errors.append(f"키워드 컬럼을 찾을 수 없습니다. 컬럼: {columns}")
                return result

            if not search_vol_col:
                result.errors.append(f"검색량 컬럼을 찾을 수 없습니다. 컬럼: {columns}")
                return result

            # 데이터 파싱
            for idx, row in df.iterrows():
                try:
                    keyword = str(row[keyword_col]).strip()
                    if not keyword or keyword == "nan":
                        continue

                    search_volume = self._parse_number(row.get(search_vol_col, 0))
                    search_volume_pc = self._parse_number(row.get(search_vol_pc_col, 0)) if search_vol_pc_col else 0
                    search_volume_mobile = self._parse_number(row.get(search_vol_mobile_col, 0)) if search_vol_mobile_col else 0
                    total_products = self._parse_number(row.get(products_col, 0)) if products_col else 0

                    # 경쟁강도 계산 (컬럼이 없으면 직접 계산)
                    if competition_col:
                        competition_rate = self._parse_float(row.get(competition_col, 0))
                    elif search_volume > 0:
                        competition_rate = total_products / search_volume
                    else:
                        competition_rate = 0.0

                    avg_price = self._parse_number(row.get(price_col, 0)) if price_col else None

                    # 유효한 데이터만 추가
                    if search_volume > 0:
                        result.valid_rows += 1

                        keyword_data = KeywordData(
                            keyword=keyword,
                            monthly_search_volume=search_volume,
                            monthly_search_volume_pc=search_volume_pc,
                            monthly_search_volume_mobile=search_volume_mobile,
                            total_products=total_products,
                            competition_rate=round(competition_rate, 2),
                            avg_price=avg_price if avg_price and avg_price > 0 else None
                        )

                        # 기회 점수 계산
                        keyword_data.calculate_opportunity_score()

                        # 필터링 조건 확인
                        if (search_volume >= self.min_search_volume and
                            competition_rate <= self.max_competition_rate):
                            result.keywords.append(keyword_data)
                        else:
                            result.filtered_rows += 1

                except Exception as e:
                    result.errors.append(f"행 {idx} 파싱 오류: {str(e)}")

            # 기회 점수 기준 정렬
            result.keywords.sort(key=lambda x: x.opportunity_score, reverse=True)
            result.success = True

        except Exception as e:
            result.errors.append(f"파일 읽기 오류: {str(e)}")

        return result

    def import_from_csv(self, file_path: str, encoding: str = "utf-8") -> ImportResult:
        """CSV 파일에서 데이터 임포트"""
        result = ImportResult(
            success=False,
            total_rows=0,
            valid_rows=0,
            filtered_rows=0,
            file_path=file_path
        )

        if pd is None:
            result.errors.append("pandas가 설치되지 않았습니다.")
            return result

        if not os.path.exists(file_path):
            result.errors.append(f"파일을 찾을 수 없습니다: {file_path}")
            return result

        try:
            # CSV를 임시 엑셀로 변환하지 않고 직접 처리
            df = pd.read_csv(file_path, encoding=encoding)

            # 임시 엑셀 파일로 저장 후 import_from_excel 재사용
            temp_excel = file_path.replace(".csv", "_temp.xlsx")
            df.to_excel(temp_excel, index=False)

            result = self.import_from_excel(temp_excel)
            result.file_path = file_path

            # 임시 파일 삭제
            if os.path.exists(temp_excel):
                os.remove(temp_excel)

        except Exception as e:
            result.errors.append(f"CSV 읽기 오류: {str(e)}")

        return result

    def get_top_opportunities(self, result: ImportResult, top_n: int = 20) -> List[KeywordData]:
        """상위 기회 키워드 반환"""
        return result.keywords[:top_n]

    def to_dict_list(self, keywords: List[KeywordData]) -> List[Dict[str, Any]]:
        """KeywordData 리스트를 딕셔너리 리스트로 변환"""
        return [
            {
                "keyword": kw.keyword,
                "monthly_search_volume": kw.monthly_search_volume,
                "total_products": kw.total_products,
                "competition_rate": kw.competition_rate,
                "avg_price": kw.avg_price,
                "opportunity_score": round(kw.opportunity_score, 2)
            }
            for kw in keywords
        ]


# --- 테스트 실행 코드 ---
if __name__ == "__main__":
    print("="*60)
    print("📊 데이터 임포터 테스트 (v3.1)")
    print("="*60)

    # 샘플 데이터로 테스트 (실제 파일 없이)
    importer = DataImporter(min_search_volume=500, max_competition_rate=10.0)

    print("\n[설정값]")
    print(f"  - 최소 검색량: {importer.min_search_volume}")
    print(f"  - 최대 경쟁강도: {importer.max_competition_rate}")

    # 샘플 KeywordData 생성
    sample_keywords = [
        KeywordData(
            keyword="캠핑의자",
            monthly_search_volume=45000,
            monthly_search_volume_pc=15000,
            monthly_search_volume_mobile=30000,
            total_products=25000,
            competition_rate=0.56
        ),
        KeywordData(
            keyword="초경량 캠핑의자",
            monthly_search_volume=8500,
            monthly_search_volume_pc=2500,
            monthly_search_volume_mobile=6000,
            total_products=3200,
            competition_rate=0.38
        ),
        KeywordData(
            keyword="접이식 캠핑의자 경량",
            monthly_search_volume=3200,
            monthly_search_volume_pc=800,
            monthly_search_volume_mobile=2400,
            total_products=890,
            competition_rate=0.28
        ),
    ]

    print("\n[샘플 키워드 분석]")
    for kw in sample_keywords:
        kw.calculate_opportunity_score()
        print(f"\n  키워드: {kw.keyword}")
        print(f"    - 월간 검색량: {kw.monthly_search_volume:,}")
        print(f"    - 상품수: {kw.total_products:,}")
        print(f"    - 경쟁강도: {kw.competition_rate}")
        print(f"    - 기회점수: {kw.opportunity_score:.2f}")

    print("\n" + "="*60)
    print("✅ 데이터 임포터 모듈 준비 완료")
    print("   실제 사용: importer.import_from_excel('파일경로.xlsx')")
    print("="*60 + "\n")
