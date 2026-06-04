-- Dimensão de parada (ponto) da rede.
select
    stop_id,
    stop_name,
    stop_lat,
    stop_lon
from {{ ref('stg_gtfs__stops') }}
