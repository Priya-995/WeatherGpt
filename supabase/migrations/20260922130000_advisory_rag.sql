-- Step 3: Advisory RAG Supabase Migration
-- Enables pgvector, creates advisory_documents table, vector index, and search function.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS advisory_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT NOT NULL,
    hazard_type TEXT NOT NULL,
    official_text TEXT NOT NULL,
    plain_language_text TEXT NOT NULL,
    persona_tags TEXT[] NOT NULL DEFAULT '{}',
    embedding VECTOR(384) NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for vector similarity search using Cosine distance
CREATE INDEX IF NOT EXISTS advisory_documents_embedding_idx 
ON advisory_documents 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- RPC function to query vector-matched advisory documents by persona and hazard filters
CREATE OR REPLACE FUNCTION match_advisory_documents(
    query_embedding VECTOR(384),
    persona TEXT DEFAULT NULL,
    hazard_types TEXT[] DEFAULT NULL,
    match_count INT DEFAULT 6
)
RETURNS TABLE (
    id UUID,
    source_url TEXT,
    hazard_type TEXT,
    official_text TEXT,
    plain_language_text TEXT,
    persona_tags TEXT[],
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ad.id,
        ad.source_url,
        ad.hazard_type,
        ad.official_text,
        ad.plain_language_text,
        ad.persona_tags,
        1 - (ad.embedding <=> query_embedding) AS similarity
    FROM advisory_documents ad
    WHERE
        (persona IS NULL OR persona = '' OR ad.persona_tags @> ARRAY[persona])
        AND
        (hazard_types IS NULL OR cardinality(hazard_types) = 0 OR ad.hazard_type = ANY(hazard_types))
    ORDER BY ad.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
