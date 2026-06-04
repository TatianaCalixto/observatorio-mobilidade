-- Base de viagens planejadas por linha e dia (oferta), datando os padrões via calendar.
-- Expande cada padrão (trip) pelas datas em que seu serviço opera e agrega por (linha, dia).
-- Grão: (route_id, data). É a base do fato fct_viagens_dia.
with padroes as (
    select * from {{ ref('int_viagens_por_padrao') }}
),

servico_datas as (
    select * from {{ ref('int_servico_datas') }}
)

select
    p.route_id || '|' || cast(sd.data as varchar) as viagem_dia_sk,
    p.route_id,
    sd.data,
    sd.iso_dia_semana,
    sum(p.partidas_dia)                                                   as n_viagens,
    sum(p.headway_med_secs * p.partidas_dia) / nullif(sum(p.partidas_dia), 0)
        as headway_med_secs,
    sum(p.n_paradas * p.partidas_dia) / nullif(sum(p.partidas_dia), 0)    as paradas_por_viagem_med,
    count(distinct p.trip_id)                                            as n_padroes
from padroes p
inner join servico_datas sd on p.service_id = sd.service_id
group by p.route_id, sd.data, sd.iso_dia_semana
