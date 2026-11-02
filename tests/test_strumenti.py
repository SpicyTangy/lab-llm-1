import json
from datetime import datetime, timezone

import pytest

from assistente.strumenti import crea_orologio, ora_in_fuso

ISTANTE_INVERNO = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
ISTANTE_ESTATE = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)


def leggi(fuso, istante):
    return json.loads(ora_in_fuso(fuso, adesso=lambda: istante))


def test_ora_roma_inverno():
    r = leggi("Europe/Rome", ISTANTE_INVERNO)
    assert r == {
        "fuso_orario": "Europe/Rome",
        "data_ora": "2026-10-26T13:00:00+01:00",
        "giorno": "lunedì",
        "abbreviazione": "CET",
    }


def test_ora_roma_estate():
    r = leggi("Europe/Rome", ISTANTE_ESTATE)
    assert (r["data_ora"], r["giorno"], r["abbreviazione"]) == (
        "2026-07-01T12:00:00+02:00",
        "mercoledì",
        "CEST",
    )


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
