# Assistente con orologio — Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Obiettivo:** chat da terminale in Python che usa un grafo LangGraph esplicito per parlare con il
modello di LM Studio e chiamare uno strumento `orologio` con fuso orario IANA, eseguibile in
locale e con Docker Compose.

**Architettura:** pacchetto `assistente/` con moduli piccoli: `config` (variabili d'ambiente),
`strumenti` (orologio con istante iniettabile), `modello` (client verso LM Studio e controllo dei
modelli serviti), `grafo` (stato, nodi `modello`/`strumenti`/`limite`, instradamento), `terminale`
(ciclo di chat e cronologia di sessione), `__main__` (avvio). Test `pytest` con un modello finto;
prove reali separate con marcatore `lmstudio`.

**Stack:** Python 3.14, `langgraph` 1.2.17, `langchain-openai` 1.7.2, `tzdata` 2026.5,
`pytest` 9.1.1, Docker (`python:3.14-slim`) + Docker Compose v5.

**Specifica:** `docs/superpowers/specs/2026-10-26-assistente-orologio-design.md`

## Vincoli globali

- Radice del progetto = radice della repo `LLM/`, branch `main`. Non leggere né modificare `lezione3/`.
- Python 3.14; codice sincrono; nessuna dipendenza oltre a `langgraph==1.2.17`,
  `langchain-openai==1.7.2`, `tzdata==2026.5`, `pytest==9.1.1` (versioni fissate con `==`).
- Variabili d'ambiente: `LMSTUDIO_BASE_URL` (obbligatoria), `LMSTUDIO_MODEL` (obbligatoria),
  `FUSO_ORARIO_LOCALE` (default `Europe/Rome`), `MAX_PASSI` (default `5`), `LOG_LEVEL` (default `INFO`).
- Chiave API passata al client: segnaposto fisso `"lm-studio"` (non è una credenziale).
- Nome dello strumento: `orologio`; unico argomento `fuso_orario` (stringa IANA, obbligatorio).
- Nodi del grafo: `modello`, `strumenti`, `limite`. Niente `create_react_agent`, niente `ToolNode`
  preconfezionato, niente checkpointer.
- Risposte su stdout; log su stderr con prefisso `[log]`.
- Uscita con `esci`/`exit`/`quit`, EOF (Ctrl+D / Ctrl+Z+Invio) o Ctrl+C, senza traceback.
- Comandi documentati per PowerShell. Conventional Commits in italiano; prima di ogni commit
  `git status` + `git diff --cached`, staging selettivo; mai `.env`, `.venv`, cache. Nessun push.
- Ogni messaggio di commit termina con la riga
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Un test con modello finto non dimostra che Gemma sappia usare lo strumento: dirlo nel resoconto.

## Punti di attenzione per la revisione

1. **Fuso vuoto o malformato** (`""`, `"../etc/passwd"`, `"Europe/../Rome"`): l'orologio restituisce
   un errore leggibile, nessuna eccezione → test in Task 1.
2. **Il modello chiama lo strumento con argomenti mancanti o uno strumento inesistente**: il nodo
   `strumenti` risponde con un `ToolMessage` d'errore e il grafo prosegue → test in Task 4.
3. **Domanda dopo che il limite è scattato**: la cronologia non contiene `tool_call` senza
   risposta e il turno successivo funziona → test in Task 4.
4. **Errore di rete o Ctrl+C a metà turno**: messaggio chiaro o uscita pulita; la cronologia
   resta quella precedente alla domanda fallita → test in Task 4 e Task 5.
5. **Risposta finale vuota del modello**: il terminale stampa un segnaposto invece di una riga
   vuota → test in Task 5.

---

### Task 1: Ambiente, dipendenze e strumento orologio

**File:**
- Crea: `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `assistente/__init__.py`,
  `assistente/strumenti.py`
- Test: `tests/test_strumenti.py`

**Interfacce:**
- Produce:
  - `ora_utc() -> datetime` — `datetime.now(timezone.utc)`.
  - `ora_in_fuso(fuso_orario: str, adesso: Callable[[], datetime] = ora_utc) -> str` — stringa JSON
    (`json.dumps(..., ensure_ascii=False)`). Successo: chiavi `fuso_orario`, `data_ora`
    (ISO 8601 con offset, `timespec="seconds"`), `giorno` (nome italiano minuscolo), `abbreviazione`
    (`tzname()`). Errore: unica chiave `errore`, testo
    `"Fuso orario sconosciuto: '<valore>'. Usa un identificativo IANA, ad esempio Europe/Rome."`.
    Mai eccezioni (intercettare `ZoneInfoNotFoundError` e `ValueError`).
  - `crea_orologio(adesso: Callable[[], datetime] = ora_utc) -> BaseTool` — strumento LangChain di
    nome `orologio`, argomento `fuso_orario: str`, descrizione in italiano
    ("Restituisce data e ora correnti nel fuso orario IANA indicato, es. Europe/Rome, Asia/Tokyo.").

- [ ] **Step 1: File di dipendenze e configurazione di pytest**

  `requirements.txt`: `langgraph==1.2.17`, `langchain-openai==1.7.2`, `tzdata==2026.5`.
  `requirements-dev.txt`: `-r requirements.txt` e `pytest==9.1.1`.
  `pyproject.toml`, solo questo:

  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  pythonpath = ["."]
  markers = ["lmstudio: prove reali che richiedono LM Studio acceso (pytest -m lmstudio)"]
  addopts = "-m 'not lmstudio'"
  ```

  `assistente/__init__.py` vuoto.

- [ ] **Step 2: Creare il venv e installare**

  ```powershell
  py -3.14 -m venv .venv
  .\.venv\Scripts\python -m pip install -r requirements-dev.txt
  .\.venv\Scripts\python -c "import langgraph, langchain_openai, zoneinfo; print(zoneinfo.ZoneInfo('Asia/Tokyo'))"
  ```

  Atteso: installazione senza errori, stampa `Asia/Tokyo`. Se una versione non si installa su 3.14,
  scendere alla più recente compatibile, aggiornare i file e annotarlo nel resoconto.

- [ ] **Step 3: Scrivere i test che falliscono** in `tests/test_strumenti.py`

  ```python
  ISTANTE_INVERNO = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
  ISTANTE_ESTATE = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)

  def leggi(fuso, istante):
      return json.loads(ora_in_fuso(fuso, adesso=lambda: istante))

  def test_ora_roma_inverno():
      r = leggi("Europe/Rome", ISTANTE_INVERNO)
      assert r == {"fuso_orario": "Europe/Rome", "data_ora": "2026-10-26T13:00:00+01:00",
                   "giorno": "lunedì", "abbreviazione": "CET"}

  def test_ora_roma_estate():
      r = leggi("Europe/Rome", ISTANTE_ESTATE)
      assert (r["data_ora"], r["giorno"], r["abbreviazione"]) == (
          "2026-07-01T12:00:00+02:00", "mercoledì", "CEST")

  def test_ora_tokyo():
      r = leggi("Asia/Tokyo", ISTANTE_INVERNO)
      assert (r["data_ora"], r["abbreviazione"]) == ("2026-10-26T21:00:00+09:00", "JST")

  def test_ora_new_york():
      r = leggi("America/New_York", ISTANTE_INVERNO)
      assert (r["data_ora"], r["abbreviazione"]) == ("2026-10-26T08:00:00-04:00", "EDT")

  @pytest.mark.parametrize("fuso", ["Marte/Base", "", "../etc/passwd", "Europe/../Rome"])
  def test_fuso_non_valido_restituisce_errore(fuso):
      r = leggi(fuso, ISTANTE_INVERNO)
      assert list(r) == ["errore"]
      assert f"'{fuso}'" in r["errore"]

  def test_crea_orologio_espone_lo_strumento():
      strumento = crea_orologio(adesso=lambda: ISTANTE_INVERNO)
      assert strumento.name == "orologio"
      assert list(strumento.args) == ["fuso_orario"]
      r = json.loads(strumento.invoke({"fuso_orario": "Asia/Tokyo"}))
      assert r["data_ora"] == "2026-10-26T21:00:00+09:00"
  ```

- [ ] **Step 4: Verificare che falliscano**

  Run: `.\.venv\Scripts\python -m pytest tests/test_strumenti.py -v`
  Atteso: errore di import (`assistente.strumenti` non esiste).

- [ ] **Step 5: Implementare `assistente/strumenti.py`** secondo le interfacce sopra. Giorni con una
  tupla `("lunedì", ..., "domenica")` indicizzata da `weekday()`. `crea_orologio` con
  `StructuredTool.from_function` su una funzione interna `orologio(fuso_orario: str) -> str`.

- [ ] **Step 6: Verificare che passino**

  Run: `.\.venv\Scripts\python -m pytest tests/test_strumenti.py -v`
  Atteso: 9 passed.

- [ ] **Step 7: Commit** (due commit)

  ```powershell
  git add requirements.txt requirements-dev.txt pyproject.toml
  git commit -m "chore: fissa le dipendenze e configura pytest"   # + riga Co-Authored-By
  git add assistente/__init__.py assistente/strumenti.py tests/test_strumenti.py
  git commit -m "feat(strumenti): aggiunge lo strumento orologio con fuso IANA"
  ```

---

### Task 2: Configurazione

**File:**
- Crea: `assistente/config.py`
- Test: `tests/test_config.py`

**Interfacce:**
- Produce:
  - `class ErroreConfigurazione(Exception)` — messaggio leggibile per l'utente.
  - `@dataclass(frozen=True) class Config` con campi `base_url: str`, `modello: str`,
    `fuso_locale: str`, `max_passi: int`, `log_level: str`.
  - `carica_config(env: Mapping[str, str] | None = None) -> Config` — `None` ⇒ `os.environ`.
    Spazi rimossi; valore vuoto = mancante; `base_url` senza `/` finale; `log_level` in maiuscolo,
    ammessi `DEBUG`, `INFO`, `WARNING`, `ERROR`; fuso validato con `ZoneInfo`; `max_passi` intero ≥ 1.
    Raccoglie tutti i problemi e li riporta in un'unica `ErroreConfigurazione`, una riga per
    variabile, ciascuna col nome della variabile.

- [ ] **Step 1: Scrivere i test che falliscono**

  ```python
  BASE = {"LMSTUDIO_BASE_URL": "http://localhost:1234/v1/", "LMSTUDIO_MODEL": "google/gemma-4-e2b"}

  def test_valori_predefiniti():
      c = carica_config(BASE)
      assert c == Config("http://localhost:1234/v1", "google/gemma-4-e2b", "Europe/Rome", 5, "INFO")

  @pytest.mark.parametrize("nome", ["LMSTUDIO_BASE_URL", "LMSTUDIO_MODEL"])
  @pytest.mark.parametrize("valore", [None, "", "   "])
  def test_variabile_obbligatoria_mancante(nome, valore):
      env = dict(BASE)
      if valore is None: del env[nome]
      else: env[nome] = valore
      with pytest.raises(ErroreConfigurazione, match=nome): carica_config(env)

  def test_fuso_non_valido():
      with pytest.raises(ErroreConfigurazione, match="FUSO_ORARIO_LOCALE"):
          carica_config(BASE | {"FUSO_ORARIO_LOCALE": "Marte/Base"})

  @pytest.mark.parametrize("valore", ["0", "-1", "abc", "2.5"])
  def test_max_passi_non_valido(valore):
      with pytest.raises(ErroreConfigurazione, match="MAX_PASSI"):
          carica_config(BASE | {"MAX_PASSI": valore})

  def test_valori_personalizzati():
      c = carica_config(BASE | {"FUSO_ORARIO_LOCALE": "Asia/Tokyo", "MAX_PASSI": "3", "LOG_LEVEL": "debug"})
      assert (c.fuso_locale, c.max_passi, c.log_level) == ("Asia/Tokyo", 3, "DEBUG")

  def test_log_level_non_valido():
      with pytest.raises(ErroreConfigurazione, match="LOG_LEVEL"):
          carica_config(BASE | {"LOG_LEVEL": "boh"})

  def test_errori_multipli_in_un_solo_messaggio():
      with pytest.raises(ErroreConfigurazione) as e:
          carica_config({"MAX_PASSI": "0"})
      assert all(n in str(e.value) for n in ("LMSTUDIO_BASE_URL", "LMSTUDIO_MODEL", "MAX_PASSI"))
  ```

- [ ] **Step 2: Verificare che falliscano** — `.\.venv\Scripts\python -m pytest tests/test_config.py -v` → errore di import.
- [ ] **Step 3: Implementare `assistente/config.py`** secondo le interfacce.
- [ ] **Step 4: Verificare che passino** — stesso comando → 15 passed.
- [ ] **Step 5: Commit** — `feat(config): legge e valida la configurazione dalle variabili d'ambiente`.

---

### Task 3: Collegamento a LM Studio

**File:**
- Crea: `assistente/modello.py`
- Test: `tests/test_modello.py`

**Interfacce:**
- Consuma: `Config`, `ErroreConfigurazione` (Task 2).
- Produce:
  - `class ErroreServer(Exception)` — server irraggiungibile o risposta non valida; il messaggio
    contiene `base_url` e suggerisce di avviare LM Studio / controllare l'indirizzo.
  - `modelli_serviti(base_url: str, timeout: float = 5.0) -> list[str]` — `GET {base_url}/models`
    con `urllib.request` (nessuna dipendenza nuova); restituisce gli `id` di `data`.
    Errori di rete, HTTP ≠ 200, JSON non valido → `ErroreServer`.
  - `verifica_modello(config: Config, elenca: Callable[[str], list[str]] = modelli_serviti) -> None`
    — se `config.modello` non è tra gli id → `ErroreConfigurazione` che nomina `LMSTUDIO_MODEL` ed
    elenca i modelli disponibili.
  - `crea_modello(config: Config) -> ChatOpenAI` — `ChatOpenAI(model=config.modello,
    base_url=config.base_url, api_key="lm-studio", temperature=0, timeout=120, max_retries=1)`.

- [ ] **Step 1: Scrivere i test che falliscono**

  Fixture `server_finto` in `tests/test_modello.py`: `http.server.ThreadingHTTPServer` su
  `127.0.0.1:0` in un thread, con un handler che risponde a `GET /v1/models` con stato e corpo
  impostabili dal test; restituisce `http://127.0.0.1:<porta>/v1`; spegnimento a fine test.
  Fixture `porta_chiusa` in `tests/conftest.py` (servirà anche al Task 5): apre un socket su
  porta 0, legge la porta, lo chiude, restituisce `http://127.0.0.1:<porta>/v1`.

  ```python
  def test_modelli_serviti_legge_gli_id(server_finto):
      url = server_finto(200, {"data": [{"id": "google/gemma-4-e2b"}, {"id": "emb"}]})
      assert modelli_serviti(url) == ["google/gemma-4-e2b", "emb"]

  def test_server_irraggiungibile(porta_chiusa):
      with pytest.raises(ErroreServer, match=re.escape(porta_chiusa)):
          modelli_serviti(porta_chiusa, timeout=1)

  @pytest.mark.parametrize("stato,corpo", [(500, {"errore": "x"}), (200, "non json")])
  def test_risposta_non_valida(server_finto, stato, corpo):
      with pytest.raises(ErroreServer): modelli_serviti(server_finto(stato, corpo))

  def test_verifica_modello_presente():
      verifica_modello(CONFIG, elenca=lambda url: ["google/gemma-4-e2b"])

  def test_verifica_modello_assente_elenca_i_disponibili():
      with pytest.raises(ErroreConfigurazione, match="LMSTUDIO_MODEL") as e:
          verifica_modello(CONFIG, elenca=lambda url: ["altro/modello"])
      assert "altro/modello" in str(e.value)

  def test_crea_modello_punta_a_lm_studio():
      m = crea_modello(CONFIG)
      assert m.model_name == "google/gemma-4-e2b"
      assert m.openai_api_base == "http://localhost:1234/v1"
  ```

  (`CONFIG = Config("http://localhost:1234/v1", "google/gemma-4-e2b", "Europe/Rome", 5, "INFO")`;
  corpo stringa = scritto così com'è, corpo dict = serializzato JSON.)

- [ ] **Step 2: Verificare che falliscano** — `.\.venv\Scripts\python -m pytest tests/test_modello.py -v` → errore di import.
- [ ] **Step 3: Implementare `assistente/modello.py`** secondo le interfacce.
- [ ] **Step 4: Verificare che passino** — stesso comando → 7 passed.
- [ ] **Step 5: Commit** — `feat(modello): collega LM Studio e verifica il modello servito`.

---

### Task 4: Grafo LangGraph

**File:**
- Crea: `assistente/grafo.py`, `tests/aiuti.py`
- Modifica: `tests/conftest.py` (fixture `orologio_fisso`)
- Test: `tests/test_grafo.py`

**Interfacce:**
- Consuma: `crea_orologio`, `ora_in_fuso` (Task 1).
- Produce:
  - `class Stato(TypedDict)`: `messages: Annotated[list[AnyMessage], add_messages]`, `passi: int`.
  - `MESSAGGIO_LIMITE: str` — es. `"Mi fermo qui: ho raggiunto il limite di passaggi per questa
    domanda. Prova a riformularla."`
  - `RISULTATO_NON_ESEGUITO = "Non eseguito: limite di passaggi raggiunto."`
  - `prompt_sistema(fuso_locale: str) -> str` — in italiano: rispondi in italiano; per data/ora usa
    sempre `orologio`, mai indovinare; senza luogo usa `fuso_locale`; per città/paesi scegli
    l'identificativo IANA. Testo esatto a scelta.
  - `instrada(stato: Stato, max_passi: int) -> str` — ultimo messaggio senza `tool_calls` → `END`;
    con `tool_calls` e `passi < max_passi` → `"strumenti"`; altrimenti `"limite"`.
  - `crea_grafo(modello: BaseChatModel, strumenti: list[BaseTool], max_passi: int, prompt: str)
    -> CompiledStateGraph` — nodi:
    - `modello`: chiama `modello.bind_tools(strumenti)` con `[SystemMessage(prompt), *messages]`;
      restituisce `{"messages": [risposta], "passi": passi + 1}` (il `SystemMessage` non entra nello stato).
    - `strumenti`: per ogni `tool_call` dell'ultimo messaggio, `ToolMessage(content=..., tool_call_id=id,
      name=nome)`. Strumento sconosciuto → contenuto `"Errore: strumento sconosciuto '<nome>'."`;
      eccezione durante `invoke` (es. argomenti mancanti) → `"Errore: argomenti non validi per
      '<nome>': <eccezione>"`. Log INFO su logger `assistente.grafo`:
      `"passo %d: strumento %s(%s) -> %s"` con passo, nome, `json.dumps(args, ensure_ascii=False)`, risultato.
    - `limite`: un `ToolMessage(RISULTATO_NON_ESEGUITO)` per ogni `tool_call` pendente, poi
      `AIMessage(MESSAGGIO_LIMITE)`; log WARNING `"limite di %d passaggi raggiunto"`.
    - Archi: `START → modello`; condizionale da `modello` con `instrada` verso
      `["strumenti", "limite", END]`; `strumenti → modello`; `limite → END`.
  - `esegui_turno(grafo, cronologia: list[AnyMessage], domanda: str, max_passi: int)
    -> list[AnyMessage]` — invoca con `{"messages": [*cronologia, HumanMessage(domanda)], "passi": 0}`
    e `config={"recursion_limit": 2 * max_passi + 4}`; restituisce `risultato["messages"]`.
    Non modifica la lista `cronologia` passata; le eccezioni del modello si propagano.

- [ ] **Step 1: Modello finto e aiuti in `tests/aiuti.py`** (importati nei test con
  `from aiuti import ...`; la cartella `tests/` è nel `sys.path` di pytest)

  Va scritto così, perché `add_messages` sostituisce (invece di accodare) un messaggio con lo
  stesso `id`: ogni risposta deve essere una copia nuova senza id. Se pydantic rifiuta il campo
  `errore`, aggiungere `model_config = ConfigDict(arbitrary_types_allowed=True)`.

  ```python
  class ModelloFinto(BaseChatModel):
      risposte: list[AIMessage]          # l'ultima si ripete all'infinito
      errore: BaseException | None = None
      chiamate: list[list[BaseMessage]] = Field(default_factory=list)

      @property
      def _llm_type(self) -> str: return "finto"

      def bind_tools(self, tools, **kwargs): return self

      def _generate(self, messages, stop=None, run_manager=None, **kwargs):
          self.chiamate.append(list(messages))
          if self.errore: raise self.errore
          i = min(len(self.chiamate) - 1, len(self.risposte) - 1)
          msg = self.risposte[i].model_copy(deep=True, update={"id": None})
          return ChatResult(generations=[ChatGeneration(message=msg)])

  def chiamata(nome="orologio", args=None, id="c1") -> AIMessage:
      args = {"fuso_orario": "Asia/Tokyo"} if args is None else args
      return AIMessage(content="", tool_calls=[{"name": nome, "args": args, "id": id, "type": "tool_call"}])

  ISTANTE = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
  ```

  Sempre in `tests/aiuti.py`: `def grafo_con(risposte, orologio, max_passi=5, errore=None)` che crea
  `ModelloFinto` e `crea_grafo(finto, [orologio], max_passi, prompt_sistema("Europe/Rome"))` e
  restituisce `(grafo, finto)`; `def conta_coerenza(msgs)` → `(n. tool_calls nei AIMessage, n. ToolMessage)`.
  In `tests/conftest.py`: fixture `orologio_fisso` → `crea_orologio(adesso=lambda: ISTANTE)`.

- [ ] **Step 2: Scrivere i test che falliscono** in `tests/test_grafo.py`

  ```python
  def test_instrada_senza_tool_call_termina():
      assert instrada({"messages": [AIMessage("ok")], "passi": 1}, 5) == END
  def test_instrada_con_tool_call_va_a_strumenti():
      assert instrada({"messages": [chiamata()], "passi": 1}, 5) == "strumenti"
  def test_instrada_al_limite_va_a_limite():
      assert instrada({"messages": [chiamata()], "passi": 5}, 5) == "limite"

  def test_risposta_diretta(orologio_fisso):
      g, finto = grafo_con([AIMessage("Ciao!")], orologio_fisso)
      r = g.invoke({"messages": [HumanMessage("ciao")], "passi": 0})
      assert r["passi"] == 1 and r["messages"][-1].content == "Ciao!"
      assert isinstance(finto.chiamate[0][0], SystemMessage)
      assert not any(isinstance(m, SystemMessage) for m in r["messages"])

  def test_strumento_eseguito_e_risposta_finale(orologio_fisso):
      g, finto = grafo_con([chiamata(), AIMessage("A Tokyo sono le 21:00.")], orologio_fisso)
      msgs = esegui_turno(g, [], "Che ore sono a Tokyo?", 5)
      assert [type(m) for m in msgs] == [HumanMessage, AIMessage, ToolMessage, AIMessage]
      assert msgs[2].tool_call_id == "c1"
      assert "2026-10-26T21:00:00+09:00" in msgs[2].content
      assert msgs[2] in finto.chiamate[1]

  def test_log_della_chiamata(orologio_fisso, caplog):
      caplog.set_level(logging.INFO, logger="assistente.grafo")
      g, _ = grafo_con([chiamata(), AIMessage("ok")], orologio_fisso)
      esegui_turno(g, [], "ora a Tokyo?", 5)
      testo = caplog.text
      assert "orologio" in testo and "Asia/Tokyo" in testo and "21:00:00+09:00" in testo

  def test_limite_di_passaggi(orologio_fisso):
      g, finto = grafo_con([chiamata()], orologio_fisso, max_passi=3)
      msgs = esegui_turno(g, [], "ora?", 3)
      assert len(finto.chiamate) == 3
      tool = [m for m in msgs if isinstance(m, ToolMessage)]
      assert [m.content == RISULTATO_NON_ESEGUITO for m in tool] == [False, False, True]
      assert msgs[-1].content == MESSAGGIO_LIMITE
      assert conta_coerenza(msgs)[0] == conta_coerenza(msgs)[1]

  def test_domanda_dopo_il_limite(orologio_fisso):
      g, finto = grafo_con([chiamata(), chiamata(), AIMessage("ripreso")], orologio_fisso, max_passi=2)
      prima = esegui_turno(g, [], "ora?", 2)
      dopo = esegui_turno(g, prima, "e adesso?", 2)
      assert dopo[-1].content == "ripreso"
      assert conta_coerenza(dopo)[0] == conta_coerenza(dopo)[1]

  def test_strumento_sconosciuto(orologio_fisso):
      g, _ = grafo_con([chiamata(nome="meteo", args={}), AIMessage("ok")], orologio_fisso)
      msgs = esegui_turno(g, [], "meteo?", 5)
      assert msgs[2].content == "Errore: strumento sconosciuto 'meteo'."

  def test_argomenti_mancanti(orologio_fisso):
      g, _ = grafo_con([chiamata(args={}), AIMessage("ok")], orologio_fisso)
      msgs = esegui_turno(g, [], "ora?", 5)
      assert msgs[2].content.startswith("Errore: argomenti non validi per 'orologio'")

  def test_cronologia_tra_due_domande(orologio_fisso):
      g, finto = grafo_con([AIMessage("Prima"), AIMessage("Seconda")], orologio_fisso)
      c1 = esegui_turno(g, [], "domanda 1", 5)
      c2 = esegui_turno(g, c1, "domanda 2", 5)
      assert [m.content for m in c2] == ["domanda 1", "Prima", "domanda 2", "Seconda"]
      assert [m.content for m in finto.chiamate[1][1:]] == ["domanda 1", "Prima", "domanda 2"]

  def test_errore_del_modello_non_tocca_la_cronologia(orologio_fisso):
      g, _ = grafo_con([AIMessage("x")], orologio_fisso, errore=RuntimeError("giù"))
      cronologia = [HumanMessage("vecchia"), AIMessage("risposta")]
      with pytest.raises(RuntimeError): esegui_turno(g, cronologia, "nuova", 5)
      assert [m.content for m in cronologia] == ["vecchia", "risposta"]

  def test_prompt_sistema_cita_fuso_e_strumento():
      p = prompt_sistema("Europe/Rome")
      assert "Europe/Rome" in p and "orologio" in p
  ```

- [ ] **Step 3: Verificare che falliscano** — `.\.venv\Scripts\python -m pytest tests/test_grafo.py -v` → errore di import.
- [ ] **Step 4: Implementare `assistente/grafo.py`** secondo le interfacce.
- [ ] **Step 5: Verificare che passino** — `.\.venv\Scripts\python -m pytest -v` → tutti i test passano (Task 1–4).
- [ ] **Step 6: Commit** — `feat(grafo): aggiunge il grafo con nodi modello, strumenti e limite`
  (file `assistente/grafo.py`, `tests/aiuti.py`, `tests/conftest.py`, `tests/test_grafo.py`).

---

### Task 5: Terminale e avvio

**File:**
- Crea: `assistente/terminale.py`, `assistente/__main__.py`
- Test: `tests/test_terminale.py`, `tests/test_main.py`

**Interfacce:**
- Consuma: `carica_config`, `ErroreConfigurazione` (T2); `verifica_modello`, `crea_modello`,
  `ErroreServer` (T3); `crea_orologio` (T1); `crea_grafo`, `esegui_turno`, `prompt_sistema` (T4).
- Produce:
  - `COMANDI_USCITA = {"esci", "exit", "quit"}`, `RISPOSTA_VUOTA = "(il modello non ha dato una risposta)"`.
  - `configura_log(livello: str) -> None` — `logging.basicConfig(level=livello, stream=sys.stderr,
    format="[log] %(levelname)s %(name)s: %(message)s", force=True)`; logger `httpx` e `openai`
    a WARNING se `livello != "DEBUG"`.
  - `chat(grafo, max_passi: int, leggi: Callable[[str], str] = input, scrivi: Callable[[str], None] = print) -> None`
    — saluto iniziale con le istruzioni di uscita; ciclo: `leggi("tu> ")`, riga vuota ignorata,
    comando di uscita (case-insensitive) → `scrivi("Alla prossima!")` e ritorno; altrimenti
    `esegui_turno`, poi `scrivi(f"assistente> {testo or RISPOSTA_VUOTA}")`.
    `openai.APIError` durante il turno → `scrivi` di un messaggio che nomina LM Studio, log a DEBUG
    con traceback, cronologia invariata, il ciclo continua. `EOFError`/`KeyboardInterrupt`
    (in lettura o durante il turno) → `scrivi("Alla prossima!")` e ritorno.
  - `main(env: Mapping[str, str] | None = None) -> int` in `__main__.py` — config non valida →
    messaggio su stderr, `2`; `ErroreServer` o modello assente all'avvio → messaggio su stderr, `1`;
    altrimenti costruisce tutto, esegue `chat`, `0`. Fine file: `if __name__ == "__main__": sys.exit(main())`.

- [ ] **Step 1: Scrivere i test che falliscono**

  `tests/test_terminale.py` — helper `ingressi(*righe)` che restituisce una `leggi` che emette le righe
  in ordine (un elemento eccezione viene sollevato) e poi solleva `EOFError`; `scrivi` = `uscita.append`.

  ```python
  def test_esci_termina_senza_chiamare_il_modello(orologio_fisso):
      g, finto = grafo_con([AIMessage("x")], orologio_fisso); uscita = []
      chat(g, 5, ingressi("ESCI"), uscita.append)
      assert finto.chiamate == [] and uscita[-1] == "Alla prossima!"

  @pytest.mark.parametrize("eccezione", [EOFError(), KeyboardInterrupt()])
  def test_eof_e_ctrl_c_terminano(orologio_fisso, eccezione):
      g, _ = grafo_con([AIMessage("x")], orologio_fisso); uscita = []
      chat(g, 5, ingressi(eccezione), uscita.append)
      assert uscita[-1] == "Alla prossima!"

  def test_riga_vuota_ignorata_e_risposta_stampata(orologio_fisso):
      g, finto = grafo_con([AIMessage("Ciao!")], orologio_fisso); uscita = []
      chat(g, 5, ingressi("   ", "ciao", "esci"), uscita.append)
      assert len(finto.chiamate) == 1 and "assistente> Ciao!" in uscita

  def test_risposta_vuota_mostra_segnaposto(orologio_fisso):
      g, _ = grafo_con([AIMessage("")], orologio_fisso); uscita = []
      chat(g, 5, ingressi("ciao", "esci"), uscita.append)
      assert f"assistente> {RISPOSTA_VUOTA}" in uscita

  def test_errore_di_rete_non_chiude_la_sessione(orologio_fisso):
      errore = openai.APIConnectionError(request=httpx.Request("POST", "http://x"))
      g, finto = grafo_con([AIMessage("ok")], orologio_fisso, errore=errore); uscita = []
      chat(g, 5, ingressi("prima", "seconda", "esci"), uscita.append)
      assert len(finto.chiamate) == 2
      assert [m.content for m in finto.chiamate[1][1:]] == ["seconda"]   # "prima" non è in cronologia
      assert any("LM Studio" in r for r in uscita)

  def test_ctrl_c_durante_il_turno(orologio_fisso):
      g, _ = grafo_con([AIMessage("x")], orologio_fisso, errore=KeyboardInterrupt()); uscita = []
      chat(g, 5, ingressi("ciao"), uscita.append)
      assert uscita[-1] == "Alla prossima!"
  ```

  `tests/test_main.py`:

  ```python
  def test_config_mancante_esce_con_2(capsys):
      assert main({}) == 2
      assert "LMSTUDIO_BASE_URL" in capsys.readouterr().err

  def test_server_spento_esce_con_1(capsys, porta_chiusa):
      assert main({"LMSTUDIO_BASE_URL": porta_chiusa, "LMSTUDIO_MODEL": "m"}) == 1
      assert porta_chiusa in capsys.readouterr().err
  ```

- [ ] **Step 2: Verificare che falliscano** — `.\.venv\Scripts\python -m pytest tests/test_terminale.py tests/test_main.py -v` → errore di import.
- [ ] **Step 3: Implementare `assistente/terminale.py` e `assistente/__main__.py`** secondo le interfacce.
- [ ] **Step 4: Verificare che passino** — `.\.venv\Scripts\python -m pytest -v` → tutto verde, nessun test `lmstudio` eseguito.
- [ ] **Step 5: Commit** — `feat(terminale): aggiunge il ciclo di chat e l'avvio con python -m assistente`.

---

### Task 6: Prova reale con LM Studio

**File:**
- Crea: `.env.example`, `tests/test_reale_lmstudio.py`

**Interfacce:**
- Consuma: tutto quanto sopra.

- [ ] **Step 1: `.env.example`** senza credenziali:

  ```
  # Copiare in .env e adattare. L'id del modello è quello restituito da GET /v1/models.
  LMSTUDIO_BASE_URL=http://localhost:1234/v1
  LMSTUDIO_MODEL=google/gemma-4-e2b
  FUSO_ORARIO_LOCALE=Europe/Rome
  MAX_PASSI=5
  LOG_LEVEL=INFO
  ```

- [ ] **Step 2: Test reali** marcati `@pytest.mark.lmstudio` (a livello di modulo con `pytestmark`).
  Config da `carica_config()` (se fallisce → `pytest.fail` col messaggio). Grafo con `crea_modello(cfg)`,
  `crea_orologio(adesso=lambda: ISTANTE)` (2026-10-26T12:00Z), `cfg.max_passi`.

  ```python
  def chiamate_orologio(msgs):
      return [tc["args"] for m in msgs if isinstance(m, AIMessage) for tc in m.tool_calls
              if tc["name"] == "orologio"]

  def test_reale_ora_a_tokyo(grafo_reale):
      msgs = esegui_turno(grafo_reale, [], "Che ore sono a Tokyo adesso?", 5)
      assert {"fuso_orario": "Asia/Tokyo"} in chiamate_orologio(msgs)
      assert any(isinstance(m, ToolMessage) for m in msgs)
      assert "21" in msgs[-1].content

  def test_reale_ora_locale(grafo_reale):
      msgs = esegui_turno(grafo_reale, [], "Che ore sono?", 5)
      assert {"fuso_orario": "Europe/Rome"} in chiamate_orologio(msgs)
      assert "13" in msgs[-1].content
  ```

- [ ] **Step 3: Verificare che restino esclusi di default**

  Run: `.\.venv\Scripts\python -m pytest`
  Atteso: tutti i test passano, `2 deselected`.

- [ ] **Step 4: Eseguire la prova reale** (LM Studio acceso con `google/gemma-4-e2b` caricato)

  ```powershell
  Copy-Item .env.example .env
  Get-Content .env | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
      $n, $v = $_ -split '=', 2; Set-Item "env:$($n.Trim())" $v.Trim() }
  .\.venv\Scripts\python -m pytest -m lmstudio -v
  ```

  Atteso: 2 passed. Se falliscono, annotare l'esito reale (cosa ha chiesto il modello) nel
  resoconto: non correggere i test per farli passare.

- [ ] **Step 5: Sessione manuale** — `.\.venv\Scripts\python -m assistente`; chiedere
  "che ore sono?", "e a Tokyo?", poi `esci`. Atteso: righe `[log] INFO assistente.grafo: passo 1:
  strumento orologio({"fuso_orario": "Europe/Rome"}) -> ...` e poi `Asia/Tokyo`, risposte coerenti
  con l'ora reale, la seconda domanda capita grazie al contesto.
- [ ] **Step 6: Commit** — `test(reale): aggiunge le prove con LM Studio e il file .env.example`
  (verificare con `git status` che `.env` non compaia).

---

### Task 7: Docker e Docker Compose

**File:**
- Crea: `Dockerfile`, `compose.yaml`, `.dockerignore`

- [ ] **Step 1: `Dockerfile`** — `FROM python:3.14-slim`; `ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1`;
  `WORKDIR /app`; copia e installa `requirements.txt` con `pip install --no-cache-dir`; copia
  `assistente/`; utente non root (`useradd --create-home app`, `USER app`);
  `CMD ["python", "-m", "assistente"]`.

- [ ] **Step 2: `compose.yaml`**

  ```yaml
  services:
    assistente:
      build: .
      stdin_open: true
      tty: true
      env_file: .env
      environment:
        LMSTUDIO_BASE_URL: http://host.docker.internal:1234/v1
      extra_hosts:
        - "host.docker.internal:host-gateway"
  ```

  `.dockerignore`: `.git`, `.venv`, `.env`, `__pycache__`, `.pytest_cache`, `tests`, `docs`, `lezione3`.

- [ ] **Step 3: Verificare configurazione e build**

  ```powershell
  docker compose config
  docker compose build
  ```

  Atteso: configurazione stampata con `LMSTUDIO_BASE_URL: http://host.docker.internal:1234/v1`
  (l'`environment` prevale su `.env`), build completata.

- [ ] **Step 4: Verificare che il container raggiunga LM Studio**

  ```powershell
  docker compose run --rm assistente python -c "from assistente.modello import modelli_serviti; print(modelli_serviti('http://host.docker.internal:1234/v1'))"
  ```

  Atteso: lista con `google/gemma-4-e2b`. Se fallisce: in LM Studio attivare "Serve on Local
  Network" e riprovare; annotare quale configurazione è servita (finirà nel README).

- [ ] **Step 5: Sessione manuale in Docker** — `docker compose run --rm assistente`, domande
  "che ore sono?" e "e a Tokyo?", poi `esci`. Atteso come Task 6 Step 5.
- [ ] **Step 6: Commit** — `feat(docker): aggiunge Dockerfile e compose per l'avvio in container`.

---

### Task 8: Documentazione e resoconto

**File:**
- Crea: `README.md`
- Modifica: `CLAUDE.md` (riga 4 e nuove sezioni "Struttura" e "Comandi")

- [ ] **Step 1: `README.md`** — sezioni: cosa fa; requisiti (Python 3.14, Docker Compose v5, LM Studio
  con un modello che supporta il tool calling); configurazione (`.env` da `.env.example`, come
  trovare l'id con `Invoke-RestMethod http://localhost:1234/v1/models`, come caricare `.env` in
  PowerShell); avvio locale; avvio con Docker; test automatici; prove reali (`pytest -m lmstudio`,
  sessione Docker); com'è fatto il grafo (stato, nodi, instradamento, limite); diagnosi (LM Studio
  spento, modello errato, container che non raggiunge l'host, limite di passaggi). Solo i comandi
  effettivamente eseguiti nei Task 1–7, con l'esito osservato.

- [ ] **Step 2: `CLAUDE.md`** — sostituire "all'inizio contiene soltanto questo file. Struttura,
  dipendenze e comandi verranno definiti con la specifica e il piano." con il rimando alla
  specifica; aggiungere la struttura dei file e i comandi di test (`pytest`, `pytest -m lmstudio`).
  Nessuna annotazione di avanzamento.

- [ ] **Step 3: Verifica finale**

  ```powershell
  .\.venv\Scripts\python -m pytest -v
  git status
  ```

  Atteso: tutto verde, `2 deselected`; nessun file non voluto (`.env`, `.venv`) tra i non tracciati.

- [ ] **Step 4: Commit** — `docs: aggiunge il README e aggiorna CLAUDE.md con struttura e comandi`.

- [ ] **Step 5: Resoconto all'utente** — cosa è stato eseguito (test automatici, prova reale
  `lmstudio`, sessione locale, build e sessione Docker) con esito, cosa resta da provare; ricordare
  che i test con modello finto non dimostrano il tool calling di Gemma. Nessun push.
