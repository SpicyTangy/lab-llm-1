import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from assistente.config import Config, ErroreConfigurazione
from assistente.modello import ErroreServer, crea_modello, modelli_serviti, verifica_modello

CONFIG = Config("http://localhost:1234/v1", "google/gemma-4-e2b", "Europe/Rome", 5, "INFO")


@pytest.fixture
def server_finto():
    """Server locale che risponde a GET /v1/models con stato e corpo scelti dal test."""
    risposta = {}

    class Gestore(BaseHTTPRequestHandler):
        def do_GET(self):
            corpo = risposta["corpo"]
            dati = (corpo if isinstance(corpo, str) else json.dumps(corpo)).encode()
            self.send_response(risposta["stato"] if self.path == "/v1/models" else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dati)))
            self.end_headers()
            self.wfile.write(dati)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Gestore)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def imposta(stato, corpo):
        risposta.update(stato=stato, corpo=corpo)
        return f"http://127.0.0.1:{server.server_address[1]}/v1"

    yield imposta
    server.shutdown()
    server.server_close()


def test_modelli_serviti_legge_gli_id(server_finto):
    url = server_finto(200, {"data": [{"id": "google/gemma-4-e2b"}, {"id": "emb"}]})
    assert modelli_serviti(url) == ["google/gemma-4-e2b", "emb"]


def test_server_irraggiungibile(porta_chiusa):
    with pytest.raises(ErroreServer, match=re.escape(porta_chiusa)):
        modelli_serviti(porta_chiusa, timeout=1)


@pytest.mark.parametrize("stato,corpo", [(500, {"errore": "x"}), (200, "non json")])
def test_risposta_non_valida(server_finto, stato, corpo):
    with pytest.raises(ErroreServer):
        modelli_serviti(server_finto(stato, corpo))


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
