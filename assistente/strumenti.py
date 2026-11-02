"""Strumento `orologio`: data e ora correnti in un fuso orario IANA esplicito."""

import json
from collections.abc import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.tools import BaseTool, StructuredTool

GIORNI = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")


def ora_utc() -> datetime:
    return datetime.now(timezone.utc)


def ora_in_fuso(fuso_orario: str, adesso: Callable[[], datetime] = ora_utc) -> str:
    """Restituisce un JSON con data e ora nel fuso indicato, o con la chiave `errore`.

    Non solleva mai eccezioni: l'errore torna al modello come testo leggibile.
    """
    try:
        fuso = ZoneInfo(fuso_orario)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        errore = (
            f"Fuso orario sconosciuto: '{fuso_orario}'. "
            "Usa un identificativo IANA, ad esempio Europe/Rome."
        )
        return json.dumps({"errore": errore}, ensure_ascii=False)

    locale = adesso().astimezone(fuso)
    return json.dumps(
        {
            "fuso_orario": fuso_orario,
            "data_ora": locale.isoformat(timespec="seconds"),
            "giorno": GIORNI[locale.weekday()],
            "abbreviazione": locale.tzname(),
        },
        ensure_ascii=False,
    )


def crea_orologio(adesso: Callable[[], datetime] = ora_utc) -> BaseTool:
    """Crea lo strumento LangChain `orologio` con l'istante corrente iniettabile."""

    def orologio(fuso_orario: str) -> str:
        return ora_in_fuso(fuso_orario, adesso=adesso)

    return StructuredTool.from_function(
        func=orologio,
        name="orologio",
        description=(
            "Restituisce data e ora correnti nel fuso orario IANA indicato, "
            "es. Europe/Rome, Asia/Tokyo."
        ),
    )
