-- Frequências planejadas (SPTrans é baseado em headway): janela start..end e headway_secs.
-- Inclui os segundos-desde-a-meia-noite (GTFS permite horas >= 24h).
with source as (
    select * from {{ source('raw', 'raw_gtfs_frequencies') }}
)

select
    cast(trip_id as varchar) || '-' || cast(start_time as varchar) as frequency_id,
    cast(trip_id as varchar)         as trip_id,
    cast(start_time as varchar)      as start_time,
    cast(end_time as varchar)        as end_time,
    try_cast(headway_secs as integer) as headway_secs,
    try_cast(split_part(start_time, ':', 1) as integer) * 3600
        + try_cast(split_part(start_time, ':', 2) as integer) * 60
        + try_cast(split_part(start_time, ':', 3) as integer) as start_secs,
    try_cast(split_part(end_time, ':', 1) as integer) * 3600
        + try_cast(split_part(end_time, ':', 2) as integer) * 60
        + try_cast(split_part(end_time, ':', 3) as integer) as end_secs
from source
