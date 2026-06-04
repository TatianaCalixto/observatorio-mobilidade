"""Smoke consolidado do app (S06-T05): cada página renderiza sem exceção."""

import pytest
from streamlit.testing.v1 import AppTest

from app.main import PAGINAS


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cada_pagina_renderiza_sem_excecao(pagina):
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value(pagina).run()
    assert at.exception == [], f"a página {pagina!r} lançou exceção"
