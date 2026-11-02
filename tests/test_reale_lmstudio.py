"""Prove reali con LM Studio acceso: escluse di default, si lanciano con `pytest -m lmstudio`.

L'orologio è fermo su ISTANTE (2026-10-26T12:00Z): Tokyo 21:00, Roma 13:00.
"""

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from aiuti import ISTANTE
from assistente.config import ErroreConfigurazione, carica_config
from assistente.grafo import crea_grafo, esegui_turno, prompt_sistema
from assistente.modello import crea_modello
from assistente.strumenti import crea_orologio

pytestmark = pytest.mark.lmstudio


@pytest.fixture
def grafo_reale():
    try:
        cfg = carica_config()
    except ErroreConfigurazione as e:
        pytest.fail(str(e))
    return crea_grafo(
        crea_modello(cfg),
        [crea_orologio(adesso=lambda: ISTANTE)],
        cfg.max_passi,
        prompt_sistema(cfg.fuso_locale),
    )


def chiamate_orologio(msgs):
    return [
        tc["args"]
        for m in msgs
        if isinstance(m, AIMessage)
        for tc in m.tool_calls
        if tc["name"] == "orologio"
    ]


def test_reale_ora_a_tokyo(grafo_reale):
    msgs = esegui_turno(grafo_reale, [], "Che ore sono a Tokyo adesso?", 5)
    assert {"fuso_orario": "Asia/Tokyo"} in chiamate_orologio(msgs)
    assert any(isinstance(m, ToolMessage) for m in msgs)
    assert "21" in msgs[-1].content


def test_reale_ora_locale(grafo_reale):
    msgs = esegui_turno(grafo_reale, [], "Che ore sono?", 5)
    assert {"fuso_orario": "Europe/Rome"} in chiamate_orologio(msgs)
    assert "13" in msgs[-1].content
