"""Avvio con `python -m assistente`."""

import sys
from collections.abc import Mapping

from assistente.config import ErroreConfigurazione, carica_config
from assistente.grafo import crea_grafo, prompt_sistema
from assistente.modello import ErroreServer, crea_modello, verifica_modello
from assistente.strumenti import crea_orologio
from assistente.terminale import chat, configura_log


def main(env: Mapping[str, str] | None = None) -> int:
    try:
        config = carica_config(env)
    except ErroreConfigurazione as e:
        print(e, file=sys.stderr)
        return 2

    try:
        verifica_modello(config)
    except (ErroreServer, ErroreConfigurazione) as e:
        print(e, file=sys.stderr)
        return 1

    configura_log(config.log_level)
    grafo = crea_grafo(
        crea_modello(config),
        [crea_orologio()],
        config.max_passi,
        prompt_sistema(config.fuso_locale),
    )
    chat(grafo, config.max_passi)
    return 0


if __name__ == "__main__":
    sys.exit(main())
