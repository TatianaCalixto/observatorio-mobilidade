# Blueprint — Observatório de Mobilidade Urbana

> Projeto de dados end-to-end (Engenharia + Análise + ML) construído como portfólio
> técnico, seguindo a metodologia de **documentação viva + agente executor**.

---

## 1. Visão geral

**Pergunta de negócio que sustenta o projeto:**
> Dá para prever atrasos/demanda no transporte público a partir de fatores como dia
> da semana, clima e linha — e onde estão os principais gargalos da rede?

O projeto percorre o ciclo completo de dados — ingestão, modelagem, qualidade,
análise, machine learning e visualização — orbitando uma única pergunta de negócio
para manter coesão. O entregável final é um **app web público** (Streamlit) com
dashboard analítico, mapa da rede e previsões do modelo, sustentado por um pipeline
ELT reprodutível e versionado.

### Objetivos
- Demonstrar domínio de uma **Modern Data Stack** "local-first" reprodutível.
- Mostrar rigor de engenharia: testes de dados, CI/CD, tracking de experimentos.
- Entregar análise com storytelling e um modelo preditivo com baseline honesto.
- Produzir um repositório GitHub que recrutador técnico reconhece em segundos.

### Não-objetivos (escopo controlado)
- Não é um sistema de produção em tempo real (ingestão é batch/agendada).
- Não buscar SOTA de ML — baseline sólido e bem avaliado é suficiente.
- Não depende de infra paga; cloud (BigQuery) é evolução documentada, não requisito.

---

## 2. Fontes de dados (públicas, gratuitas)

| Fonte | Conteúdo | Acesso | Uso no projeto |
|---|---|---|---|
| **GTFS — SPTrans (São Paulo)** | Linhas, paradas, horários, trajetos | GTFS estático + API pública | Estrutura da rede, horários planejados |
| **Base dos Dados** (`basedosdados`) | Datasets municipais/transporte já tratados | Python / BigQuery público | Enriquecimento, dados socioeconômicos |
| **INMET** | Clima por estação meteorológica | CSV / API | Feature de clima para o modelo |
| **IBGE / SIDRA** | População por região | API SIDRA | Normalização de demanda por área |

> **Parâmetros do projeto:** cidade/feed GTFS = **São Paulo/SPTrans**; destino do
> warehouse = **DuckDB local** (alternativa documentada: BigQuery free tier);
> **recorte temporal = últimos 12 meses (2025-06-01 a 2026-05-31)** — aplicado a clima
> e à série de viagens/atrasos, e usado para definir o split temporal do ML (treino nos
> primeiros meses, validação nos últimos).

---

## 3. Arquitetura

```
fontes públicas ──> ingestão (Python) ──> camada RAW (Parquet particionado)
        │                                         │
   Base dos Dados                            dbt (staging → intermediate → marts)
   GTFS / SPTrans                                 │
   INMET (clima)                          ┌───────┴────────┐
   IBGE / SIDRA                       análise (SQL)     feature store
                                          │                  │
                                      Streamlit          modelo (XGBoost/sklearn)
                                       (dashboard)        + MLflow tracking
```

### Princípios de arquitetura
- **Local-first**: roda 100% na máquina; nenhuma dependência paga obrigatória.
- **Camadas explícitas**: `raw` (imutável) → `staging` → `intermediate` → `marts`.
- **Idempotência**: re-execução do pipeline não duplica nem corrompe dados.
- **Reprodutibilidade**: ambiente travado (lockfile), seeds fixas no ML.

---

## 4. Stack técnica

| Camada | Ferramenta | Justificativa |
|---|---|---|
| Linguagem | **Python 3.12** | Padrão de mercado em dados |
| Ambiente | **uv** (ou Poetry) | Gestão de deps rápida e reprodutível |
| Ingestão | `requests`, `basedosdados`, `httpx` | APIs públicas + downloads GTFS |
| Formato RAW | **Parquet** particionado | Colunar, eficiente, padrão de lake |
| Warehouse | **DuckDB** | Analítico, zero infra, SQL completo |
| Transformação | **dbt-duckdb** | Camadas + testes de qualidade declarativos |
| Orquestração | **Prefect** | Schedules, retries, observabilidade |
| ML | **scikit-learn / XGBoost** + **MLflow** | Modelo + tracking de experimentos |
| Visualização | **Streamlit** + **pydeck/folium** | App web compartilhável com mapa |
| Qualidade | **ruff**, **pytest**, **pre-commit** | Lint, testes, gates antes do commit |
| CI/CD | **GitHub Actions** | Roda `dbt test` + `pytest` a cada push |
| Empacotamento | **Dockerfile**, **Makefile** | Execução portátil e comandos padronizados |

---

## 5. Módulos do projeto

### M1 — Fundação do repositório
Estrutura de pastas, ambiente (uv/lockfile), `ruff` + `pre-commit`, `Makefile`,
esqueleto de testes, README inicial e estrutura de docs vivos.

### M2 — Ingestão (Extract & Load)
Scripts de download/coleta de GTFS, INMET, IBGE e Base dos Dados, gravando em
camada RAW (Parquet particionado) de forma idempotente, com logging e validação
básica de schema na entrada.

### M3 — Modelagem dbt (Transform)
Projeto dbt-duckdb com camadas `staging` (limpeza/tipagem), `intermediate`
(joins e enriquecimento clima/população) e `marts` (modelo dimensional:
fato de viagens/atrasos + dimensões linha, parada, tempo, clima). Testes de
qualidade em cada camada.

### M4 — Análise exploratória & métricas
Análises SQL/notebook respondendo a pergunta de negócio: gargalos da rede,
sazonalidade, correlação clima × atraso. Consolidação em tabelas `marts`
prontas para o dashboard.

### M5 — Machine Learning
Feature engineering a partir dos marts, baseline (regressão/heurística),
modelo principal (XGBoost), avaliação honesta (split temporal, métricas claras),
tracking com MLflow e serialização do modelo para o app.

### M6 — App Streamlit
Dashboard com KPIs, mapa interativo da rede (gargalos), explorador de linhas e
seção de previsões consumindo o modelo treinado. Deploy gratuito (Streamlit
Community Cloud).

### M7 — Orquestração & CI/CD
Pipeline Prefect orquestrando ingestão → dbt → treino, com schedule e retries.
GitHub Actions rodando lint, `pytest` e `dbt test`. Dockerfile para execução
portátil.

### M8 — Documentação & portfólio
README com storytelling da pergunta de negócio, diagrama de arquitetura, GIF do
app, instruções de reprodução, decisões técnicas (ADRs leves) e preparação para
publicação (skill `portfolio-docs`).

---

## 6. Roadmap de sprints (proposta)

| Sprint | Foco | Módulos | Entregável verificável |
|---|---|---|---|
| **S1** | Fundação | M1 | Repo executável: `make setup`, lint e testes passando no CI |
| **S2** | Ingestão | M2 | RAW populada com GTFS+INMET+IBGE de forma idempotente |
| **S3** | Modelagem | M3 | dbt build verde com testes de qualidade nas 3 camadas |
| **S4** | Análise | M4 | Marts analíticos + relatório respondendo a pergunta de negócio |
| **S5** | ML | M5 | Modelo treinado, avaliado e registrado no MLflow + baseline |
| **S6** | App | M6 | Streamlit local funcional consumindo marts + modelo |
| **S7** | Orquestração/CI | M7 | Pipeline Prefect agendado + GitHub Actions verde |
| **S8** | Publicação | M8 | App no ar (link público) + README de portfólio finalizado |

### Regras de execução (documentação viva)
- Cada sprint só fecha com seu **entregável verificável** demonstrado.
- **Testes obrigatórios** acompanham cada tarefa (proteção contra regressão).
- Dúvidas/impedimentos param a execução e voltam para decisão (não improvisar escopo).
- Ao fim de cada fase, rodar a skill `phase-review` antes de planejar a próxima.

---

## 7. Critérios de sucesso do projeto
- `make all` reproduz o pipeline completo do zero em outra máquina.
- CI verde (lint + pytest + dbt test) em todos os commits da branch principal.
- App público acessível por link, respondendo à pergunta de negócio.
- README que comunica método e resultado em menos de 2 minutos de leitura.
