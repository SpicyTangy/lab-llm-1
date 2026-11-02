# Assistente del laboratorio

Chat da terminale in Python che conversa con un modello servito da **LM Studio** sul computer
host. Il flusso è un grafo **LangGraph** esplicito; l'assistente sa dire l'ora (quella locale,
Europe/Rome, e quella di altri paesi) chiedendo lo strumento `orologio`, che il programma esegue
davvero. La cronologia resta in memoria per la sola durata della sessione.

Specifica: `docs/superpowers/specs/2026-10-26-assistente-orologio-design.md`.

## Requisiti

- Python 3.14
- LM Studio con il server avviato (porta 1234) e un modello che supporta il tool calling
  (provato con `google/gemma-4-e2b`)
- Per l'avvio in container: Docker con Docker Compose v2 o successivo (provato con Docker 29.2.0, Compose v5)

## Installazione (PowerShell)

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

`requirements.txt` contiene le dipendenze di esecuzione (`langgraph`, `langchain-openai`, `tzdata`);
`requirements-dev.txt` aggiunge `pytest`.

## Configurazione

Tutto arriva da variabili d'ambiente. Si parte dal file di esempio (il `.env` reale è escluso da Git):

```powershell
Copy-Item .env.example .env
```

| Variabile | Obbligatoria | Predefinito | Note |
|---|---|---|---|
| `LMSTUDIO_BASE_URL` | sì | — | `http://localhost:1234/v1` (in Docker viene sostituita da compose) |
| `LMSTUDIO_MODEL` | sì | — | id esatto restituito da LM Studio, vedi sotto |
| `FUSO_ORARIO_LOCALE` | no | `Europe/Rome` | fuso usato quando non si indica un luogo |
| `MAX_PASSI` | no | `5` | chiamate massime al modello per una domanda |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

L'id del modello si legge dal server, non si inventa:

```powershell
(Invoke-RestMethod http://localhost:1234/v1/models).data.id
```

Python non legge `.env` da solo. Per caricarlo nella sessione PowerShell corrente:

```powershell
Get-Content .env | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
    $n, $v = $_ -split '=', 2; Set-Item "env:$($n.Trim())" $v.Trim() }
```

## Avvio in locale

Con LM Studio acceso e `.env` caricato:

```powershell
.\.venv\Scripts\python -m assistente
```

Si scrive dopo `tu>`; si esce con `esci` (o `exit`, `quit`), Ctrl+C o Ctrl+Z seguito da Invio.
Le risposte vanno su stdout; i log, con prefisso `[log]`, vanno su stderr e mostrano ogni
chiamata allo strumento:

```
tu> che ore sono?
[log] INFO assistente.grafo: passo 1: strumento orologio({"fuso_orario": "Europe/Rome"}) -> {"fuso_orario": "Europe/Rome", "data_ora": "2026-11-02T09:51:28+01:00", "giorno": "lunedì", "abbreviazione": "CET"}
assistente> Ora sono le 09:51 del lunedì.
tu> e a Tokyo?
[log] INFO assistente.grafo: passo 1: strumento orologio({"fuso_orario": "Asia/Tokyo"}) -> {"fuso_orario": "Asia/Tokyo", "data_ora": "2026-11-02T17:51:50+09:00", "giorno": "lunedì", "abbreviazione": "JST"}
assistente> A Tokyo sono le 17:51 del lunedì.
```

## Avvio con Docker Compose

LM Studio resta sull'host; il container lo raggiunge su `host.docker.internal`, e `compose.yaml`
imposta già `LMSTUDIO_BASE_URL` di conseguenza. Serve il file `.env` (vedi Configurazione).

```powershell
docker compose build
docker compose run --rm assistente
```

La sessione in container è stata provata con le domande passate da pipe
(`docker compose run --rm -T assistente`); l'uso interattivo con TTY va ancora confermato.

Per controllare che il container veda LM Studio:

```powershell
docker compose run --rm assistente python -c "from assistente.modello import modelli_serviti; print(modelli_serviti('http://host.docker.internal:1234/v1'))"
```

Con Docker Desktop su Windows ha funzionato senza attivare "Serve on Local Network" in LM Studio.

## Test

Test automatici, che **non** richiedono LM Studio (strumento con istante fisso, configurazione,
collegamento con server finto, grafo e cronologia con un modello finto, terminale):

```powershell
.\.venv\Scripts\python -m pytest
```

Prove reali con il modello vero, escluse di default. Servono LM Studio acceso e `.env` caricato:

```powershell
.\.venv\Scripts\python -m pytest -m lmstudio -v
```

Verificano che il modello chieda davvero `orologio` con `Asia/Tokyo` / `Europe/Rome` e che la
risposta riporti l'ora restituita dallo strumento. I test con il modello finto non dimostrano che
il modello locale sappia usare lo strumento: lo dimostrano solo queste prove.

## Com'è fatto

```
assistente/
  config.py      lettura e validazione delle variabili d'ambiente
  strumenti.py   strumento orologio (istante iniettabile per i test)
  modello.py     ChatOpenAI verso LM Studio, controllo dei modelli serviti
  grafo.py       stato, nodi, instradamento del grafo LangGraph
  terminale.py   ciclo di chat, cronologia di sessione, log
  __main__.py    avvio (python -m assistente)
tests/           test automatici e prove reali (marcatore lmstudio)
```

Il grafo (`assistente/grafo.py`):

- **Stato:** `messages` (accodati con `add_messages`) e `passi` (chiamate al modello nella domanda corrente).
- **Nodi:** `modello` (antepone il prompt di sistema, chiama il modello con lo strumento collegato),
  `strumenti` (esegue ogni `tool_call` e registra nome, argomenti e risultato), `limite` (risponde
  "non eseguito" alle chiamate pendenti e avvisa l'utente).
- **Instradamento dopo `modello`:** nessuna `tool_call` → fine; `tool_call` e `passi < MAX_PASSI`
  → `strumenti` → `modello`; `tool_call` e `passi >= MAX_PASSI` → `limite` → fine.

## Diagnosi

| Sintomo | Causa e rimedio |
|---|---|
| `Configurazione non valida: ...` (uscita 2) | variabili mancanti o errate: caricare `.env` come sopra |
| `Impossibile ottenere i modelli da http://.../models ... Avvia il server di LM Studio` (uscita 1) | server di LM Studio spento o indirizzo sbagliato |
| `LMSTUDIO_MODEL: il modello '...' non è servito da LM Studio. Modelli disponibili: ...` (uscita 1) | id errato o modello non caricato: usare uno degli id elencati |
| `assistente> Non riesco a comunicare con LM Studio (...)` durante la chat | LM Studio fermato a sessione aperta: riavviarlo; la cronologia resta valida |
| `assistente> Errore inatteso durante la risposta (...)` | risposta del modello non interpretabile: riprovare; con `LOG_LEVEL=DEBUG` il log mostra il dettaglio |
| `assistente> Mi fermo qui: ho raggiunto il limite di passaggi...` | il modello ha chiesto lo strumento più di `MAX_PASSI` volte: riformulare o alzare `MAX_PASSI` |
| `env file ...\.env not found` da `docker compose` | creare `.env` da `.env.example` |
