-- Um registro por padrão de viagem (trip_id), com a oferta planejada derivada das
-- frequências (SPTrans é baseado em headway): partidas/dia, headway médio e nº de paradas.
-- Grão: trip_id. Sem fan-out (agregações por trip_id antes do join).
with trips as (
    select trip_id, route_id, service_id from {{ ref('stg_gtfs__trips') }}
),

freq as (
    select
        trip_id,
        -- nº de partidas no dia = soma, por janela, de duração/headway
        sum(case when headway_secs > 0 then (end_secs - start_secs) / headway_secs else 0 end)
            as partidas_dia,
        sum(case when headway_secs > 0 then (end_secs - start_secs) else 0 end) as duracao_total_secs,
        sum(case when headway_secs > 0 then (end_secs - start_secs) * headway_secs else 0 end)
            as headway_pond
    from {{ ref('stg_gtfs__frequencies') }}
    group by trip_id
),

paradas as (
    select trip_id, count(*) as n_paradas
    from {{ ref('stg_gtfs__stop_times') }}
    group by trip_id
)

select
    t.trip_id,
    t.route_id,
    t.service_id,
    coalesce(p.n_paradas, 0)     as n_paradas,
    coalesce(f.partidas_dia, 0)  as partidas_dia,
    case when f.duracao_total_secs > 0 then f.headway_pond / f.duracao_total_secs end
        as headway_med_secs
from trips t
left join freq f on t.trip_id = f.trip_id
left join paradas p on t.trip_id = p.trip_id
