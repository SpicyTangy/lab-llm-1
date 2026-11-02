import socket

import pytest

from aiuti import ISTANTE
from assistente.strumenti import crea_orologio


@pytest.fixture
def orologio_fisso():
    """Strumento orologio fermo su ISTANTE (2026-10-26T12:00Z)."""
    return crea_orologio(adesso=lambda: ISTANTE)


@pytest.fixture
def porta_chiusa():
    """URL di un server che non risponde: una porta appena liberata."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    return f"http://127.0.0.1:{porta}/v1"
