"""Helper HTTP compartilhado para downloads das ingestões.

Faz streaming para disco (seguro para arquivos grandes) e envia um ``User-Agent`` de
browser, pois alguns portais públicos (ex.: INMET) recusam clientes sem UA conhecido.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#: User-Agent usado nas requisições (alguns servidores bloqueiam UAs não-browser).
USER_AGENT = (
    "Mozilla/5.0 (compatible; observatorio-mobilidade/0.1; "
    "+https://github.com/TatianaCalixto/observatorio-mobilidade)"
)


def download_file(
    url: str,
    dest: str | Path,
    *,
    timeout: float = 120.0,
    chunk_size: int = 1 << 16,
) -> Path:
    """Baixa ``url`` para ``dest`` em streaming. Retorna o caminho do arquivo gravado."""
    import httpx

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in resp.iter_bytes(chunk_size):
                    fh.write(chunk)
    logger.info("Baixado %s (%d bytes) <- %s", dest, dest.stat().st_size, url)
    return dest
