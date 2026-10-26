# Assistente del laboratorio — chat da terminale con strumento orologio

Data: 2026-10-26 · Stato: approvata dall'utente il 2026-10-26

## 1. Intento

Un assistente da terminale, in Python, con cui si chiacchiera come con un normale agente AI.
Gira contro il modello servito da LM Studio sul computer host e sa rispondere a domande
sull'ora — quella locale (Roma) e quella di altri paesi — chiedendo uno strumento orologio
che il programma esegue davvero.

È la base del progetto del corso: le lezioni successive aggiungeranno altri strumenti, MCP,
workflow e RAG. Per questo il flusso deve stare in un grafo LangGraph **esplicito e leggibile**
(stato, nodi, instradamento riconoscibili), facile da estendere più avanti, e il progetto deve
essere verificabile sia con test automatici senza modello sia con prove reali.

## 2. Obiettivi

1. Chat a turni nel terminale: l'utente scrive, l'assistente risponde in italiano.
2. Cronologia conservata in memoria per tutta la sessione; persa alla chiusura.
3. Strumento `orologio` con fuso orario IANA esplicito, richiesto dal modello via tool calling,
   eseguito dal programma, con il risultato restituito al modello per la risposta finale.
4. Ogni chiamata allo strumento è visibile nei log (nome, argomenti, risultato).
5. Limite al numero di passaggi del ciclo modello ↔ strumento per ogni domanda.
6. Avvio sia in locale (venv) sia con Docker Compose; LM Studio resta sull'host.
7. Test automatici che non richiedono un modello attivo, più prove reali (LM Studio, Docker)
   separate e attivate esplicitamente, documentate nel README.

## 3. Non-obiettivi (per ora)

- Altri strumenti oltre all'orologio, MCP, RAG, workflow.
- Interfacce web o grafiche, servizi cloud.
- Persistenza della cronologia tra sessioni.
- Streaming token per token della risposta.
- Containerizzare LM Studio.

## 4. Anti-obiettivi (sarebbe un fallimento anche se "funziona")

- Grafo nascosto dentro un agente preconfezionato (es. `create_react_agent`): stato, nodi e
  instradamento devono essere scritti e leggibili nel codice del progetto.
- Chiamate allo strumento invisibili: chi guarda il terminale/log deve poter vedere che lo
  strumento è stato davvero eseguito, con quali argomenti e con quale risultato.
- Crash o traceback davanti a errori prevedibili (fuso inesistente, LM Studio spento, modello
  sbagliato, Ctrl+C).
- Dichiarare "funziona con il modello" sulla base di test con modello simulato.
- Identificativo del modello inventato o scritto nel codice; credenziali o `.env` in Git.
- Anticipare funzionalità delle lezioni successive.

## 5. Vincoli

- **Repository:** `LLM/` è la radice della repository `SpicyTangy/lab-llm-1`, branch `main`
  (già inizializzata e allineata a `origin/main`). `lezione3/` contiene la lezione precedente:
  non va letta per copiarne codice né modificata. Il progetto vive nella radice, accanto a
  `lezione3/`. Push solo su richiesta.
- **Python 3.14** (installata sull'host: 3.14.7). Codice sincrono, moduli piccoli.
- **LM Studio** sull'host, API compatibile OpenAI su `http://localhost:1234/v1`.
  Modello di chat disponibile oggi: `google/gemma-4-e2b` (verificato con `GET /v1/models`).
  Prova manuale fatta il 2026-10-26: alla domanda "Che ore sono a Tokyo adesso?" con uno
  strumento `orologio` dichiarato, Gemma ha risposto con `tool_calls` →
  `orologio({"fuso_orario": "Asia/Tokyo"})`. Il modello quindi supporta il tool calling.
- **Docker** 29.2.0, **Docker Compose** v5.0.2 (plugin `docker compose`, linea "v2" moderna).
- Configurazione solo da variabili d'ambiente; un `.env.example` versionato, `.env` escluso.
- Dipendenze motivate e con versioni fissate.
- Comandi documentati anche per PowerShell.
- Conventional Commits in italiano, staging selettivo, incrementi piccoli verificati.

## 6. Decisioni prese con l'utente

- Sessione = chat con un normale agente AI; si può chiedere l'ora locale e di altri paesi.
- "Ora locale" = **Europe/Rome**.
- Python 3.14; Compose v5 va bene così.
- Struttura: tutto nella radice `LLM/`, `lezione3/` lasciata com'è; repo `lab-llm-1`.
  L'utente ha già aggiornato `CLAUDE.md` di conseguenza (progetto in `LLM/`, specifica e piano
  in `LLM/docs/superpowers/`): non va riscritto, solo versionato.

## 7. Progetto della soluzione (scelte mie, da confermare con l'approvazione)

### 7.1 Dipendenze

| Pacchetto | Versione | Perché |
|---|---|---|
| `langgraph` | 1.2.17 | grafo esplicito (StateGraph, archi condizionali) |
| `langchain-openai` | 1.7.2 | client `ChatOpenAI` verso l'API OpenAI-compatibile di LM Studio, con `bind_tools` |
| `tzdata` | 2026.5 | database IANA per `zoneinfo`: indispensabile su Windows e nell'immagine slim |
| `pytest` | 9.1.1 | test (solo sviluppo) |

Si fissano le dipendenze dirette (`requirements.txt` per l'esecuzione, `requirements-dev.txt`
che include il primo più `pytest`). `langchain-core` e `openai` arrivano come transitive.
Le versioni sono le ultime pubblicate al 2026-10-26; il primo passo del piano verifica che si
installino e si importino su Python 3.14 (in caso contrario si scende alla versione compatibile
più recente e lo si annota).

### 7.2 Configurazione (variabili d'ambiente)

| Variabile | Obbligatoria | Default | Note |
|---|---|---|---|
| `LMSTUDIO_BASE_URL` | sì | — | locale: `http://localhost:1234/v1`; Docker: `http://host.docker.internal:1234/v1` |
| `LMSTUDIO_MODEL` | sì | — | id restituito da `GET /v1/models`, es. `google/gemma-4-e2b` |
| `FUSO_ORARIO_LOCALE` | no | `Europe/Rome` | fuso usato per "che ore sono?" senza luogo |
| `MAX_PASSI` | no | `5` | numero massimo di chiamate al modello per una domanda |
| `LOG_LEVEL` | no | `INFO` | livello dei log |

LM Studio non richiede chiave: al client si passa un valore segnaposto fisso nel codice
(non è una credenziale). Variabili mancanti o non valide (fuso inesistente, `MAX_PASSI` non
intero positivo) → messaggio chiaro e uscita con codice ≠ 0, senza traceback.

All'avvio il programma interroga `GET /v1/models` e, se `LMSTUDIO_MODEL` non è tra i modelli
serviti, si ferma indicando quelli disponibili; se il server non risponde, si ferma con un
messaggio che suggerisce di avviare LM Studio / controllare l'indirizzo.

### 7.3 Moduli

Pacchetto `assistente/` nella radice:

- `config.py` — lettura e validazione delle variabili d'ambiente.
- `strumenti.py` — lo strumento `orologio`, con orologio di sistema iniettabile.
- `modello.py` — costruzione del `ChatOpenAI` verso LM Studio e controllo dei modelli serviti.
- `grafo.py` — stato, nodi, instradamento, compilazione del grafo.
- `terminale.py` — ciclo di chat, cronologia di sessione, uscita.
- `__main__.py` — avvio con `python -m assistente`.

Test in `tests/`.

### 7.4 Strumento `orologio`

- Argomento: `fuso_orario` (stringa, identificativo IANA, es. `Asia/Tokyo`). Obbligatorio nello
  schema: il prompt di sistema dice al modello di usare `FUSO_ORARIO_LOCALE` quando l'utente
  chiede l'ora senza indicare un luogo. Così la chiamata è sempre esplicita e leggibile nei log.
- Risultato: testo/JSON con fuso, data e ora ISO 8601 con offset, giorno della settimana,
  abbreviazione del fuso (es. `CET`). Formato esatto lasciato al costruttore.
- Fuso inesistente → nessuna eccezione: il risultato è un messaggio d'errore leggibile che
  torna al modello (che può correggersi o spiegarlo all'utente) ed è registrato nei log.
- L'istante "adesso" viene da una funzione iniettabile, così i test usano un istante fisso.

### 7.5 Grafo

**Stato:**
- `messages`: lista dei messaggi (con il reducer standard di LangGraph per l'accodamento);
- `passi`: numero di chiamate al modello eseguite per la domanda corrente.

**Nodi:**
- `modello` — antepone il prompt di sistema (non salvato nella cronologia), chiama il modello
  con lo strumento collegato, accoda la risposta, incrementa `passi`.
- `strumenti` — nodo scritto a mano: per ogni `tool_call` dell'ultimo messaggio esegue
  `orologio`, accoda il `ToolMessage` col risultato e scrive nel log nome, argomenti, risultato
  e numero di passo.
- `limite` — raggiunto `MAX_PASSI`: per ogni `tool_call` pendente accoda un `ToolMessage`
  "non eseguito: limite di passaggi raggiunto" (così la cronologia resta valida per le
  domande successive) e poi un messaggio dell'assistente che avvisa l'utente. Log a livello
  WARNING.

**Instradamento** (dopo `modello`):
- nessuna `tool_call` → fine;
- `tool_call` presenti e `passi < MAX_PASSI` → `strumenti` → di nuovo `modello`;
- `tool_call` presenti e `passi >= MAX_PASSI` → `limite` → fine.

La funzione di instradamento è pura e testabile da sola. Il `recursion_limit` di LangGraph
resta come rete di sicurezza, sopra il limite esplicito.

### 7.6 Cronologia e terminale

- Il ciclo di chat tiene la lista dei messaggi della sessione: a ogni domanda invoca il grafo
  con `messages = cronologia + domanda` e `passi = 0`, poi sostituisce la cronologia con i
  messaggi restituiti (inclusi chiamate e risultati dello strumento). Nessun checkpointer,
  nessun file.
- Stampa su stdout solo le risposte dell'assistente; i log vanno su stderr con un prefisso
  riconoscibile, così chiamate allo strumento e risposte restano distinguibili.
- Uscita con `esci` (anche `exit`/`quit`), Ctrl+D/EOF o Ctrl+C, senza traceback.
- Riga vuota → ignorata.
- Errore di rete o del server durante una domanda → messaggio chiaro, la sessione continua e
  la cronologia non viene sporcata dalla domanda fallita.

### 7.7 Prompt di sistema

In italiano, breve: l'assistente risponde in italiano; per qualsiasi domanda su data/ora deve
usare lo strumento `orologio` invece di indovinare; se l'utente non indica un luogo usa il
fuso `FUSO_ORARIO_LOCALE`; per città/paesi sceglie l'identificativo IANA corrispondente.
Testo esatto lasciato al costruttore.

### 7.8 Docker

- `Dockerfile` su `python:3.14-slim`, installa `requirements.txt`, comando `python -m assistente`.
- `compose.yaml` con un servizio `assistente`: `stdin_open` e `tty` attivi, `env_file: .env`,
  `LMSTUDIO_BASE_URL` impostata a `http://host.docker.internal:1234/v1`,
  `extra_hosts: host.docker.internal:host-gateway` (serve su Linux, innocuo su Docker Desktop).
- Avvio interattivo: `docker compose run --rm assistente`.
- Il fuso del container (UTC) non conta: lo strumento usa sempre un fuso esplicito.

### 7.9 Git e file di supporto

- `.gitignore` nella radice (già scritto, nuovo, richiesto dall'utente): `.env` e varianti
  (tranne `.env.example`), ambienti virtuali, cache Python e di test, pesi dei modelli
  (`*.gguf`, `*.safetensors`, `*.bin`), file di editor/OS e `lezione3/repo-lab-llm/`
  (vecchia copia locale con un suo `.git`, `.venv`, `.env`).
- Primo commit: `CLAUDE.md` della radice, `.gitignore` e questa specifica.
- `README.md` nella radice con configurazione, avvio locale e Docker, test, prove reali e
  diagnosi; solo comandi verificati, anche per PowerShell.

## 8. Test e verifiche

### 8.1 Automatici (default, senza modello)

`pytest` deve passare con LM Studio spento. Coprono almeno:

- **Strumento:** istante fisso → ora corretta in `Europe/Rome` (anche a cavallo dell'ora
  legale), `Asia/Tokyo`, `America/New_York`; fuso inesistente → messaggio d'errore, nessuna
  eccezione.
- **Instradamento:** i tre casi (fine, strumenti, limite) sulla funzione pura.
- **Grafo** con un modello finto a risposte programmate:
  - domanda senza strumento → una risposta, `passi = 1`;
  - richiesta strumento → `ToolMessage` col risultato reale dello strumento (istante fisso),
    poi risposta finale;
  - modello che chiede sempre lo strumento → si ferma a `MAX_PASSI`, messaggio di avviso,
    nessuna `tool_call` senza risposta nella cronologia;
  - log della chiamata allo strumento presente (`caplog`).
- **Cronologia:** due domande di fila → la seconda chiamata al modello riceve anche la prima
  domanda e risposta.
- **Configurazione:** default, variabili mancanti, valori non validi.

### 8.2 Prove reali (attivate esplicitamente)

- Test pytest con marcatore `lmstudio`, esclusi di default e lanciati con
  `pytest -m lmstudio`: con LM Studio acceso e il modello configurato, chiedere l'ora a Tokyo
  e verificare che il modello abbia chiesto `orologio` con `Asia/Tokyo` e che la risposta
  finale contenga l'ora restituita dallo strumento.
- Prova Docker manuale documentata nel README: `docker compose build`,
  `docker compose run --rm assistente`, domande "che ore sono?" e "e a Tokyo?", controllo che
  i log mostrino le chiamate allo strumento e che la seconda domanda usi il contesto della
  prima.

### 8.3 Resoconto

A fine lavoro: cosa è stato eseguito, con quale esito, cosa resta da provare. Un test con
modello simulato non dimostra che Gemma sappia usare lo strumento.

## 9. Lasciato al costruttore

- Testo esatto del prompt di sistema e del messaggio di limite raggiunto.
- Formato esatto del risultato dello strumento e delle righe di log.
- Come realizzare il modello finto nei test.
- Dettagli interni dei moduli, purché resti la separazione del §7.3.
- Uso di `pyproject.toml` o `pytest.ini` per la configurazione di pytest e del marcatore.
