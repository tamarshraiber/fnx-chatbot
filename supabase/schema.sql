-- Run this once in the Supabase SQL Editor (safe to run again).

-- 1. Turn on pgvector (vector columns and vector search).
create extension if not exists vector;

-- 2. One row per chunk. chunk_id is the primary key, so uploading the same
--    chunk again overwrites the old row (no duplicates).
create table if not exists chunks (
    chunk_id     text primary key,
    url          text not null,
    title        text not null default '',
    text         text not null,
    chunk_index  integer not null,
    lastmod      text,
    content_hash text,
    crawled_at   timestamptz,
    embedding    vector(768) not null
);

-- Used to find or delete all chunks of one page.
create index if not exists chunks_url_idx on chunks (url);

-- 3. Fast approximate vector search (HNSW, cosine distance).
create index if not exists chunks_embedding_idx
    on chunks using hnsw (embedding vector_cosine_ops);

-- 4. Search function. Returns the closest chunks with a similarity score
--    (1 = same meaning, 0 = unrelated). The Python code calls it as an RPC.
create or replace function match_chunks(
    query_embedding vector(768),
    match_count int default 5
)
returns table (
    chunk_id   text,
    url        text,
    title      text,
    text       text,
    lastmod    text,
    similarity float
)
language sql stable
as $$
    select
        c.chunk_id,
        c.url,
        c.title,
        c.text,
        c.lastmod,
        1 - (c.embedding <=> query_embedding) as similarity
    from chunks c
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
