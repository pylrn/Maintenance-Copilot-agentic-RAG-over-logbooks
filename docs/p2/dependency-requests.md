# Dependency requests from Person 2 (Agent, UI & Workflows) to Person 1 (Platform & Retrieval)

## Date: 2026-10-22
## Target Contract: maintenance/v1

### Required packages to add to `pyproject.toml` / `requirements.lock`:
1. `pydantic>=2.7.0` (validated runtime schemas)
2. `pydantic-settings>=2.0.0` (validated environment configuration)
3. `fastapi>=0.110.0`
4. `uvicorn[standard]>=0.28.0`
5. `httpx>=0.27.0`
6. `openai>=1.20.0` (OpenAI-compatible client for DeepSeek Chat Completions)
7. `pydantic-ai-slim[openai]>=1.106.0,<2.0` (or compatible PydanticAI 1.x adapter for native tool calls & structured output)
8. `asyncpg>=0.29.0` (PostgreSQL async database driver)
9. `pypdf>=4.0.0` (for optional/bounded untrusted PDF upload text extraction)
10. `python-multipart>=0.0.9` (FastAPI file upload support)
11. `pytest>=8.0.0`, `pytest-asyncio>=0.23.0` (test suites)
