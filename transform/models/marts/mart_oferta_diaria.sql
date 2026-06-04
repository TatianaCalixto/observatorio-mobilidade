-- Série diária da rede: oferta total e nº de linhas ativas por dia, com atributos de
-- tempo e clima. Base analítica para sazonalidade, correlação com clima e o ML.
-- Grão: data.
with diario as (
    select
        data,
        sum(n_viagens)            as total_viagens,
        count(distinct route_id)  as n_linhas_ativas,
        avg(headway_med_min)      as headway_med_min
    from {{ ref('fct_viagens_dia') }}
    group by data
)

select
    t.data,
    t.ano,
    t.mes,
    t.iso_dia_semana,
    t.dia_semana,
    t.fim_de_semana,
    d.total_viagens,
    d.n_linhas_ativas,
    round(d.headway_med_min, 2)   as headway_med_min,
    c.precipitacao_total_mm,
    c.temperatura_media_c,
    c.choveu
from diario d
inner join {{ ref('dim_tempo') }} t using (data)
left join {{ ref('dim_clima') }} c using (data)
