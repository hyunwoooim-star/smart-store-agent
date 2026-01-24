-- ============================================================
-- Smart Store Agent - Supabase Schema (v4.0)
-- ============================================================
-- Gemini CTO 권장: "로컬 JSON → Supabase 마이그레이션"
--
-- 테이블 구조:
-- 1. sourcing_keywords - 소싱 키워드 관리
-- 2. sourcing_candidates - 소싱 후보 상품
-- 3. upload_history - 업로드 히스토리
-- 4. app_settings - 앱 설정 (환율, 수수료 등)
-- ============================================================

-- Extension for UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. 소싱 키워드 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS sourcing_keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keyword VARCHAR(100) NOT NULL,
    category VARCHAR(50) DEFAULT '기타',
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(keyword)
);

-- 인덱스
CREATE INDEX idx_keywords_active ON sourcing_keywords(is_active);
CREATE INDEX idx_keywords_priority ON sourcing_keywords(priority);

-- ============================================================
-- 2. 소싱 후보 상품 테이블
-- ============================================================
CREATE TYPE candidate_status AS ENUM ('pending', 'approved', 'rejected', 'uploaded', 'failed');
CREATE TYPE crawl_risk_level AS ENUM ('safe', 'warning', 'danger');

CREATE TABLE IF NOT EXISTS sourcing_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 원본 정보 (1688)
    source_url TEXT NOT NULL,
    source_title TEXT,
    source_price_cny DECIMAL(10, 2) DEFAULT 0,
    source_images TEXT[] DEFAULT '{}',
    source_shop_name VARCHAR(200),
    source_shop_rating DECIMAL(3, 2) DEFAULT 0,
    source_sales_count INTEGER DEFAULT 0,

    -- AI 분석 결과
    title_kr VARCHAR(200),
    estimated_cost_krw INTEGER DEFAULT 0,
    estimated_margin_rate DECIMAL(5, 2) DEFAULT 0,
    recommended_price INTEGER DEFAULT 0,
    breakeven_price INTEGER DEFAULT 0,
    risk_level crawl_risk_level DEFAULT 'safe',
    risk_reasons TEXT[] DEFAULT '{}',

    -- 경쟁사 분석 (네이버)
    naver_min_price INTEGER DEFAULT 0,
    naver_avg_price INTEGER DEFAULT 0,
    naver_max_price INTEGER DEFAULT 0,
    competitor_count INTEGER DEFAULT 0,

    -- 상태 관리
    status candidate_status DEFAULT 'pending',
    approved_at TIMESTAMPTZ,
    rejected_reason TEXT,

    -- 등록 정보
    naver_product_id VARCHAR(50),
    naver_product_url TEXT,
    uploaded_at TIMESTAMPTZ,

    -- 메타
    keyword_id UUID REFERENCES sourcing_keywords(id) ON DELETE SET NULL,
    keyword VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source_url)
);

-- 인덱스
CREATE INDEX idx_candidates_status ON sourcing_candidates(status);
CREATE INDEX idx_candidates_keyword_id ON sourcing_candidates(keyword_id);
CREATE INDEX idx_candidates_margin ON sourcing_candidates(estimated_margin_rate DESC);
CREATE INDEX idx_candidates_created ON sourcing_candidates(created_at DESC);

-- ============================================================
-- 3. 업로드 히스토리 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS upload_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES sourcing_candidates(id) ON DELETE CASCADE,
    platform VARCHAR(20) DEFAULT 'naver',
    status VARCHAR(20) DEFAULT 'pending',
    response_data JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_history_candidate ON upload_history(candidate_id);
CREATE INDEX idx_history_created ON upload_history(created_at DESC);

-- ============================================================
-- 4. 앱 설정 테이블 (Key-Value Store)
-- ============================================================
CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 기본 설정 삽입
INSERT INTO app_settings (key, value, description) VALUES
    ('exchange_rate', '{"CNY_KRW": 190}', '환율 설정'),
    ('tariff_rates', '{
        "가구/인테리어": 0.08,
        "캠핑/레저": 0.08,
        "의류/패션": 0.13,
        "전자기기": 0.08,
        "생활용품": 0.08,
        "주방용품": 0.08,
        "뷰티/화장품": 0.08,
        "기타": 0.10
    }', '카테고리별 관세율'),
    ('cost_rates', '{
        "vat_rate": 0.10,
        "naver_fee_rate": 0.055,
        "return_allowance_rate": 0.05,
        "ad_cost_rate": 0.10
    }', '비용 비율 설정'),
    ('shipping', '{
        "air_freight_per_kg": 8000,
        "sea_freight_per_kg": 3000,
        "domestic_shipping": 3000,
        "volume_weight_divisor": 6000
    }', '배송비 설정'),
    ('margin_thresholds', '{
        "minimum_viable": 15,
        "low_risk": 30,
        "target": 30
    }', '마진율 임계값')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- 5. RLS (Row Level Security) 정책
-- ============================================================
-- 개인 프로젝트용: 모든 접근 허용 (production에서는 수정 필요)

ALTER TABLE sourcing_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE sourcing_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

-- 익명/인증 사용자 모두 허용 (개인 프로젝트용)
CREATE POLICY "Allow all operations on keywords" ON sourcing_keywords
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on candidates" ON sourcing_candidates
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on history" ON upload_history
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on settings" ON app_settings
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- 6. Updated At 트리거
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_keywords_updated_at
    BEFORE UPDATE ON sourcing_keywords
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON sourcing_candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON app_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
