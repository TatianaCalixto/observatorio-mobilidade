-- Dimensão de tempo: um registro por dia na janela do projeto.
with datas as (
    select unnest(
        generate_series(
            date '{{ var("data_inicio") }}',
            date '{{ var("data_fim") }}',
            interval 1 day
        )
    )::date as data
)

select
    data,
    extract(year from data)  as ano,
    extract(month from data) as mes,
    extract(day from data)   as dia,
    isodow(data)             as iso_dia_semana,  -- 1=segunda ... 7=domingo
    strftime(data, '%A')     as dia_semana,
    strftime(data, '%B')     as nome_mes,
    (isodow(data) in (6, 7)) as fim_de_semana
from datas
