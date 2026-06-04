-- Linhas (rotas) da rede, tipadas a partir do GTFS RAW.
with source as (
    select * from {{ source('raw', 'raw_gtfs_routes') }}
)

select
    cast(route_id as varchar)         as route_id,
    cast(route_short_name as varchar) as route_short_name,
    cast(route_long_name as varchar)  as route_long_name,
    try_cast(route_type as integer)   as route_type
from source
