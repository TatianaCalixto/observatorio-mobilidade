-- População por município (IBGE/SIDRA), tipada. Chave = regiao_codigo (código IBGE).
with source as (
    select * from {{ source('raw', 'raw_populacao') }}
)

select
    cast(regiao_codigo as varchar) as regiao_codigo,
    cast(regiao_nome as varchar)   as regiao_nome,
    cast(nivel as varchar)         as nivel,
    try_cast(valor as bigint)      as populacao,
    cast(unidade as varchar)       as unidade
from source
