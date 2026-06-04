# Makefile -- Observatorio de Mobilidade
# Comandos padrao do projeto. Requer `uv` no PATH.
# Uso: make <alvo>   |   make help para listar os alvos.

.DEFAULT_GOAL := help
.PHONY: help setup lint test ingest dbt-build train app all

help:  ## Lista os alvos disponiveis
	@echo Observatorio de Mobilidade -- alvos:
	@echo   setup      instala dependencias e cria o venv (uv sync)
	@echo   lint       ruff check + ruff format --check
	@echo   test       roda a suite de testes (pytest)
	@echo   ingest     [Sprint 2] ingestao das fontes para a camada RAW
	@echo   dbt-build  [Sprint 3] build dos modelos dbt
	@echo   train      [Sprint 5] treino do modelo de ML
	@echo   app        [Sprint 6] sobe o app Streamlit
	@echo   all        pipeline reprodutivel disponivel (setup lint test)

setup:  ## Instala dependencias e cria o venv (.venv) via uv
	uv sync

lint:  ## Verifica lint e formatacao com ruff (nao altera arquivos)
	uv run ruff check .
	uv run ruff format --check .

test:  ## Roda a suite de testes (pytest)
	uv run pytest

ingest:  ## Ingestao das fontes (GTFS+INMET+SIDRA) -> RAW Parquet -> DuckDB
	uv run python -m ingestion.run_all

dbt-build:  ## Build dos modelos dbt (staging -> intermediate -> marts) + testes
	uv run dbt build --project-dir transform --profiles-dir transform

train:  ## [Sprint 5] Treino e avaliacao do modelo de ML
	@echo make train: a ser implementado na Sprint 5 -- machine learning.

app:  ## [Sprint 6] Sobe o dashboard Streamlit
	@echo make app: a ser implementado na Sprint 6 -- app Streamlit.

all: setup lint test  ## Executa o pipeline reprodutivel disponivel
