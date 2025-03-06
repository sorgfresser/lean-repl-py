import subprocess
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union, Tuple, Literal

# Max lines a single repl output is expected to be, will raise if longer than this
REPL_MAX_OUTPUT_LINES = 10000


class LeanREPLPos(BaseModel):
    line: int
    column: int


class LeanREPLEnvironment(BaseModel):
    env_index: int


class LeanREPLProofState(BaseModel):
    proof_state: int = Field(alias="proofState")
    goal: str
    pos: LeanREPLPos
    end_pos: LeanREPLPos = Field(alias="endPos")


class LeanREPLNextProofState(BaseModel):
    proof_state: int = Field(alias="proofState")
    goals: list[str]


class LeanREPLMessage(BaseModel):
    data: str
    pos: LeanREPLPos
    end_pos: Optional[LeanREPLPos] = Field(alias="endPos")
    severity: Literal["error", "warning", "info"]


class LeanREPLHandler:
    def __init__(self, project_path: Optional[Path] = None):
        """Initialize the Lean REPL handler.

        :param project_path: An optional path for a Lean project directory, containing the desired Lean environment.
            If set, will run repl using `lake env repl` from the project directory.
        """
        # Path to the Lean REPL submodule
        self.lean_repl_path = Path(__file__).parent.parent / "repl"
        # Start the Lean REPL subprocess with pipes for stdin, stdout, and stderr
        if project_path is None:
            self.process = subprocess.Popen(
                ["lake", "exe", "repl"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Handle input/output as text (string)
                bufsize=1,
                cwd=self.lean_repl_path,
            )
        else:
            # Need to ensure repl is built - this is a bit hacky, as it might take a second to detect if already built
            subprocess.check_call(["lake", "build"], cwd=self.lean_repl_path)
            repl_bin_path = self.lean_repl_path / ".lake" / "build" / "bin" / "repl"
            self.process = subprocess.Popen(
                ["lake", "env", str(repl_bin_path.absolute())],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Handle input/output as text (string)
                bufsize=1,
                cwd=project_path,
            )
        self._env: Optional[LeanREPLEnvironment] = None

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, environment: Union[LeanREPLEnvironment, int, None]):
        if isinstance(environment, LeanREPLEnvironment) or environment is None:
            self._env = environment
        elif isinstance(environment, int):
            self._env = LeanREPLEnvironment(env_index=environment)
        else:
            raise ValueError("Environment must be a LeanREPLEnvironment object.")

    def send_command(self, command: str) -> None:
        return self._send_json({"cmd": command})

    def send_file(self, path: Path, all_tactics: bool = True) -> None:
        return self._send_json(
            {"path": str(path.absolute()), "allTactics": all_tactics}
        )

    def send_tactic(self, tactic: str, proof_state_idx: int) -> None:
        return self._send_json({"tactic": tactic, "proofState": proof_state_idx})

    def send_json_str(self, data: str) -> None:
        return self._send_json(json.loads(data))

    def _send_json(self, data: Dict[str, Union[str, int]]) -> None:
        """Send a JSON object to the Lean REPL."""
        if self.env is not None:
            data["env"] = self.env.env_index
        json_data = json.dumps(data, ensure_ascii=False)
        self.process.stdin.write(json_data + "\n\n")
        self.process.stdin.flush()

    def _get_output(self) -> str:
        output = self.process.stdout.readline().strip()
        # Since we know repl only returns valid json, we can use this while here
        # We might want to have some way to ensure we do not get stuck
        i = 0
        while True:
            if i >= REPL_MAX_OUTPUT_LINES:
                raise RuntimeError(f"Read more than {REPL_MAX_OUTPUT_LINES} lines!")
            # If we have a valid json, we can stop reading
            try:
                json.loads(output)
                break
            except json.JSONDecodeError:
                pass
            output += self.process.stdout.readline().strip()
            i += 1
        return output

    def _has_sorries(self, response: Dict[str, str]):
        return "sorries" in response

    def _parse_sorries(self, response: Dict[str, str]) -> None:
        for idx, sorry in enumerate(response["sorries"]):
            response["sorries"][idx] = LeanREPLProofState.model_validate(sorry)

    def _is_next_proof_state(self, response: Dict[str, str]):
        return "proofState" in response  # if response has top level proofState

    def _has_messages(self, response: Dict[str, str]):
        return "messages" in response

    def _parse_messages(self, response: Dict[str, str]) -> None:
        for idx, message in enumerate(response["messages"]):
            response["messages"][idx] = LeanREPLMessage.model_validate(message)

    def receive_json(
        self,
    ) -> Optional[
        Tuple[
            Union[Dict[str, Union[str, LeanREPLProofState]], LeanREPLNextProofState],
            Optional[LeanREPLEnvironment],
        ]
    ]:
        """Read a JSON object from the Lean REPL."""
        output = self._get_output()
        try:
            response = json.loads(output)
            # Env is not send in tactic mode
            if "env" in response:
                env = response["env"]
                del response["env"]
            else:
                env = None
            # If we have sorries, we can return proof states
            if self._has_sorries(response):
                self._parse_sorries(response)
            if self._has_messages(response):
                self._parse_messages(response)
            if self._is_next_proof_state(response):
                response = LeanREPLNextProofState.model_validate(response)
            if env is not None:
                return response, LeanREPLEnvironment(env_index=int(env))
            return response, None
        except json.JSONDecodeError:
            return None

    def pickle_env(
        self, pickle_to: Path, env: LeanREPLEnvironment
    ) -> Optional[Tuple[Dict[str, str], LeanREPLEnvironment]]:
        self._send_json({"pickleTo": str(pickle_to.absolute()), "env": env.env_index})
        return self.receive_json()

    def pickle_proof_state(
        self, pickle_to: Path, proof_state_idx: int
    ) -> Optional[Dict[str, Union[str, int]]]:
        self._send_json(
            {
                "pickleTo": str(pickle_to.absolute()),
                "proofState": proof_state_idx,
            }
        )
        return self.receive_json()

    def unpickle_env(self, env_from: Path) -> None:
        self._send_json({"unpickleEnvFrom": str(env_from.absolute())})
        return self.receive_json()

    def unpickle_proof_state(self, proof_state_from: Path) -> None:
        self._send_json({"unpickleProofStateFrom": str(proof_state_from.absolute())})
        return self.receive_json()

    def close(self):
        """Close the subprocess."""
        self.process.terminate()
        self.process.wait()

    def __del__(self):
        self.close()
