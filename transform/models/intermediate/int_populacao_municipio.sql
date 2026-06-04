-- População por município (IBGE/SIDRA), preparada como contexto de região.
-- Grão: regiao_codigo (código IBGE do município).
select
    regiao_codigo,
    regiao_nome,
    populacao
from {{ ref('stg_populacao') }}
