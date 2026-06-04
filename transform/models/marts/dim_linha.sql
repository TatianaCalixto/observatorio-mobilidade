-- Dimensão de linha (rota) da rede.
select
    route_id,
    route_short_name,
    route_long_name,
    route_type,
    case route_type
        when 3 then 'Ônibus'
        when 0 then 'Bonde/Tram'
        when 1 then 'Metrô'
        when 2 then 'Trem'
        else cast(route_type as varchar)
    end as modo
from {{ ref('stg_gtfs__routes') }}
