-- Fato de oferta planejada de viagens. Grão: (linha, dia).
-- Métricas: n_viagens (oferta/demanda planejada) e headway_med_min (regularidade).
-- Como só há GTFS estático (sem realizado), "atraso" é reenquadrado como headway/regularidade
-- planejada — ver DEC-006.
with base as (
    select * from {{ ref('int_viagens_dia') }}
)

select
    viagem_dia_sk,
    route_id,
    data,
    iso_dia_semana,
    round(n_viagens)                  as n_viagens,
    headway_med_secs / 60.0           as headway_med_min,
    paradas_por_viagem_med,
    n_padroes
from base
