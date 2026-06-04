-- Agrega o clima horário (estação A701) para o grão diário, dentro da janela do projeto.
-- Grão: data.
with horario as (
    select * from {{ ref('stg_clima') }}
)

select
    data,
    any_value(estacao)              as estacao,
    sum(precipitacao_mm)            as precipitacao_total_mm,
    avg(temperatura_c)              as temperatura_media_c,
    min(temperatura_c)              as temperatura_min_c,
    max(temperatura_c)              as temperatura_max_c,
    count(*)                        as horas_observadas
from horario
where data between date '{{ var("data_inicio") }}' and date '{{ var("data_fim") }}'
group by data
