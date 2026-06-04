-- Dimensão de clima diário (estação A701, São Paulo). Chave = data.
select
    data,
    estacao,
    precipitacao_total_mm,
    temperatura_media_c,
    temperatura_min_c,
    temperatura_max_c,
    (precipitacao_total_mm > 0) as choveu
from {{ ref('int_clima_diario') }}
