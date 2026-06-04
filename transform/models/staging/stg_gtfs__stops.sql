-- Paradas (pontos) da rede, tipadas a partir do GTFS RAW.
with source as (
    select * from {{ source('raw', 'raw_gtfs_stops') }}
)

select
    cast(stop_id as varchar)   as stop_id,
    cast(stop_name as varchar) as stop_name,
    try_cast(stop_lat as double) as stop_lat,
    try_cast(stop_lon as double) as stop_lon
from source
