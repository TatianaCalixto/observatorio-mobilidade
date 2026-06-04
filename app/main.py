"""App Streamlit do Observatório de Mobilidade.

Executar: ``uv run streamlit run app/main.py`` (ou ``make app``).

A lógica de dados/predição/mapa vive em ``app.data`` / ``app.predict`` / ``app.mapa``
(testável). Este arquivo é a UI fina: ``render()`` só roda quando o script é executado
(guarda ``__name__ == "__main__"``), para que importar o módulo nos testes não dispare a UI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ao rodar `streamlit run app/main.py`, o Streamlit coloca a pasta `app/` no sys.path
# (não a raiz do repo). Garantimos a raiz no path para importar os pacotes do projeto
# (ingestion, ml, analysis, app).
_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

PAGINAS = ["Visão Geral", "KPIs & Análises", "Mapa da Rede", "Previsões"]


def render() -> None:
    import streamlit as st

    from app import data as appdata

    st.set_page_config(page_title="Observatório de Mobilidade", page_icon="🚌", layout="wide")
    st.sidebar.title("🚌 Observatório de Mobilidade")
    st.sidebar.caption("Transporte público de São Paulo · dados GTFS/INMET/IBGE")
    pagina = st.sidebar.radio("Navegação", PAGINAS)

    try:
        con = appdata.get_con()
    except Exception as exc:  # noqa: BLE001 - mostrar erro amigável na UI
        st.error(
            "Não foi possível abrir o warehouse (DuckDB). "
            f"Rode `make ingest` e `make dbt-build` primeiro.\n\n{exc}"
        )
        return

    if pagina == "Visão Geral":
        _pagina_visao_geral(st, appdata, con)
    elif pagina == "KPIs & Análises":
        _pagina_kpis(st, appdata, con)
    elif pagina == "Mapa da Rede":
        _pagina_mapa(st, appdata, con)
    elif pagina == "Previsões":
        _pagina_previsoes(st, appdata, con)


def _pagina_visao_geral(st, appdata, con) -> None:
    st.title("Visão Geral da rede")
    with st.spinner("Carregando KPIs..."):
        kpis = appdata.kpis_gerais(con)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Linhas", f"{kpis['n_linhas']:,}")
    c2.metric("Paradas", f"{kpis['n_paradas']:,}")
    c3.metric("Oferta média (dia útil)", f"{kpis['oferta_util']:,.0f}")
    c4.metric("Headway médio (min)", f"{kpis['headway_med_min']:.1f}")

    st.subheader("Oferta planejada diária")
    serie = appdata.oferta_diaria(con)
    if serie.height == 0:
        st.info("Sem dados na série diária. Rode a ingestão e o dbt build.")
        return
    st.line_chart(serie.to_pandas().set_index("data")["total_viagens"])
    st.caption(
        "Métrica = **oferta planejada** (partidas/dia) a partir do GTFS estático. "
        "Ver `docs/metrica_oferta.md`."
    )


def _pagina_kpis(st, appdata, con) -> None:
    from analysis.queries import agregado_clima, linhas_pior_headway, sazonalidade_dia_semana

    st.title("KPIs & Análises")

    inicio, fim = appdata.periodo_disponivel(con)
    col_periodo, col_linha = st.columns([2, 1])
    intervalo = col_periodo.date_input(
        "Período", value=(inicio, fim), min_value=inicio, max_value=fim
    )
    linhas = appdata.listar_linhas(con)
    opcoes = ["Todas as linhas", *linhas["route_short_name"].to_list()]
    escolha = col_linha.selectbox("Linha", opcoes)

    if not isinstance(intervalo, tuple) or len(intervalo) != 2:
        st.info("Selecione um intervalo de datas (início e fim).")
        return
    data_inicio, data_fim = intervalo

    if escolha == "Todas as linhas":
        serie = appdata.oferta_diaria(con, data_inicio, data_fim)
        coluna_valor = "total_viagens"
    else:
        route_id = linhas.filter(linhas["route_short_name"] == escolha)["route_id"][0]
        serie = appdata.oferta_diaria_linha(con, route_id, data_inicio, data_fim)
        coluna_valor = "n_viagens"

    if serie.height == 0:
        st.info("Nenhum dado no período/linha selecionados.")
        return

    pdf = serie.to_pandas()
    c1, c2, c3 = st.columns(3)
    c1.metric("Oferta média/dia", f"{pdf[coluna_valor].mean():,.0f}")
    c2.metric("Headway médio (min)", f"{pdf['headway_med_min'].mean():.1f}")
    c3.metric("Dias no período", f"{len(pdf):,}")

    st.subheader("Oferta planejada ao longo do tempo")
    st.line_chart(pdf.set_index("data")[coluna_valor])

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Sazonalidade por dia da semana")
        saz = sazonalidade_dia_semana(con, data_inicio, data_fim).to_pandas()
        st.bar_chart(saz.set_index("dia_semana")["media_viagens_dia"])
    with col_b:
        st.subheader("Oferta por condição de chuva")
        clima = agregado_clima(con).to_pandas()
        st.bar_chart(clima.set_index("condicao")["oferta_media"])

    st.subheader("Gargalos de regularidade (maior headway)")
    st.dataframe(linhas_pior_headway(con, n=10).to_pandas(), use_container_width=True)


def _pagina_mapa(st, appdata, con) -> None:
    import pydeck as pdk

    from app.mapa import preparar_paradas

    st.title("Mapa da rede — movimento das paradas")
    limite = st.slider("Nº de paradas (mais movimentadas)", 100, 5000, 1500, step=100)
    df = preparar_paradas(con, limite=limite)
    if df.height == 0:
        st.info("Sem paradas georreferenciadas disponíveis.")
        return

    pdf = df.to_pandas()
    pdf["raio"] = 30 + pdf["intensidade"] * 220
    pdf["g"] = (180 * (1 - pdf["intensidade"])).astype(int)
    camada = pdk.Layer(
        "ScatterplotLayer",
        data=pdf,
        get_position=["stop_lon", "stop_lat"],
        get_radius="raio",
        get_fill_color=[255, "g", 40, 160],
        pickable=True,
    )
    vista = pdk.ViewState(
        latitude=float(pdf["stop_lat"].median()),
        longitude=float(pdf["stop_lon"].median()),
        zoom=10,
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[camada],
            initial_view_state=vista,
            tooltip={"text": "{stop_name}\nPassagens: {n_passagens}"},
        )
    )
    st.caption(
        "Intensidade = movimento da parada (nº de passagens no GTFS). "
        "Paradas sem coordenada são omitidas."
    )


DIAS_SEMANA = {
    "Segunda": 1,
    "Terça": 2,
    "Quarta": 3,
    "Quinta": 4,
    "Sexta": 5,
    "Sábado": 6,
    "Domingo": 7,
}


def _pagina_previsoes(st, appdata, con) -> None:
    from app.predict import get_artefato, montar_features, prever_demanda

    st.title("Previsões de demanda")
    st.warning(
        "⚠️ **Demanda simulada (ilustrativa).** Não há dado de demanda realizada com GTFS "
        "estático; o alvo é simulado a partir da oferta planejada + clima + ruído (ver DEC-007). "
        "Serve para demonstrar o pipeline de ML."
    )

    try:
        artefato = get_artefato()
    except Exception:  # noqa: BLE001 - artefato pode não existir
        st.error("Modelo não encontrado. Gere o artefato com `make train`.")
        return

    linhas = appdata.listar_linhas(con)
    col1, col2, col3 = st.columns(3)
    nome_linha = col1.selectbox("Linha", linhas["route_short_name"].to_list())
    dia = col2.selectbox("Dia da semana", list(DIAS_SEMANA))
    mes = col3.selectbox("Mês", list(range(1, 13)), index=5)
    precip = col1.slider("Precipitação no dia (mm)", 0.0, 60.0, 0.0, step=1.0)
    temp = col2.slider("Temperatura média (°C)", 5.0, 40.0, 20.0, step=0.5)

    route_id = linhas.filter(linhas["route_short_name"] == nome_linha)["route_id"][0]
    n_viagens = appdata.oferta_tipica_linha(con, route_id)
    features = montar_features(
        n_viagens=n_viagens,
        iso_dia_semana=DIAS_SEMANA[dia],
        mes=mes,
        precipitacao=precip,
        temperatura=temp,
        choveu=precip > 0,
    )
    demanda = prever_demanda(artefato, features)

    st.metric(
        f"Demanda estimada (simulada) — linha {nome_linha}, {dia.lower()}",
        f"{demanda:,.0f} viagens/dia",
    )
    meta = artefato["metadata"]
    st.caption(
        f"Oferta típica da linha: {n_viagens:,.0f}/dia · modelo {meta['model_type']} "
        f"v{meta['version']} (treinado em {meta['trained_at']}; "
        f"MAE {meta['metrics']['mae']:.1f})."
    )


if __name__ == "__main__":
    render()
