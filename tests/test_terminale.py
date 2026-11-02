import logging

import httpx
import openai
import pytest
from langchain_core.messages import AIMessage

from aiuti import grafo_con
from assistente.terminale import RISPOSTA_VUOTA, chat, configura_log

LOGGER_HTTP = ("httpx", "httpx2", "openai")


@pytest.fixture
def logging_ripristinato():
    """configura_log tocca la configurazione globale: la rimette com'era a fine test."""
    radice = logging.getLogger()
    prima = (radice.handlers[:], radice.level, {n: logging.getLogger(n).level for n in LOGGER_HTTP})
    yield
    radice.handlers[:], radice.level = prima[0], prima[1]
    for nome, livello in prima[2].items():
        logging.getLogger(nome).setLevel(livello)


def test_configura_log_zittisce_le_librerie_http(logging_ripristinato):
    configura_log("INFO")
    assert all(logging.getLogger(n).level == logging.WARNING for n in LOGGER_HTTP)


def ingressi(*righe):
    """`leggi` finta: emette le righe in ordine (solleva quelle che sono eccezioni), poi EOF."""
    coda = list(righe)

    def leggi(_prompt):
        if not coda:
            raise EOFError
        riga = coda.pop(0)
        if isinstance(riga, BaseException):
            raise riga
        return riga

    return leggi


def test_esci_termina_senza_chiamare_il_modello(orologio_fisso):
    g, finto = grafo_con([AIMessage("x")], orologio_fisso)
    uscita = []
    chat(g, 5, ingressi("ESCI"), uscita.append)
    assert finto.chiamate == [] and uscita[-1] == "Alla prossima!"


@pytest.mark.parametrize("eccezione", [EOFError(), KeyboardInterrupt()])
def test_eof_e_ctrl_c_terminano(orologio_fisso, eccezione):
    g, _ = grafo_con([AIMessage("x")], orologio_fisso)
    uscita = []
    chat(g, 5, ingressi(eccezione), uscita.append)
    assert uscita[-1] == "Alla prossima!"


def test_riga_vuota_ignorata_e_risposta_stampata(orologio_fisso):
    g, finto = grafo_con([AIMessage("Ciao!")], orologio_fisso)
    uscita = []
    chat(g, 5, ingressi("   ", "ciao", "esci"), uscita.append)
    assert len(finto.chiamate) == 1 and "assistente> Ciao!" in uscita


def test_risposta_vuota_mostra_segnaposto(orologio_fisso):
    g, _ = grafo_con([AIMessage("")], orologio_fisso)
    uscita = []
    chat(g, 5, ingressi("ciao", "esci"), uscita.append)
    assert f"assistente> {RISPOSTA_VUOTA}" in uscita


def test_errore_di_rete_non_chiude_la_sessione(orologio_fisso):
    errore = openai.APIConnectionError(request=httpx.Request("POST", "http://x"))
    g, finto = grafo_con([AIMessage("ok")], orologio_fisso, errore=errore)
    uscita = []
    chat(g, 5, ingressi("prima", "seconda", "esci"), uscita.append)
    assert len(finto.chiamate) == 2
    assert [m.content for m in finto.chiamate[1][1:]] == ["seconda"]  # "prima" non è in cronologia
    assert any("LM Studio" in r for r in uscita)


def test_ctrl_c_durante_il_turno(orologio_fisso):
    g, _ = grafo_con([AIMessage("x")], orologio_fisso, errore=KeyboardInterrupt())
    uscita = []
    chat(g, 5, ingressi("ciao"), uscita.append)
    assert uscita[-1] == "Alla prossima!"


def test_errore_inatteso_non_chiude_la_sessione(orologio_fisso):
    g, finto = grafo_con([AIMessage("ok")], orologio_fisso, errore=ValueError("risposta strana"))
    uscita = []
    chat(g, 5, ingressi("prima", "seconda", "esci"), uscita.append)
    assert len(finto.chiamate) == 2
    assert [m.content for m in finto.chiamate[1][1:]] == ["seconda"]
    assert any("risposta strana" in r for r in uscita)
    assert uscita[-1] == "Alla prossima!"
