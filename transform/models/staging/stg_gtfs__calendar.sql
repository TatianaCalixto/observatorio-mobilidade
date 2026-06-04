-- Calendário de serviços do GTFS: flags por dia da semana + vigência.
with source as (
    select * from {{ source('raw', 'raw_gtfs_calendar') }}
)

select
    cast(service_id as varchar)  as service_id,
    try_cast(monday as integer)    as monday,
    try_cast(tuesday as integer)   as tuesday,
    try_cast(wednesday as integer) as wednesday,
    try_cast(thursday as integer)  as thursday,
    try_cast(friday as integer)    as friday,
    try_cast(saturday as integer)  as saturday,
    try_cast(sunday as integer)    as sunday,
    try_strptime(cast(start_date as varchar), '%Y%m%d')::date as start_date,
    try_strptime(cast(end_date as varchar), '%Y%m%d')::date   as end_date
from source
