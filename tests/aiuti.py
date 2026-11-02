"""Aiuti per i test: un modello finto a risposte programmate e qualche costruttore."""

from datetime import datetime, timezone

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, Field

from assistente.grafo import crea_grafo, prompt_sistema

ISTANTE = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


class ModelloFinto(BaseChatModel):
    """Restituisce le risposte in ordine; l'ultima si ripete all'infinito."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    risposte: list[AIMessage]
    errore: BaseException | None = None
    chiamate: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "finto"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.chiamate.append(list(messages))
        if self.errore:
            raise self.errore
        i = min(len(self.chiamate) - 1, len(self.risposte) - 1)
        # Copia senza id: add_messages sostituirebbe un messaggio con lo stesso id.
        msg = self.risposte[i].model_copy(deep=True, update={"id": None})
        return ChatResult(generations=[ChatGeneration(message=msg)])


def chiamata(nome="orologio", args=None, id="c1") -> AIMessage:
    args = {"fuso_orario": "Asia/Tokyo"} if args is None else args
    return AIMessage(
        content="", tool_calls=[{"name": nome, "args": args, "id": id, "type": "tool_call"}]
    )


def grafo_con(risposte, orologio, max_passi=5, errore=None):
    finto = ModelloFinto(risposte=risposte, errore=errore)
    grafo = crea_grafo(finto, [orologio], max_passi, prompt_sistema("Europe/Rome"))
    return grafo, finto


def conta_coerenza(msgs):
    """(numero di tool_call richieste, numero di ToolMessage di risposta)."""
    richieste = sum(len(m.tool_calls) for m in msgs if isinstance(m, AIMessage))
    risposte = sum(1 for m in msgs if isinstance(m, ToolMessage))
    return richieste, risposte
