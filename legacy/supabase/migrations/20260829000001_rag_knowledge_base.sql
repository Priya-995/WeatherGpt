-- =============================================================================
-- WeatherGPT RAG Knowledge Base Migration
-- Run this in the Supabase SQL Editor (Dashboard -> SQL Editor -> New query)
-- =============================================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Hazard and persona enums
DO $$ BEGIN
    CREATE TYPE hazard_type AS ENUM (
        'heavy_rain', 'heatwave', 'flood', 'cyclone', 'general'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE persona_type AS ENUM (
        'citizen', 'farmer', 'health', 'govt', 'all'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 3. knowledge_documents — one row per source document
CREATE TABLE IF NOT EXISTS public.knowledge_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    hazard          hazard_type NOT NULL DEFAULT 'general',
    persona         persona_type NOT NULL DEFAULT 'all',
    location_scope  TEXT NOT NULL DEFAULT 'India',
    published_at    DATE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_content     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kd_hazard_persona
    ON public.knowledge_documents (hazard, persona);

-- 4. knowledge_chunks — one row per embedding chunk (384-dim for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS public.knowledge_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.knowledge_documents(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    embedding   vector(384) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. IVFFlat index for fast approximate cosine similarity search
CREATE INDEX IF NOT EXISTS idx_kc_embedding_cosine
    ON public.knowledge_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 6. match_knowledge_chunks — RAG retrieval function
CREATE OR REPLACE FUNCTION match_knowledge_chunks(
    query_embedding  vector(384),
    match_hazard     text,           -- e.g. 'heavy_rain', 'heatwave', 'general'
    match_persona    text,           -- e.g. 'citizen', 'farmer', 'health'
    match_count      int DEFAULT 4
)
RETURNS TABLE (
    chunk_id        UUID,
    content         TEXT,
    similarity      FLOAT,
    doc_title       TEXT,
    doc_source_name TEXT,
    doc_source_url  TEXT,
    doc_hazard      TEXT,
    doc_persona     TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kc.id                       AS chunk_id,
        kc.content                  AS content,
        1 - (kc.embedding <=> query_embedding) AS similarity,
        kd.title                    AS doc_title,
        kd.source_name              AS doc_source_name,
        kd.source_url               AS doc_source_url,
        kd.hazard::text             AS doc_hazard,
        kd.persona::text            AS doc_persona
    FROM
        public.knowledge_chunks kc
        JOIN public.knowledge_documents kd ON kd.id = kc.document_id
    WHERE
        -- Hazard filter: match exact hazard OR 'general' docs always included
        (kd.hazard::text = match_hazard OR kd.hazard::text = 'general')
        AND
        -- Persona filter: match exact persona OR 'all' docs always included
        (kd.persona::text = match_persona OR kd.persona::text = 'all')
    ORDER BY
        kc.embedding <=> query_embedding  -- cosine distance ASC = most similar first
    LIMIT match_count;
END;
$$;

-- Grant execute permissions to API roles
GRANT EXECUTE ON FUNCTION match_knowledge_chunks TO anon, authenticated, service_role;
