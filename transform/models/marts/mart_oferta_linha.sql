-- Mart analítico da MÉTRICA de oferta por linha (agregado de fct_viagens_dia).
-- Métrica central do projeto: oferta planejada (partidas/dia) e headway (regularidade),
-- separando dia útil x fim de semana. Ver docs/metrica_oferta.md e DEC-006.
with f as (
    select * from {{ ref('fct_viagens_dia') }}
)

select
    route_id,
    count(distinct data)                                                  as dias_operados,
    round(avg(n_viagens), 1)                                              as media_viagens_dia,
    round(avg(case when iso_dia_semana <= 5 then n_viagens end), 1)       as media_viagens_dia_util,
    round(avg(case when iso_dia_semana >= 6 then n_viagens end), 1)       as media_viagens_fim_semana,
    round(avg(headway_med_min), 1)                                        as headway_med_min,
    sum(n_viagens)                                                        as total_viagens_periodo
from f
group by route_id
