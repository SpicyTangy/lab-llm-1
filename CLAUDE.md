# Assistente del laboratorio
- Obiettivo: un client Python per un modello locale.
- client.py è il client completo, in un unico file (vedi "Funzionamento del client").
- README.md descrive la preparazione dell'ambiente.
- requirements.txt contiene le dipendenze concordate.
- Usare PowerShell nei comandi per Windows.
- Preferire Python sincrono e modifiche circoscritte.
- Non aggiungere dipendenze senza motivarle e concordarle.
- Non inserire segreti, pesi o ambiente virtuale in Git.
- Non sono presenti test automatici in questo checkpoint.

## Codice
- Conservare import e gestione degli errori già presenti; modificare solo ciò che serve alla richiesta.
- URL e nome del modello si leggono da `.env` (`LM_BASE_URL`, `LM_MODEL`), mai scritti nel codice.
- Eseguire il client con `.\.venv\Scripts\python.exe client.py`.
- Un'estensione alla volta: piano prima della modifica, poi la verifica; niente funzioni non richieste.

## Funzionamento del client
Le estensioni si sommano in quest'ordine, ognuna in un commit dedicato.
1. **Input da terminale:** ciclo con `input("Tu> ")`. Si esce con `esci` (anche maiuscolo), Ctrl+C o fine input, senza traceback; le righe vuote sono ignorate. Il `try/except` è dentro il ciclo: con il server fermo stampa l'errore e chiede la domanda successiva.
2. **Streaming:** `"stream": True` e POST con `stream=True`, `timeout=(5, 120)`. Legge le righe `data: {...}` fino a `data: [DONE]`, decodifica esplicitamente in UTF-8 (il server non dichiara il charset e `requests` userebbe ISO-8859-1, rovinando gli accenti), stampa ogni `choices[0].delta.content` con `flush=True` e accumula il testo completo in `testo`. Non usare `with` sulla risposta: l'`except HTTPError` legge `response.text` dopo, e con il `with` risulterebbe vuoto; la risposta si chiude con `response.close()`.
3. **Cronologia in memoria:** la lista `messages` parte dal solo messaggio `system`; il payload invia `messages` più la domanda corrente. Domanda e risposta (`testo`) si aggiungono solo dopo una risposta completa e non vuota, così una richiesta fallita non lascia nulla nella lista. Vive solo nel processo: alla chiusura si perde, nessun file o database.

Limiti noti, da non nascondere nei resoconti:
- La cronologia non viene mai accorciata: la richiesta si allunga a ogni turno, fino al limite di contesto del modello.
- Una risposta troncata da `max_tokens` resta troncata nella cronologia.
- Ctrl+C durante la risposta e le connessioni interrotte a metà non sono gestiti dagli `except`.
- Se LM Studio risponde 200 con un errore in JSON (es. percorso sbagliato), non ci sono righe `data: ` e il client stampa solo una riga vuota.

## Ambiente (Windows, PowerShell)
- Python: usare `python`; il launcher `py` può mancare. Creare la `.venv` sul PC con `python -m venv .venv` e `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Una `.venv` con cartella `bin/` invece di `Scripts/` è di tipo Linux e non funziona: va ricreata (è in `.gitignore`).
- `.env` non è nella repo: crearlo con `Copy-Item .env.example .env` e mettere in `LM_MODEL` l'id restituito da `GET {LM_BASE_URL}/models` (finora `google/gemma-4-e2b`). Non sovrascrivere un `.env` già presente.
- LM Studio deve avere il server avviato (sezione Developer, porta 1234) e il modello caricato per ogni prova reale.
- PowerShell mostra come errori rossi i messaggi normali di Git su stderr (`Switched to branch`, esito di `push`): controllare l'output e il codice di uscita, non il colore. Non usare `$ErrorActionPreference = "Stop"` con Git.
- Messaggi di commit con virgolette o su più righe: scriverli in un file (UTF-8 senza BOM, fine riga LF) e usare `git commit -F file`; con `-m` PowerShell spezza gli argomenti. Gli avvisi "LF will be replaced by CRLF" sono innocui.
- Script e file di prova temporanei vanno fuori dalla repo, non dentro.

## Come provare il client
- Non ci sono test automatici: si pilota il client da stdin, ad esempio `"domanda`nesci" | .\.venv\Scripts\python.exe client.py`, con `$env:PYTHONIOENCODING = "utf-8"` per leggere bene gli accenti.
- Gli errori si simulano con variabili del solo processo, senza toccare `.env`: `$env:LM_BASE_URL = "http://localhost:1/v1"` per il server non raggiungibile, poi `Remove-Item Env:LM_BASE_URL`. Un modello inesistente non basta: LM Studio risponde lo stesso con il modello caricato.
- Un vero errore HTTP si ottiene con un payload non valido; un percorso sbagliato dà invece `200` con un errore in JSON.
- Ctrl+C e l'arrivo progressivo del testo in streaming non si verificano da script: chiederli all'utente e segnalare nel resoconto che non sono stati provati.

## Verifica
- Provare davvero il client: una risposta reale e un errore comprensibile con server non raggiungibile.
- Se LM Studio non è disponibile, dirlo; non simulare una risposta.
- Distinguere nel resoconto le prove eseguite da quelle ancora da fare.

## Git
- `main` contiene solo codice stabile e verificato; `develop` è per i lavori in corso.
- Si porta il lavoro su `main` solo dopo la verifica, con un merge da `develop`, mai con commit diretti.
- La repository è pubblica: non committare `.env`, `.venv/`, pesi, log, slide o altro materiale del corso.
- Prima di ogni commit controllare `git diff` e `git diff --staged`: deve contenere una sola modifica logica.
- Un commit per estensione, con titolo `feat(client): ...` e corpo che descrive cosa è cambiato e come è stato verificato.
- Niente commit o push senza richiesta esplicita; niente reset o riscritture distruttive della storia.

## Inizio sessione
- Capire lo stato dalla repo, non da note: `git branch --show-current`, `git status`, `git log --oneline -8`; lavorare su `develop`.
- Per ogni nuova estensione: leggere `client.py`, proporre un piano breve con le prove, attendere il via e solo dopo modificare.
- `PIANO.md` può esistere in locale come file non tracciato: non committarlo senza richiesta.
- Se il client non risponde, partire dalla tabella di diagnosi del `README.md`.

## Idee non ancora fatte
- Cronologia salvata su file, per sopravvivere alla chiusura: il file va in `.gitignore` perché la repo è pubblica e la cronologia può contenere dati personali. Da concordare prima.
- Gestire i limiti noti elencati sopra (messaggio chiaro per il `200` con errore in JSON, Ctrl+C durante la risposta, connessioni interrotte) e accorciare la cronologia: ognuno in un commit dedicato.
