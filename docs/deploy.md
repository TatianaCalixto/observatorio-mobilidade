# Publicar o app (Streamlit Community Cloud)

O app é preparado para rodar no [Streamlit Community Cloud](https://share.streamlit.io)
de forma autocontida — ele resolve os dados/modelo automaticamente:

`app.data.caminho_db()` procura, nesta ordem: variável de ambiente `DUCKDB_PATH` →
`mobilidade.duckdb` local → **`app_data/marts.duckdb`** (snapshot de demo versionado). O
modelo segue a mesma lógica (`app_data/modelo_demanda.joblib`). Então, no Cloud (sem o
warehouse local), o app usa o snapshot commitado.

## Artefatos do deploy (versionados por exceção)

| Arquivo | Conteúdo | Tamanho |
|---|---|---|
| `app_data/marts.duckdb` | marts + dimensões + fato (snapshot dos dados **públicos**) | ~14 MB |
| `app_data/modelo_demanda.joblib` | modelo XGBoost serializado | ~0,9 MB |
| `requirements.txt` | dependências de runtime do app (sem dbt/prefect/mlflow) | — |

> São dados **curados e públicos** (GTFS/INMET/IBGE), não dados brutos pesados — incluídos
> só para o demo público funcionar. Para regenerar: `make ingest && make dbt-build && make train`.

## Passos (manuais, na sua conta)

1. Acesse <https://share.streamlit.io> e faça login com o GitHub.
2. **New app** → repositório `TatianaCalixto/observatorio-mobilidade`, branch `main`,
   arquivo principal **`app/main.py`**.
3. **Deploy**. O Cloud instala o `requirements.txt` e sobe o app.
4. Smoke manual: confirme que **Visão Geral** (KPIs), **Mapa da rede** e **Previsões**
   carregam — e que o banner de "demanda simulada" aparece.
5. Cole o link público no topo do `README.md`.
