# repo-lab-llm

Client Python minimo che invia una domanda a un modello eseguito in locale con LM Studio e stampa la risposta. Materiale della Lezione 3 del corso Deep Learning e LLM (ITS Alto Adriatico).

## Contenuto della repository

| File | Funzione |
|---|---|
| `client.py` | Scheletro del client da completare con Claude Code |
| `requirements.txt` | Dipendenze con versioni fissate |
| `.env.example` | Modello della configurazione locale, senza segreti |
| `CLAUDE.md` | Istruzioni di sviluppo lette da Claude Code |
| `.gitignore` | File esclusi da Git: configurazione locale, ambiente virtuale, pesi, log |

## Prerequisiti

- Windows con PowerShell, Git e VS Code (estensioni Python e Git Graph).
- Python con il launcher `py`.
- LM Studio con il modello `google/gemma-4-e2b`, quantizzazione a 4 bit (`Q4_K_M`).
- Claude Code CLI: guida ufficiale <https://code.claude.com/docs/en/setup>. In PowerShell: `irm https://claude.ai/install.ps1 | iex`, poi riaprire il terminale e verificare con `claude --version`.

## Preparazione

Dalla radice della repository:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In VS Code selezionare l'interprete `.venv` con **Python: Select Interpreter**.

## Configurazione

1. In LM Studio scaricare e caricare `google/gemma-4-e2b` (4 bit), poi avviare il server dalla sezione Developer.
2. Leggere l'identificativo del modello esposto dal server:

   ```powershell
   $base = "http://localhost:1234/v1"
   (Invoke-RestMethod "$base/models").data | Select-Object id
   ```

3. Creare la configurazione locale, solo se `.env` non esiste già, e inserire l'identificativo letto al punto 2 al posto di `ID_MODELLO_REALE`:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

`.env` resta sul proprio computer ed è escluso da Git.

## Avvio

```powershell
.\.venv\Scripts\python.exe client.py
```

Il client chiede una domanda al prompt `Tu>`, stampa il testo della risposta e ne chiede un'altra. Si esce con `esci`, con Ctrl+C o a fine input; le righe vuote sono ignorate. Ogni domanda è una richiesta indipendente: il modello non ricorda le precedenti. La risposta può risultare troncata: `max_tokens` è 180.

## Verifica

1. Con il server di LM Studio acceso, due domande diverse nella stessa esecuzione ricevono ciascuna una risposta; `esci` chiude il programma.
2. Per provare l'errore, in PowerShell si indica una porta senza server solo per quel processo, senza modificare `.env`:

   ```powershell
   $env:LM_BASE_URL = "http://localhost:1/v1"
   .\.venv\Scripts\python.exe client.py
   Remove-Item Env:LM_BASE_URL
   ```

   Atteso: `Connessione fallita: controllare server, URL e porta.`

## Diagnosi rapida

| Messaggio | Primo controllo |
|---|---|
| `Connessione fallita` | LM Studio acceso, server avviato, URL e porta in `.env` |
| `Errore HTTP` con messaggio sul modello | Identificativo in `.env`, modello caricato |
| `Attesa scaduta` | Carico del computer, tempi del modello |
| Risposta vuota | `"reasoning_effort": "none"` nel payload: senza, il modello ragiona e consuma i token prima di rispondere |
| `KeyError: 'LM_BASE_URL'` o `'LM_MODEL'` | `.env` mancante o variabile non definita |

Una risposta arrivata non è necessariamente corretta: va letta e valutata.
