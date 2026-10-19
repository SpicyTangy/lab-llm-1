"""Client minimo per il server locale di LM Studio.

Scheletro da completare con Claude Code (slide 19-22):
configurazione, messaggi, payload e chiamata HTTP.
Import e gestione degli errori sono gia' presenti: conservarli.
"""

import json
import os

import requests
from dotenv import load_dotenv

# --- Configurazione -------------------------------------------------------
load_dotenv(".env", override=False)
base_url = os.environ["LM_BASE_URL"].rstrip("/")
model = os.environ["LM_MODEL"]

# --- Messaggi -------------------------------------------------------------
SYSTEM = "Rispondi in italiano."

# --- Ciclo di input -------------------------------------------------------
while True:
    try:
        domanda = input("Tu> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break
    if domanda.lower() == "esci":
        break
    if not domanda:
        continue

    # --- Payload ----------------------------------------------------------
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": domanda},
        ],
        "temperature": 0.2,
        "max_tokens": 180,
        "reasoning_effort": "none",
        "stream": True,
    }

    # --- Chiamata ---------------------------------------------------------
    try:
        testo = ""
        response = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            stream=True,
            timeout=(5, 120),
        )
        response.raise_for_status()
        for riga in response.iter_lines():
            riga = riga.decode("utf-8")
            if not riga.startswith("data: "):
                continue
            dati = riga[len("data: "):]
            if dati == "[DONE]":
                break
            delta = json.loads(dati)["choices"][0]["delta"]
            frammento = delta.get("content") or ""
            print(frammento, end="", flush=True)
            testo += frammento
        response.close()
        print()
    except requests.exceptions.Timeout:
        print("Attesa scaduta: controllare server, carico e tempi.")
    except requests.exceptions.ConnectionError:
        print("Connessione fallita: controllare server, URL e porta.")
    except requests.exceptions.HTTPError:
        print("Errore HTTP:", response.status_code, response.text)
