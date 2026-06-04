# ADRs — Architecture Decision Records

Decisões técnicas não óbvias do projeto, em formato curto (contexto → decisão →
alternativas → consequências). O log do dia a dia, mais granular, está na aba
**Decisões** da planilha ([docs/sprints_decisoes.md](../sprints_decisoes.md), DEC-001…007).

---

## ADR-001 — DuckDB local-first (em vez de data warehouse na nuvem)

**Contexto.** O projeto é um portfólio que precisa ser reproduzível por terceiros, sem
custo e sem infra obrigatória.

**Decisão.** Usar **DuckDB** (arquivo local `mobilidade.duckdb`) como warehouse analítico,
com **dbt-duckdb** para as transformações.

**Alternativas.** BigQuery free tier (exige conta GCP, credenciais, e quebra o "local-first");
Postgres (mais setup, menos colunar para análise).

**Consequências.** Roda 100% na máquina e no CI; SQL analítico completo; zero custo. Em
escala real, a migração para BigQuery está documentada como evolução, não requisito.

---

## ADR-002 — Transformações sempre via dbt, em camadas

**Contexto.** Regra inegociável do projeto: nada de marts montados "na mão".

**Decisão.** Toda transformação passa por **dbt** em camadas explícitas: `staging`
(limpeza/tipagem) → `intermediate` (joins/enriquecimento) → `marts` (modelo dimensional),
com testes `not_null`/`unique`/`relationships` e **dbt unit tests** para a métrica.

**Alternativas.** SQL avulso/notebooks (sem testes nem linhagem); pandas no Python (perde a
linhagem declarativa e os testes de qualidade).

**Consequências.** Linhagem auditável, testes de qualidade declarativos, `dbt docs`. O custo
é a curva do dbt e a necessidade de "semear" o warehouse no CI a partir de fixtures.

---

## ADR-003 — Fonte do GTFS: mirror público (em vez do feed com token da SPTrans)

**Contexto.** O GTFS estático oficial da SPTrans exige token do portal de desenvolvedores —
o que quebraria a reprodutibilidade por terceiros. (Impedimento IMP-002.)

**Decisão.** Usar o **mirror público do Mobility Database** (`mdb-latest`), que re-hospeda a
versão mais recente do feed da SPTrans, sem token. URL default no `config`, sobrescrevível
por `.env`.

**Alternativas.** Token oficial SPTrans (terceiros não reproduziriam); backup TUMI Datahub
(desatualizado, 2024); transitfeeds/transitland (403/401/arquivado).

**Consequências.** Reprodutível sem credencial. Se a URL do mirror mudar, basta reapontar
(o catálogo do MobilityData é a fonte estável). Ver DEC-005.

---

## ADR-004 — Métrica central: oferta planejada, grão (linha × dia)

**Contexto.** O GTFS é **estático** (planejado), sem dados realizados nem tempo real — então
"atraso real" não é mensurável. A SPTrans é baseada em **frequência** (`frequencies.txt`).
(Impedimento IMP-003.)

**Decisão.** A métrica de negócio é a **oferta planejada**: nº de partidas/dia por linha
(derivado das janelas de frequência) + **headway médio** (regularidade). O fato `fct_viagens_dia`
tem grão **(linha, dia)**, datado via `calendar.txt`. O cálculo é travado por um **dbt unit
test** (caso manual, sinal, dados faltantes, divisão por zero).

**Alternativas.** Headway por linha sem datar (perde a série temporal para clima); atraso
sintético como métrica de verdade (desonesto).

**Consequências.** Métrica honesta com a natureza do dado e auditável. O "atraso" vira
**regularidade/oferta**; o clima não a afeta (resultado real). Ver DEC-006 e
[`docs/metrica_oferta.md`](../metrica_oferta.md).

---

## ADR-005 — Alvo do ML: demanda simulada e explicitamente rotulada

**Contexto.** A oferta planejada é quase determinística (varia só por linha × tipo-de-dia),
o que tornaria o ML vazio: modelo ~perfeito, clima irrelevante, split temporal sem sentido.

**Decisão.** O alvo do ML é uma **`demanda_estimada_sim`**: a oferta real **modulada por
clima + tipo-de-dia + ruído** com seed fixa, **rotulada como simulada** (nome de coluna,
docs e banner no app). Vive só no pipeline `ml/`; os marts e a métrica de verdade
permanecem 100% reais.

**Alternativas.** Alvo determinístico real (ML/app sem conteúdo preditivo); buscar dados
realizados (GTFS-Realtime/AVL — fora de escopo, exige token, pode não cobrir a janela).

**Consequências.** O ML passa a ter sinal real para aprender (o clima importa), demonstrando
o pipeline completo de forma honesta via rotulagem. Ver DEC-007.

---

## ADR-006 — XGBoost como modelo principal, com baseline honesto

**Contexto.** É preciso uma referência justa para avaliar o modelo, com split **temporal**
(treino nos primeiros meses, validação nos últimos) e sem vazamento.

**Decisão.** Baseline = **média por linha** (ignora o clima de propósito). Modelo principal =
**XGBoost** com hiperparâmetros fixos (seed) sobre as mesmas features. Experimentos no
**MLflow**; o melhor (menor RMSE) é serializado para o app.

**Alternativas.** Só regressão linear (não captura interações clima×oferta); deep learning
(injustificado para o volume e o problema).

**Consequências.** XGBoost (MAE 6,8) supera o baseline (MAE 17,9) ao capturar o efeito do
clima — comparação reprodutível e registrada. A bateria de features sem vazamento (S05-T01)
trava regressões.
