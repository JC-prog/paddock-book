-- Chat provider configuration schema. Runs automatically on first
-- container startup via /docker-entrypoint-initdb.d/ for a brand-new
-- volume; on an already-initialized database, apply by hand (see
-- specs/016-chat-provider-config/quickstart.md Prerequisites). See
-- specs/016-chat-provider-config/data-model.md for the design this
-- implements.

-- Deliberately a single-row table, not a general key-value settings
-- store (see research.md) — id is always 1. Combines the spec's two
-- conceptual entities (active provider, OpenAI-compatible credential)
-- into one row, since both are exactly-one-instance-ever data.
CREATE TABLE chat_provider_settings (
    id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    active_provider text NOT NULL DEFAULT 'ollama'
        CHECK (active_provider IN ('ollama', 'bedrock', 'openai_compatible')),
    ollama_model_override text,
    bedrock_model text,
    openai_compatible_base_url text,
    -- Plain text, not encrypted at rest — a deliberate, documented
    -- tradeoff (spec FR-010/Assumptions), not an oversight.
    openai_compatible_api_key text,
    openai_compatible_model text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
