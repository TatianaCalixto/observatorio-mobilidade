# Orquestração do pipeline (Prefect)

O pipeline **ingestão → dbt build → treino** é orquestrado por um flow Prefect
(`orchestration/flow.py`), com retries nas etapas de rede e logging por task.

## Rodar uma vez (local)

```bash
uv run python -m orchestration.flow
```

Reconstrói a camada RAW, o DuckDB, os marts (dbt) e o modelo serializado, de ponta a
ponta. As etapas são idempotentes.

## Agendar (schedule diário)

O deployment `observatorio-pipeline/diario` roda **todos os dias às 04:00**
(`cron = "0 4 * * *"`, ver `orchestration/deployment.py`). Para servir o deployment
localmente — um processo de longa duração que executa runs agendados e manuais:

```bash
uv run python -m orchestration.deployment
```

## Disparar manualmente

Com o `serve` acima rodando em outro terminal:

```bash
uv run prefect deployment run 'observatorio-pipeline/diario'
```

A UI do Prefect (`uv run prefect server start`) mostra os runs, estados e logs.

## Etapas do flow

| Task | O que faz | Retries |
|---|---|---|
| `task_ingestao` | GTFS + INMET + SIDRA → RAW Parquet → DuckDB | 3 (rede) |
| `task_dbt_build` | `dbt build` (staging → intermediate → marts) + testes | 2 |
| `task_treino` | baseline + XGBoost + MLflow + serialização do modelo | 1 |

## Execução portátil (Docker)

Imagem multi-stage (ambiente via `uv`), definida em `Dockerfile`:

```bash
docker build -t observatorio-mobilidade .

# Roda a suíte (lint + testes, modo reduzido com fixtures)
docker run --rm observatorio-mobilidade make all

# Sobe o app (mapeando a porta)
docker run --rm -p 8501:8501 observatorio-mobilidade

# Roda o pipeline completo (precisa de rede; monte volumes para persistir data/)
docker run --rm observatorio-mobilidade python -m orchestration.flow
```

