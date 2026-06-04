-- Horários planejados: cada parada de cada viagem. Chave = (trip_id, stop_sequence).
with source as (
    select * from {{ source('raw', 'raw_gtfs_stop_times') }}
)

select
    cast(trip_id as varchar) || '-' || cast(stop_sequence as varchar) as stop_time_id,
    cast(trip_id as varchar)        as trip_id,
    cast(stop_id as varchar)        as stop_id,
    try_cast(stop_sequence as integer) as stop_sequence,
    cast(arrival_time as varchar)   as arrival_time,
    cast(departure_time as varchar) as departure_time
from source
