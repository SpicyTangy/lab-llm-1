import socket

import pytest


@pytest.fixture
def porta_chiusa():
    """URL di un server che non risponde: una porta appena liberata."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    return f"http://127.0.0.1:{porta}/v1"
