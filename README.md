# PaddockBook

Internal RAG knowledge assistant for F1 team staff. Answers questions
against Sporting, Technical, and Financial regulation documents with 
department-aware retrieval.

**Status**: early development, spec-driven via [OpenSpec](https://github.com/Fission-AI/OpenSpec)

## Docs
- `PRD.md` — product requirements
- `openspec/` — living specs and change proposals
- `openspec/config.yaml` — project context and rules used by AI agents

## Stack
FastAPI, Postgres + pgvector, AWS (Lambda/Fargate, Cognito, CDK), Angular,
Anthropic API/Bedrock

## Access
Private repository. Contains references to internal financial reporting
processes — do not make public without review.