"""Grafo LangGraph dell'assistente: stato, nodi e instradamento scritti in chiaro.

    START → modello ─┬─ nessuna tool_call ──────────────→ END
                     ├─ tool_call, passi < max_passi ──→ strumenti → modello
                     └─ tool_call, passi >= max_passi ─→ limite → END
"""

import json
import logging
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

log = logging.getLogger(__name__)

MESSAGGIO_LIMITE = (
    "Mi fermo qui: ho raggiunto il limite di passaggi per questa domanda. Prova a riformularla."
)
RISULTATO_NON_ESEGUITO = "Non eseguito: limite di passaggi raggiunto."


class Stato(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    passi: int  # chiamate al modello eseguite per la domanda corrente


def prompt_sistema(fuso_locale: str) -> str:
    return (
        "Sei un assistente cordiale e rispondi sempre in italiano.\n"
        "Per qualsiasi domanda su data od ora usa sempre lo strumento `orologio`: "
        "non indovinare e non usare ore scritte in precedenza nella conversazione.\n"
        f"Se l'utente non indica un luogo, usa il fuso orario {fuso_locale}.\n"
        "Per città o paesi scegli l'identificativo IANA corrispondente "
        "(per esempio Asia/Tokyo, America/New_York)."
    )


def instrada(stato: Stato, max_passi: int) -> str:
    """Decide dove andare dopo il nodo `modello`."""
    ultimo = stato["messages"][-1]
    if not getattr(ultimo, "tool_calls", None):
        return END
    if stato["passi"] < max_passi:
        return "strumenti"
    return "limite"


def crea_grafo(
    modello: BaseChatModel, strumenti: list[BaseTool], max_passi: int, prompt: str
) -> CompiledStateGraph:
    modello_con_strumenti = modello.bind_tools(strumenti)
    per_nome = {s.name: s for s in strumenti}

    def nodo_modello(stato: Stato) -> dict:
        # Il prompt di sistema viene anteposto a ogni chiamata ma non entra nella cronologia.
        risposta = modello_con_strumenti.invoke([SystemMessage(prompt), *stato["messages"]])
        return {"messages": [risposta], "passi": stato["passi"] + 1}

    def nodo_strumenti(stato: Stato) -> dict:
        risultati = []
        for tc in stato["messages"][-1].tool_calls:
            nome, args = tc["name"], tc["args"]
            strumento = per_nome.get(nome)
            if strumento is None:
                risultato = f"Errore: strumento sconosciuto '{nome}'."
            else:
                try:
                    risultato = str(strumento.invoke(args))
                except Exception as e:
                    risultato = f"Errore: argomenti non validi per '{nome}': {e}"
            log.info(
                "passo %d: strumento %s(%s) -> %s",
                stato["passi"],
                nome,
                json.dumps(args, ensure_ascii=False),
                risultato,
            )
            risultati.append(ToolMessage(content=risultato, tool_call_id=tc["id"], name=nome))
        return {"messages": risultati}

    def nodo_limite(stato: Stato) -> dict:
        log.warning("limite di %d passaggi raggiunto", max_passi)
        # Ogni tool_call pendente riceve una risposta, così la cronologia resta valida.
        non_eseguiti = [
            ToolMessage(content=RISULTATO_NON_ESEGUITO, tool_call_id=tc["id"], name=tc["name"])
            for tc in stato["messages"][-1].tool_calls
        ]
        return {"messages": [*non_eseguiti, AIMessage(MESSAGGIO_LIMITE)]}

    grafo = StateGraph(Stato)
    grafo.add_node("modello", nodo_modello)
    grafo.add_node("strumenti", nodo_strumenti)
    grafo.add_node("limite", nodo_limite)
    grafo.add_edge(START, "modello")
    grafo.add_conditional_edges(
        "modello", lambda stato: instrada(stato, max_passi), ["strumenti", "limite", END]
    )
    grafo.add_edge("strumenti", "modello")
    grafo.add_edge("limite", END)
    return grafo.compile()


def esegui_turno(
    grafo: CompiledStateGraph, cronologia: list[AnyMessage], domanda: str, max_passi: int
) -> list[AnyMessage]:
    """Esegue una domanda e restituisce la nuova cronologia; `cronologia` non viene modificata."""
    risultato = grafo.invoke(
        {"messages": [*cronologia, HumanMessage(domanda)], "passi": 0},
        config={"recursion_limit": 2 * max_passi + 4},
    )
    return risultato["messages"]
