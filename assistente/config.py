"""Lettura e validazione della configurazione dalle variabili d'ambiente."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LIVELLI_LOG = ("DEBUG", "INFO", "WARNING", "ERROR")


class ErroreConfigurazione(Exception):
    """Configurazione mancante o non valida; il messaggio è pensato per l'utente."""


@dataclass(frozen=True)
class Config:
    base_url: str
    modello: str
    fuso_locale: str
    max_passi: int
    log_level: str


def carica_config(env: Mapping[str, str] | None = None) -> Config:
    """Legge le variabili d'ambiente e riporta tutti i problemi in un'unica eccezione."""
    env = os.environ if env is None else env
    problemi: list[str] = []

    def leggi(nome: str, predefinito: str = "") -> str:
        return (env.get(nome) or "").strip() or predefinito

    base_url = leggi("LMSTUDIO_BASE_URL").rstrip("/")
    if not base_url:
        problemi.append("LMSTUDIO_BASE_URL: obbligatoria (es. http://localhost:1234/v1).")

    modello = leggi("LMSTUDIO_MODEL")
    if not modello:
        problemi.append("LMSTUDIO_MODEL: obbligatoria (id restituito da GET /v1/models).")

    fuso_locale = leggi("FUSO_ORARIO_LOCALE", "Europe/Rome")
    try:
        ZoneInfo(fuso_locale)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        problemi.append(f"FUSO_ORARIO_LOCALE: fuso IANA sconosciuto '{fuso_locale}'.")

    testo_passi = leggi("MAX_PASSI", "5")
    try:
        max_passi = int(testo_passi)
    except ValueError:
        max_passi = 0
    if max_passi < 1:
        problemi.append(f"MAX_PASSI: deve essere un intero positivo, non '{testo_passi}'.")

    log_level = leggi("LOG_LEVEL", "INFO").upper()
    if log_level not in LIVELLI_LOG:
        problemi.append(f"LOG_LEVEL: valori ammessi {', '.join(LIVELLI_LOG)}, non '{log_level}'.")

    if problemi:
        raise ErroreConfigurazione("Configurazione non valida:\n- " + "\n- ".join(problemi))
    return Config(base_url, modello, fuso_locale, max_passi, log_level)
