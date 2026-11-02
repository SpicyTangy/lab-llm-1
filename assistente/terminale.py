"""Interfaccia da terminale: ciclo di chat con la cronologia della sessione in memoria."""

import logging
import sys
from collections.abc import Callable

import openai
from langchain_core.messages import AnyMessage
from langgraph.graph.state import CompiledStateGraph

from assistente.grafo import esegui_turno

log = logging.getLogger(__name__)

COMANDI_USCITA = {"esci", "exit", "quit"}
RISPOSTA_VUOTA = "(il modello non ha dato una risposta)"
SALUTO = "Assistente del laboratorio. Scrivi una domanda; 'esci' (o Ctrl+C) per terminare."
CONGEDO = "Alla prossima!"


def configura_log(livello: str) -> None:
    """Log su stderr con prefisso `[log]`, separati dalle risposte su stdout."""
    logging.basicConfig(
        level=livello,
        stream=sys.stderr,
        format="[log] %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    if livello != "DEBUG":
        # openai 3.x usa httpx2; httpx resta per le librerie che lo usano ancora.
        for rumoroso in ("httpx", "httpx2", "openai"):
            logging.getLogger(rumoroso).setLevel(logging.WARNING)


def chat(
    grafo: CompiledStateGraph,
    max_passi: int,
    leggi: Callable[[str], str] = input,
    scrivi: Callable[[str], None] = print,
) -> None:
    cronologia: list[AnyMessage] = []  # solo in memoria: si perde alla chiusura
    scrivi(SALUTO)
    try:
        while True:
            domanda = leggi("tu> ").strip()
            if not domanda:
                continue
            if domanda.lower() in COMANDI_USCITA:
                break
            try:
                cronologia = esegui_turno(grafo, cronologia, domanda, max_passi)
            except openai.APIError as e:
                # La domanda fallita non entra nella cronologia; la sessione continua.
                log.debug("errore durante il turno", exc_info=True)
                scrivi(f"assistente> Non riesco a comunicare con LM Studio ({e}). Riprova.")
                continue
            scrivi(f"assistente> {cronologia[-1].content or RISPOSTA_VUOTA}")
    except (EOFError, KeyboardInterrupt):
        pass
    scrivi(CONGEDO)
