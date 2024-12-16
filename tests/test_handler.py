import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from lean_repl_py import LeanREPLHandler, LeanREPLEnvironment, LeanREPLProofState


@pytest.fixture
def handler():
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_process.stdin = MagicMock()
        mock_process.stdout.readline = MagicMock(return_value='{"env": 1}\n')
        yield LeanREPLHandler()


def test_send_command(handler):
    handler.send_command("def f := 2")
    handler.process.stdin.write.assert_called_with('{"cmd": "def f := 2"}\n\n')
    handler.process.stdin.flush.assert_called()


def test_send_file(handler):
    test_path = Path("../examples/test_file.lean")
    handler.send_file(test_path)
    handler.process.stdin.write.assert_called_with(
        f'{{"path": "{str(test_path.absolute())}", "allTactics": true}}\n\n'
    )
    handler.process.stdin.flush.assert_called()


def test_send_tactic(handler):
    proof_state = LeanREPLProofState(proof_state_index=1)
    handler.send_tactic("intro", proof_state)
    handler.process.stdin.write.assert_called_with(
        '{"tactic": "intro", "proofState": 1}\n\n'
    )
    handler.process.stdin.flush.assert_called()


def test_receive_json(handler):
    handler.process.stdout.readline = MagicMock(
        side_effect=['{"env": 1, "result": "foo"}\n']
    )
    response = handler.receive_json()
    assert response == ({"result": "foo"}, LeanREPLEnvironment(env_index=1))


def test_pickle_env(handler):
    test_path = Path("test_pickle_to.olean")
    env = LeanREPLEnvironment(env_index=2)
    handler.pickle_env(test_path, env)
    handler.process.stdin.write.assert_called_with(
        f'{{"pickleTo": "{str(test_path.absolute())}", "env": 2}}\n\n'
    )
    handler.process.stdin.flush.assert_called()


def test_unpickle_env(handler):
    test_path = Path("test_unpickle_from.olean")
    handler.unpickle_env(test_path)
    handler.process.stdin.write.assert_called_with(
        f'{{"unpickleEnvFrom": "{str(test_path.absolute())}"}}\n\n'
    )
    handler.process.stdin.flush.assert_called()


def test_close(handler):
    handler.close()
    handler.process.terminate.assert_called()
    handler.process.wait.assert_called()
