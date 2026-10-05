-- =========================================================================
-- SafeBite AI: Supabase PostgreSQL Schema & Security Policies
-- Tables: user_profiles, scan_history, verified_products_cache
-- Storage Bucket: label-scans
-- =========================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Table: user_profiles
CREATE TABLE IF NOT EXISTS public.user_profiles (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL DEFAULT 'User',
    medical_history TEXT DEFAULT '',
    allergies TEXT[] DEFAULT ARRAY[]::TEXT[],
    food_preferences TEXT DEFAULT '',
    diabetic_insulin_sensitivity NUMERIC(4,2) DEFAULT 1.0,
    cultural_flags JSONB DEFAULT '{"jain": false, "halal": false, "vrat": false}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 2. Table: scan_history
CREATE TABLE IF NOT EXISTS public.scan_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,
    product_id TEXT,
    product_name TEXT NOT NULL,
    brand TEXT DEFAULT '',
    verdict TEXT NOT NULL,
    confidence TEXT DEFAULT 'UNVERIFIED',
    input_mode TEXT DEFAULT 'text',
    nutrition_facts JSONB DEFAULT '{}'::JSONB,
    ingredients TEXT DEFAULT '',
    allergens TEXT[] DEFAULT ARRAY[]::TEXT[],
    ocr_text TEXT DEFAULT '',
    image_url TEXT,
    clinical_reasons JSONB DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- 3. Table: verified_products_cache
CREATE TABLE IF NOT EXISTS public.verified_products_cache (
    id TEXT PRIMARY KEY,
    barcode TEXT,
    name TEXT NOT NULL,
    brand TEXT DEFAULT '',
    category TEXT DEFAULT '',
    nutrition_facts JSONB DEFAULT '{}'::JSONB,
    ingredients TEXT DEFAULT '',
    allergens TEXT[] DEFAULT ARRAY[]::TEXT[],
    nova_group INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    last_verified_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- Indexes for high-performance querying
CREATE INDEX IF NOT EXISTS idx_scan_history_user_id ON public.scan_history(user_id);
CREATE INDEX IF NOT EXISTS idx_scan_history_created_at ON public.scan_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verified_products_barcode ON public.verified_products_cache(barcode);

-- =========================================================================
-- Row-Level Security (RLS) Policies
-- =========================================================================

-- Enable RLS on all tables
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scan_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verified_products_cache ENABLE ROW LEVEL SECURITY;

-- Grant API access to anon and authenticated roles
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_profiles TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.scan_history TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.verified_products_cache TO anon, authenticated;

-- Policies for user_profiles
CREATE POLICY "Allow public read on user_profiles"
    ON public.user_profiles FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow public insert on user_profiles"
    ON public.user_profiles FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "Allow public update on user_profiles"
    ON public.user_profiles FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- Policies for scan_history
CREATE POLICY "Allow public read on scan_history"
    ON public.scan_history FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow public insert on scan_history"
    ON public.scan_history FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Policies for verified_products_cache
CREATE POLICY "Allow public read on verified_products_cache"
    ON public.verified_products_cache FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow public insert on verified_products_cache"
    ON public.verified_products_cache FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "Allow public update on verified_products_cache"
    ON public.verified_products_cache FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- =========================================================================
-- Storage Bucket: label-scans
-- =========================================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('label-scans', 'label-scans', true)
ON CONFLICT (id) DO NOTHING;

-- Storage Policies for label-scans
CREATE POLICY "Allow public upload to label-scans"
    ON storage.objects FOR INSERT
    TO anon, authenticated
    WITH CHECK (bucket_id = 'label-scans');

CREATE POLICY "Allow public read from label-scans"
    ON storage.objects FOR SELECT
    TO anon, authenticated
    USING (bucket_id = 'label-scans');
