import pytest
from pathlib import Path
from lean_repl_py import LeanREPLHandler


@pytest.fixture
def handler():
    yield LeanREPLHandler(Path(__file__).parent.parent / "repl")
