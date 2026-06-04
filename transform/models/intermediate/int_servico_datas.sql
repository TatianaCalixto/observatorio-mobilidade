-- "Data" os serviços: para cada data da janela do projeto, quais service_id operam,
-- cruzando o spine de datas com o calendar (flags de dia da semana + vigência).
-- Grão: (service_id, data).
with datas as (
    select unnest(
        generate_series(
            date '{{ var("data_inicio") }}',
            date '{{ var("data_fim") }}',
            interval 1 day
        )
    )::date as data
),

calendario as (
    select * from {{ ref('stg_gtfs__calendar') }}
)

select
    c.service_id || '|' || cast(d.data as varchar) as servico_data_sk,
    c.service_id,
    d.data,
    isodow(d.data) as iso_dia_semana  -- 1=segunda ... 7=domingo
from datas d
inner join calendario c
    on d.data between c.start_date and c.end_date
    and (
        (isodow(d.data) = 1 and c.monday = 1)
        or (isodow(d.data) = 2 and c.tuesday = 1)
        or (isodow(d.data) = 3 and c.wednesday = 1)
        or (isodow(d.data) = 4 and c.thursday = 1)
        or (isodow(d.data) = 5 and c.friday = 1)
        or (isodow(d.data) = 6 and c.saturday = 1)
        or (isodow(d.data) = 7 and c.sunday = 1)
    )
