"""Smoke consolidado do app (S06-T05): cada página renderiza sem exceção."""

import subprocess
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.main import PAGINAS


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cada_pagina_renderiza_sem_excecao(pagina):
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value(pagina).run()
    assert at.exception == [], f"a página {pagina!r} lançou exceção"


def test_app_roda_como_streamlit_run():
    """Reproduz `streamlit run app/main.py`: executar o script (com a pasta app/ no
    sys.path, não a raiz) deve importar os pacotes do projeto sem ModuleNotFoundError."""
    raiz = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(raiz / "app" / "main.py")],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert "ModuleNotFoundError" not in proc.stderr
    assert proc.returncode == 0, proc.stderr[-1500:]
