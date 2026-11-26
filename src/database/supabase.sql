-- 1. Create the reusable trigger function (one-time setup)
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = current_timestamp;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. users table + trigger
create table users (
    user_id uuid primary key default gen_random_uuid(),
    first_name varchar(50) not null,
    last_name varchar(50) not null,
    email varchar(254) not null unique,
    password_hash varchar(255) not null,
    rf_token varchar(255) not null,
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp
);

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- 3. objects table + trigger
CREATE TABLE objects (
    object_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid REFERENCES users(user_id) ON DELETE CASCADE,
    object_name varchar(100) NOT NULL,
    object_type varchar(50)  NOT NULL,
    object_url  text         NOT NULL,
    created_at  timestamp DEFAULT current_timestamp,
    updated_at  timestamp DEFAULT current_timestamp
);

CREATE TRIGGER trg_objects_updated_at
BEFORE UPDATE ON objects
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- 4. Conversations and their messages. PostgreSQL is the canonical message
-- store; Pinecone contains only the embeddings and retrieval metadata.
CREATE TABLE chats (
    chat_id    uuid PRIMARY KEY,
    user_id   uuid REFERENCES users(user_id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT current_timestamp,
    updated_at timestamptz NOT NULL DEFAULT current_timestamp
);

CREATE TRIGGER trg_chats_updated_at
BEFORE UPDATE ON chats
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE messages (
    message_id uuid PRIMARY KEY,
    chat_id    uuid NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    role       varchar(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content    text NOT NULL,
    metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT current_timestamp
);

CREATE INDEX idx_messages_chat_created_at
ON messages (chat_id, created_at);

-- 5. Tool catalogue for RAG-based tool selection.
-- Both embedding columns are produced by the same model as `embedding_model`
-- (1024-d for llama-text-embed-v2, i.e. ADELARD_MODEL_OUTPUT_DIMENSIONS). A
-- decomposed question is embedded once and compared against BOTH columns to
-- rank candidate tools; see match_tools() below.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE tools (
    tool_id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name                   varchar(200) NOT NULL UNIQUE,
    tool_description            text NOT NULL DEFAULT '',
    tool_name_embeddings        vector(1024),
    tool_description_embeddings vector(1024),
    embedding_model             varchar(100) NOT NULL DEFAULT 'llama-text-embed-v2',
    input_schema                jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_active                   boolean NOT NULL DEFAULT true,
    metadata                    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at                  timestamptz NOT NULL DEFAULT current_timestamp,
    updated_at                  timestamptz NOT NULL DEFAULT current_timestamp,
    CONSTRAINT tools_name_not_blank CHECK (length(btrim(tool_name)) > 0)
);

CREATE TRIGGER trg_tools_updated_at
BEFORE UPDATE ON tools
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- HNSW needs no training data, so it is safe to build on an empty catalogue.
-- Cosine distance (<=>) matches how the embeddings are compared in match_tools().
CREATE INDEX idx_tools_name_embedding
ON tools USING hnsw (tool_name_embeddings vector_cosine_ops);

CREATE INDEX idx_tools_description_embedding
ON tools USING hnsw (tool_description_embeddings vector_cosine_ops);

CREATE INDEX idx_tools_active
ON tools (is_active) WHERE is_active;

COMMENT ON TABLE tools IS
    'MCP tool catalogue; embeddings power semantic tool selection.';
COMMENT ON COLUMN tools.tool_name_embeddings IS
    'Embedding of tool_name. Must use the same model and dimension as tool_description_embeddings.';

-- 6. Alternate surface forms for a tool ("forecast", "weather now") so recall is
-- not limited to the canonical name. Text only; add an embedding column if you
-- want to match aliases semantically as well.
CREATE TABLE tool_aliases (
    alias_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id    uuid NOT NULL REFERENCES tools(tool_id) ON DELETE CASCADE,
    alias      varchar(200) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT current_timestamp
);

CREATE UNIQUE INDEX idx_tool_aliases_unique
ON tool_aliases (tool_id, lower(alias));

-- 7. Retrieval audit trail: which tools each decomposed sub-query matched and
-- how well. Use it to debug poor selections and later tune the match weights.
CREATE TABLE tool_retrievals (
    retrieval_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      uuid REFERENCES messages(message_id) ON DELETE CASCADE,
    chat_id         uuid REFERENCES chats(chat_id) ON DELETE CASCADE,
    sub_query       text NOT NULL,
    tool_id         uuid NOT NULL REFERENCES tools(tool_id) ON DELETE CASCADE,
    rank            smallint NOT NULL CHECK (rank > 0),
    score           real NOT NULL,
    embedding_model varchar(100) NOT NULL DEFAULT 'llama-text-embed-v2',
    created_at      timestamptz NOT NULL DEFAULT current_timestamp,
    UNIQUE (message_id, sub_query, tool_id)
);

CREATE INDEX idx_tool_retrievals_message ON tool_retrievals (message_id);
CREATE INDEX idx_tool_retrievals_tool ON tool_retrievals (tool_id);

-- 8. Semantic tool search for one decomposed sub-query.
-- Blends name and description similarity; call once per sub-query and merge the
-- results (max per tool) to get the best-fit tools for a decomposition.
-- The weighted expression cannot use the HNSW indexes, so this is an exact
-- scan: fine for a tool catalogue of thousands, revisit at ~10^5 tools.
CREATE OR REPLACE FUNCTION match_tools(
    query_embedding    vector(1024),
    match_count        integer DEFAULT 5,
    min_score          real    DEFAULT 0.0,
    name_weight        real    DEFAULT 0.4,
    description_weight real    DEFAULT 0.6
)
RETURNS TABLE (
    tool_id           uuid,
    tool_name         varchar(200),
    tool_description  text,
    input_schema      jsonb,
    metadata          jsonb,
    name_score        real,
    description_score real,
    score             real
)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
    WITH scored AS (
        SELECT
            t.tool_id,
            t.tool_name,
            t.tool_description,
            t.input_schema,
            t.metadata,
            coalesce(1 - (t.tool_name_embeddings <=> query_embedding), 0)::real        AS name_score,
            coalesce(1 - (t.tool_description_embeddings <=> query_embedding), 0)::real AS description_score,
            (
                name_weight * coalesce(1 - (t.tool_name_embeddings <=> query_embedding), 0)
              + description_weight * coalesce(1 - (t.tool_description_embeddings <=> query_embedding), 0)
            )::real AS score
        FROM tools t
        WHERE t.is_active
          AND t.tool_name_embeddings IS NOT NULL
    )
    SELECT tool_id, tool_name, tool_description, input_schema, metadata,
           name_score, description_score, score
    FROM scored
    WHERE score >= min_score
    ORDER BY score DESC
    LIMIT least(greatest(coalesce(match_count, 5), 1), 50);
$$;

COMMENT ON FUNCTION match_tools IS
    'Rank active tools for one decomposed sub-query by blended name/description cosine similarity.';

create table user_context (
  context_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (user_id) on delete CASCADE,
  demographics jsonb,
  personality jsonb,
  preferences jsonb,
  interests jsonb,
  goals jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function set_updated_at () RETURNS trigger as $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

drop trigger IF exists trg_user_context_updated_at on user_context;

create trigger trg_user_context_updated_at BEFORE
update on user_context for EACH row
execute FUNCTION set_updated_at ();