-- Viagens planejadas (uma sequência de paradas de uma linha), tipadas do GTFS RAW.
with source as (
    select * from {{ source('raw', 'raw_gtfs_trips') }}
)

select
    cast(trip_id as varchar)      as trip_id,
    cast(route_id as varchar)     as route_id,
    cast(service_id as varchar)   as service_id,
    cast(trip_headsign as varchar) as trip_headsign,
    try_cast(direction_id as integer) as direction_id
from source
