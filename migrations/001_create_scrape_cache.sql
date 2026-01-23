-- 001_create_scrape_cache.sql
-- Phase 5.2: 스크래핑 캐시 테이블 (Gemini CTO 조언)
--
-- 목적: API 호출 최소화로 비용 절감
-- TTL: 1688 상품 3일, 리뷰 분석 7일
--
-- 실행 방법:
-- 1. Supabase Dashboard > SQL Editor에 복사/붙여넣기
-- 2. Run 클릭

-- 기존 테이블 삭제 (개발 중에만 사용)
-- DROP TABLE IF EXISTS scrape_cache;

-- 캐시 테이블 생성
CREATE TABLE IF NOT EXISTS scrape_cache (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,           -- 캐시 키 (정규화된 URL 또는 "review:카테고리:상품명")
    data JSONB NOT NULL,                 -- 캐시 데이터 (ScrapedProduct 또는 ReviewAnalysisResult)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스: URL 검색 최적화
CREATE INDEX IF NOT EXISTS idx_scrape_cache_url ON scrape_cache(url);

-- 인덱스: 만료 캐시 정리용 (created_at 기준)
CREATE INDEX IF NOT EXISTS idx_scrape_cache_created_at ON scrape_cache(created_at);

-- RLS (Row Level Security) 비활성화 - 서버 사이드 전용
-- 운영 환경에서는 service_role key 사용 권장
ALTER TABLE scrape_cache DISABLE ROW LEVEL SECURITY;

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_scrape_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_scrape_cache_updated_at ON scrape_cache;
CREATE TRIGGER trigger_scrape_cache_updated_at
    BEFORE UPDATE ON scrape_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_scrape_cache_updated_at();

-- 만료 캐시 자동 삭제 함수 (선택적)
-- pg_cron 확장 필요 (Supabase Pro 플랜)
--
-- SELECT cron.schedule(
--     'cleanup-expired-cache',
--     '0 3 * * *',  -- 매일 새벽 3시
--     $$DELETE FROM scrape_cache WHERE created_at < NOW() - INTERVAL '7 days'$$
-- );

-- 테이블 코멘트
COMMENT ON TABLE scrape_cache IS 'Phase 5.2: API 호출 캐싱 (1688 3일, 리뷰 7일 TTL)';
COMMENT ON COLUMN scrape_cache.url IS '캐시 키: URL 또는 "review:카테고리:상품명"';
COMMENT ON COLUMN scrape_cache.data IS 'JSONB: ScrapedProduct 또는 ReviewAnalysisResult';

-- 확인
SELECT 'scrape_cache 테이블 생성 완료!' AS result;
