# Assistente del laboratorio
- Obiettivo: un client Python per un modello locale.
- client.py contiene lo scheletro da completare.
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
- Un'estensione alla volta: niente cronologia, streaming o altre funzioni non richieste.

## Verifica
- Provare davvero il client: una risposta reale e un errore comprensibile con server non raggiungibile.
- Se LM Studio non è disponibile, dirlo; non simulare una risposta.
- Distinguere nel resoconto le prove eseguite da quelle ancora da fare.

## Git
- La repository è pubblica: non committare `.env`, `.venv/`, pesi, log, slide o altro materiale del corso.
- Prima di ogni commit controllare `git diff` e `git diff --staged`: deve contenere una sola modifica logica.
- Un commit per estensione, con titolo `feat(client): ...` e corpo che descrive cosa è cambiato e come è stato verificato.
- Niente commit o push senza richiesta esplicita; niente reset o riscritture distruttive della storia.
