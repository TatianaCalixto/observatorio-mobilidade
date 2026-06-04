# syntax=docker/dockerfile:1
# Imagem do Observatório de Mobilidade — ambiente reprodutível via uv.

# ---- Stage 1: builder (instala dependências com uv) ----
FROM python:3.12-slim AS builder

# Binário do uv a partir da imagem oficial.
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

# Usa o Python do sistema (3.12 da base), sem baixar um Python gerenciado.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system

WORKDIR /app

# Camada cacheável: instala dependências antes de copiar o código.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

# Copia o código e finaliza o ambiente.
COPY . .
RUN uv sync --frozen

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime

# make para `make all`; ca-certificates para HTTPS das ingestões.
RUN apt-get update \
    && apt-get install -y --no-install-recommends make ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /bin/uv /bin/uv
COPY --from=builder /app /app

# O venv já está em /app/.venv; expõe seus binários no PATH.
ENV PATH="/app/.venv/bin:$PATH" \
    UV_PYTHON_PREFERENCE=only-system

EXPOSE 8501

# Padrão: sobe o dashboard. Também roda `make all`, `python -m orchestration.flow`, etc.
CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501"]
