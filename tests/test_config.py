import pytest

from assistente.config import Config, ErroreConfigurazione, carica_config

BASE = {"LMSTUDIO_BASE_URL": "http://localhost:1234/v1/", "LMSTUDIO_MODEL": "google/gemma-4-e2b"}


def test_valori_predefiniti():
    c = carica_config(BASE)
    assert c == Config("http://localhost:1234/v1", "google/gemma-4-e2b", "Europe/Rome", 5, "INFO")


@pytest.mark.parametrize("nome", ["LMSTUDIO_BASE_URL", "LMSTUDIO_MODEL"])
@pytest.mark.parametrize("valore", [None, "", "   "])
def test_variabile_obbligatoria_mancante(nome, valore):
    env = dict(BASE)
    if valore is None:
        del env[nome]
    else:
        env[nome] = valore
    with pytest.raises(ErroreConfigurazione, match=nome):
        carica_config(env)


def test_fuso_non_valido():
    with pytest.raises(ErroreConfigurazione, match="FUSO_ORARIO_LOCALE"):
        carica_config(BASE | {"FUSO_ORARIO_LOCALE": "Marte/Base"})


@pytest.mark.parametrize("valore", ["0", "-1", "abc", "2.5"])
def test_max_passi_non_valido(valore):
    with pytest.raises(ErroreConfigurazione, match="MAX_PASSI"):
        carica_config(BASE | {"MAX_PASSI": valore})


def test_valori_personalizzati():
    c = carica_config(
        BASE | {"FUSO_ORARIO_LOCALE": "Asia/Tokyo", "MAX_PASSI": "3", "LOG_LEVEL": "debug"}
    )
    assert (c.fuso_locale, c.max_passi, c.log_level) == ("Asia/Tokyo", 3, "DEBUG")


def test_log_level_non_valido():
    with pytest.raises(ErroreConfigurazione, match="LOG_LEVEL"):
        carica_config(BASE | {"LOG_LEVEL": "boh"})


def test_errori_multipli_in_un_solo_messaggio():
    with pytest.raises(ErroreConfigurazione) as e:
        carica_config({"MAX_PASSI": "0"})
    assert all(n in str(e.value) for n in ("LMSTUDIO_BASE_URL", "LMSTUDIO_MODEL", "MAX_PASSI"))
