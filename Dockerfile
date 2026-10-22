FROM python:3.11.12-slim@sha256:dbf1de478a55d6763afaa39c2f3d7b54b25230614980276de5cacdde79529d0c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.lock ./
RUN pip install --no-cache-dir uv==0.7.3
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --system --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match -r requirements.lock
COPY maintenance ./maintenance
COPY api ./api
COPY scripts ./scripts
COPY config ./config
COPY db ./db
COPY docs/prompts ./docs/prompts
RUN useradd -m -u 10001 maintenance && mkdir -p /app/models /app/artifacts && chown -R maintenance:maintenance /app
USER maintenance
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
