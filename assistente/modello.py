"""Collegamento al modello servito da LM Studio tramite l'API compatibile con OpenAI."""

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from langchain_openai import ChatOpenAI

from assistente.config import Config, ErroreConfigurazione

# LM Studio non richiede una chiave: il client OpenAI ne vuole comunque una, questa è un segnaposto.
CHIAVE_SEGNAPOSTO = "lm-studio"

# LM Studio gira sull'host: niente proxy di sistema tra il programma e il server.
_apri = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


class ErroreServer(Exception):
    """LM Studio non raggiungibile o risposta non valida."""


def modelli_serviti(base_url: str, timeout: float = 5.0) -> list[str]:
    """Restituisce gli id dei modelli serviti da `GET {base_url}/models`."""
    url = f"{base_url}/models"
    try:
        with _apri(url, timeout=timeout) as risposta:
            dati = json.load(risposta)
        return [m["id"] for m in dati["data"]]
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as e:
        raise ErroreServer(
            f"Impossibile ottenere i modelli da {url} ({e}). "
            "Avvia il server di LM Studio e controlla LMSTUDIO_BASE_URL."
        ) from e


def verifica_modello(
    config: Config, elenca: Callable[[str], list[str]] = modelli_serviti
) -> None:
    """Controlla che `LMSTUDIO_MODEL` sia tra i modelli serviti da LM Studio."""
    disponibili = elenca(config.base_url)
    if config.modello not in disponibili:
        elenco = ", ".join(disponibili) or "(nessuno)"
        raise ErroreConfigurazione(
            f"LMSTUDIO_MODEL: il modello '{config.modello}' non è servito da LM Studio. "
            f"Modelli disponibili: {elenco}."
        )


def crea_modello(config: Config) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.modello,
        base_url=config.base_url,
        api_key=CHIAVE_SEGNAPOSTO,
        temperature=0,
        timeout=120,
        max_retries=1,
    )
