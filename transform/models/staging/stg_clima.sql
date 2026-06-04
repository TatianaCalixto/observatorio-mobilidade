-- Clima horário por estação (INMET), tipado. Chave = (estacao, data, hora_utc).
with source as (
    select * from {{ source('raw', 'raw_clima') }}
)

select
    cast(estacao as varchar) || '|' || cast(data as varchar) || '|' || cast(hora_utc as varchar)
        as clima_sk,
    cast(data as date)              as data,
    cast(hora_utc as varchar)       as hora_utc,
    cast(estacao as varchar)        as estacao,
    cast(uf as varchar)             as uf,
    try_cast(precipitacao_mm as double) as precipitacao_mm,
    try_cast(temperatura_c as double)   as temperatura_c
from source
