# Métrica central: oferta planejada de viagens

> Regra de negócio crítica do projeto (S04-T01). Definição, cálculo e regressão.
> Contexto da decisão de design: ver **DEC-006** na planilha de planejamento.

## Por que "oferta planejada" (e não "atraso real")

A única fonte de horários é o **GTFS estático da SPTrans** — o serviço **planejado**.
Não há dados **realizados** (tempo real / AVL), então um "atraso real" (realizado −
planejado) **não é mensurável**. A SPTrans, além disso, é **baseada em frequência**
(`frequencies.txt`): cada padrão de viagem opera a um *headway* (intervalo entre
partidas) por janela de horário.

Por isso a métrica central é a **oferta planejada**:

- **`n_viagens`** — número de **partidas planejadas por linha por dia** (proxy de
  oferta/demanda planejada).
- **`headway_med_min`** — **intervalo médio** entre partidas (proxy de **regularidade**).

## Cálculo (determinístico)

Para cada **padrão de viagem** (`trip_id`), a partir de `frequencies.txt`:

```
partidas_dia      = Σ_janelas  (end_secs − start_secs) / headway_secs        [headway_secs > 0]
headway_med_secs  = Σ_janelas (dur · headway_secs) / Σ_janelas dur            [dur = end_secs − start_secs]
```

- Janelas com `headway_secs = 0` são **ignoradas** (guarda de divisão por zero).
- Padrão **sem frequências** → `partidas_dia = 0`, `headway_med_secs = NULL`.

A oferta por **linha e dia** (`fct_viagens_dia`, grão `linha × dia`) soma as `partidas_dia`
dos padrões cujo **serviço opera naquela data** (datação via `calendar.txt`):

```
n_viagens(linha, dia)      = Σ_padrões-ativos  partidas_dia
headway_med_min(linha, dia)= Σ (headway_med_secs · partidas_dia) / Σ partidas_dia / 60
```

O agregado por linha no período está em **`mart_oferta_linha`**.

## Camadas dbt envolvidas

| Camada | Modelo | Papel |
|---|---|---|
| staging | `stg_gtfs__frequencies` | tipa headway e calcula `start_secs`/`end_secs` |
| intermediate | `int_viagens_por_padrao` | **cálculo da oferta por padrão** (partidas/headway) |
| intermediate | `int_servico_datas` | data os serviços (calendar × spine de datas) |
| intermediate | `int_viagens_dia` | oferta por linha × dia |
| marts | `fct_viagens_dia` | fato (grão linha × dia) |
| marts | `mart_oferta_linha` | métrica agregada por linha |

## Caso manual conhecido (trava de regressão)

Padrão `T1` com duas janelas:

| janela | duração | headway | partidas |
|---|---|---|---|
| 0–3600s | 3600s | 600s | 6,0 |
| 3600–7200s | 3600s | 1200s | 3,0 |
| **total** | 7200s | — | **9,0** |

`headway_med = (3600·600 + 3600·1200) / 7200 = 900s`. Uma terceira janela com
`headway = 0` é ignorada. Um padrão `T2` sem frequências → `partidas = 0`,
`headway = NULL`.

Esses valores são travados pelo **dbt unit test**
`int_viagens_por_padrao::metrica_oferta_partidas_e_headway`
(`transform/models/intermediate/_int_unit_tests.yml`), executado em todo `dbt build`/CI.
Se o cálculo da métrica mudar, o teste falha — a regressão é barrada.
