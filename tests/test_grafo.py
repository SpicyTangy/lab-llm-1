import logging

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END

from aiuti import chiamata, conta_coerenza, grafo_con
from assistente.grafo import (
    MESSAGGIO_LIMITE,
    RISULTATO_NON_ESEGUITO,
    esegui_turno,
    instrada,
    prompt_sistema,
)


def test_instrada_senza_tool_call_termina():
    assert instrada({"messages": [AIMessage("ok")], "passi": 1}, 5) == END


def test_instrada_con_tool_call_va_a_strumenti():
    assert instrada({"messages": [chiamata()], "passi": 1}, 5) == "strumenti"


def test_instrada_al_limite_va_a_limite():
    assert instrada({"messages": [chiamata()], "passi": 5}, 5) == "limite"


def test_risposta_diretta(orologio_fisso):
    g, finto = grafo_con([AIMessage("Ciao!")], orologio_fisso)
    r = g.invoke({"messages": [HumanMessage("ciao")], "passi": 0})
    assert r["passi"] == 1 and r["messages"][-1].content == "Ciao!"
    assert isinstance(finto.chiamate[0][0], SystemMessage)
    assert not any(isinstance(m, SystemMessage) for m in r["messages"])


def test_strumento_eseguito_e_risposta_finale(orologio_fisso):
    g, finto = grafo_con([chiamata(), AIMessage("A Tokyo sono le 21:00.")], orologio_fisso)
    msgs = esegui_turno(g, [], "Che ore sono a Tokyo?", 5)
    assert [type(m) for m in msgs] == [HumanMessage, AIMessage, ToolMessage, AIMessage]
    assert msgs[2].tool_call_id == "c1"
    assert "2026-10-26T21:00:00+09:00" in msgs[2].content
    assert msgs[2] in finto.chiamate[1]


def test_log_della_chiamata(orologio_fisso, caplog):
    caplog.set_level(logging.INFO, logger="assistente.grafo")
    g, _ = grafo_con([chiamata(), AIMessage("ok")], orologio_fisso)
    esegui_turno(g, [], "ora a Tokyo?", 5)
    testo = caplog.text
    assert "orologio" in testo and "Asia/Tokyo" in testo and "21:00:00+09:00" in testo


def test_limite_di_passaggi(orologio_fisso):
    g, finto = grafo_con([chiamata()], orologio_fisso, max_passi=3)
    msgs = esegui_turno(g, [], "ora?", 3)
    assert len(finto.chiamate) == 3
    tool = [m for m in msgs if isinstance(m, ToolMessage)]
    assert [m.content == RISULTATO_NON_ESEGUITO for m in tool] == [False, False, True]
    assert msgs[-1].content == MESSAGGIO_LIMITE
    assert conta_coerenza(msgs)[0] == conta_coerenza(msgs)[1]


def test_domanda_dopo_il_limite(orologio_fisso):
    g, finto = grafo_con(
        [chiamata(), chiamata(), AIMessage("ripreso")], orologio_fisso, max_passi=2
    )
    prima = esegui_turno(g, [], "ora?", 2)
    dopo = esegui_turno(g, prima, "e adesso?", 2)
    assert dopo[-1].content == "ripreso"
    assert conta_coerenza(dopo)[0] == conta_coerenza(dopo)[1]


def test_strumento_sconosciuto(orologio_fisso):
    g, _ = grafo_con([chiamata(nome="meteo", args={}), AIMessage("ok")], orologio_fisso)
    msgs = esegui_turno(g, [], "meteo?", 5)
    assert msgs[2].content == "Errore: strumento sconosciuto 'meteo'."


def test_argomenti_mancanti(orologio_fisso):
    g, _ = grafo_con([chiamata(args={}), AIMessage("ok")], orologio_fisso)
    msgs = esegui_turno(g, [], "ora?", 5)
    assert msgs[2].content.startswith("Errore: argomenti non validi per 'orologio'")


def test_cronologia_tra_due_domande(orologio_fisso):
    g, finto = grafo_con([AIMessage("Prima"), AIMessage("Seconda")], orologio_fisso)
    c1 = esegui_turno(g, [], "domanda 1", 5)
    c2 = esegui_turno(g, c1, "domanda 2", 5)
    assert [m.content for m in c2] == ["domanda 1", "Prima", "domanda 2", "Seconda"]
    assert [m.content for m in finto.chiamate[1][1:]] == ["domanda 1", "Prima", "domanda 2"]


def test_errore_del_modello_non_tocca_la_cronologia(orologio_fisso):
    g, _ = grafo_con([AIMessage("x")], orologio_fisso, errore=RuntimeError("giù"))
    cronologia = [HumanMessage("vecchia"), AIMessage("risposta")]
    with pytest.raises(RuntimeError):
        esegui_turno(g, cronologia, "nuova", 5)
    assert [m.content for m in cronologia] == ["vecchia", "risposta"]


def test_prompt_sistema_cita_fuso_e_strumento():
    p = prompt_sistema("Europe/Rome")
    assert "Europe/Rome" in p and "orologio" in p
