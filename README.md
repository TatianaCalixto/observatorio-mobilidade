# Observatório de Mobilidade Urbana

> Projeto de dados **end-to-end** (Engenharia + Análise + Machine Learning) sobre o
> transporte público de São Paulo, construído como portfólio técnico seguindo a
> metodologia de **documentação viva + agente executor**.

---

## Pergunta de negócio

> Dá para prever atrasos/demanda no transporte público a partir de fatores como dia da
> semana, clima e linha — e onde estão os principais gargalos da rede?

O projeto percorre o ciclo completo de dados — ingestão → modelagem → qualidade →
análise → machine learning → visualização — orbitando uma única pergunta de negócio.
O entregável final é um **app web público** (Streamlit) com dashboard analítico, mapa da
rede e previsões do modelo, sustentado por um pipeline ELT reprodutível e versionado.

**Recorte temporal:** últimos 12 meses (**2025-06-01 a 2026-05-31**).

---

## Metodologia: documentação viva + agente executor

Este repositório é executado a partir de duas fontes de verdade versionadas:

- **[`blueprint.md`](blueprint.md)** — referência funcional: visão geral, fontes de dados,
  arquitetura, stack, módulos e roadmap.
- **`observatorio_mobilidade_planejamento_sprints.xlsx`** — fonte única de verdade
  operacional: backlog de 40 tarefas em 8 sprints, com critérios de aceitação, testes
  obrigatórios, plano de testes, impedimentos e decisões técnicas.

Cada tarefa só é concluída com **testes verdes**, e toda regra de negócio tem **teste de
regressão**. Dúvidas de escopo viram impedimentos registrados, não improvisos.

---

## Stack técnica

| Camada | Ferramenta |
|---|---|
| Linguagem / ambiente | **Python 3.12** gerenciado por **uv** (lockfile versionado) |
| Ingestão | `requests` / `httpx`, GTFS / CSV / APIs públicas |
| Camada RAW | **Parquet** particionado |
| Warehouse | **DuckDB** (analítico, local) |
| Transformação | **dbt-duckdb** (staging → intermediate → marts) |
| Orquestração | **Prefect** |
| Machine Learning | **scikit-learn / XGBoost** + **MLflow** |
| Visualização | **Streamlit** + mapa (pydeck / folium) |
| Qualidade | **ruff**, **pytest**, **pre-commit** |
| CI/CD | **GitHub Actions** |
| Empacotamento | **Dockerfile**, **Makefile** |

---

## Arquitetura (visão geral)

```
fontes públicas ──> ingestão (Python) ──> camada RAW (Parquet particionado)
   GTFS / SPTrans                                  │
   INMET (clima)                          dbt (staging → intermediate → marts)
   IBGE / SIDRA                                    │
   Base dos Dados                         ┌────────┴────────┐
                                      análise (SQL)     feature store
                                          │                  │
                                      Streamlit          modelo (XGBoost)
                                      (dashboard)        + MLflow tracking
```

---

## Estrutura de pastas

```
.
├── ingestion/     # scripts de coleta (GTFS, INMET, IBGE, Base dos Dados) → RAW
├── transform/     # projeto dbt-duckdb (staging → intermediate → marts)
├── ml/            # feature engineering, baseline, modelo, tracking
├── app/           # dashboard Streamlit
├── analysis/      # análise exploratória, notebooks, relatórios
├── tests/         # suíte pytest (incl. regressão de regras de negócio)
├── docs/          # documentação viva, ADRs, diagramas
├── data/
│   ├── raw/       # camada RAW local (Parquet) — NÃO versionada
│   └── staging/   # dados intermediários locais — NÃO versionada
├── blueprint.md   # referência funcional do projeto
└── observatorio_mobilidade_planejamento_sprints.xlsx  # backlog / verdade operacional
```

> `data/`, `*.duckdb`, `*.parquet`, `mlruns/`, `.venv/` e segredos (`.env`) **não são
> versionados** (ver [`.gitignore`](.gitignore)). Configuração local usa `.env` a partir
> de um `.env.example` (a ser criado na Sprint 2).

---

## Roadmap (8 sprints)

| Sprint | Foco | Entregável verificável |
|---|---|---|
| **S1** | Fundação do repositório | `make setup`, lint e testes passando no CI |
| **S2** | Ingestão (Extract & Load) | RAW populada com GTFS + INMET + IBGE de forma idempotente |
| **S3** | Modelagem dbt | `dbt build` verde com testes de qualidade nas 3 camadas |
| **S4** | Análise & métricas | Marts analíticos + métrica de atraso/demanda testada |
| **S5** | Machine Learning | Modelo avaliado com split temporal + baseline + MLflow |
| **S6** | App Streamlit | Dashboard local consumindo marts + modelo |
| **S7** | Orquestração & CI/CD | Pipeline Prefect agendado + CI verde + cobertura ≥ 80% |
| **S8** | Documentação & publicação | App público + README de portfólio + ADRs |

**Status atual:** Sprint 1 em andamento (fundação do repositório).

---

## Reprodutibilidade

O objetivo é que `make all` reproduza o pipeline completo do zero em outra máquina, com
CI verde (lint + pytest + dbt test) em todos os commits da branch principal. Os comandos
padrão (`make setup`, `make lint`, `make test`, `make ingest`, `make dbt-build`,
`make train`, `make app`) serão adicionados ao longo das sprints.
