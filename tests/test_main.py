from assistente.__main__ import main


def test_config_mancante_esce_con_2(capsys):
    assert main({}) == 2
    assert "LMSTUDIO_BASE_URL" in capsys.readouterr().err


def test_server_spento_esce_con_1(capsys, porta_chiusa):
    assert main({"LMSTUDIO_BASE_URL": porta_chiusa, "LMSTUDIO_MODEL": "m"}) == 1
    assert porta_chiusa in capsys.readouterr().err
