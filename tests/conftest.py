import pytest
from pathlib import Path
from lean_repl_py import LeanREPLHandler, LeanREPLAsyncHandler


@pytest.fixture
def handler():
    yield LeanREPLHandler(Path(__file__).parent.parent / "repl")


@pytest.fixture
def async_handler():
    yield LeanREPLAsyncHandler(Path(__file__).parent.parent / "repl")
