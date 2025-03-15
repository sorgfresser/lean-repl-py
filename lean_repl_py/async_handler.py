import subprocess
import json
import warnings
from pathlib import Path
from typing import Optional, Dict, Union, Tuple
import asyncio
from lean_repl_py.handler import (
    LeanREPLEnvironment,
    LeanREPLProofState,
    LeanREPLNextProofState,
    LeanREPLMessage,
    REPL_MAX_OUTPUT_LINES,
)


class LeanREPLAsyncHandler:
    def __init__(self, project_path: Optional[Path] = None):
        """Initialize the asynchronous Lean REPL handler.

        :param project_path: An optional path for a Lean project directory, containing the desired Lean environment.
            If set, will run repl using `lake env repl` from the project directory.
        """
        # Path to the Lean REPL submodule
        self.lean_repl_path = Path(__file__).parent.parent / "repl"
        # Start the Lean REPL subprocess with pipes for stdin, stdout, and stderr
        if project_path is None:
            self.process_future = asyncio.create_subprocess_exec(
                "lake",
                "exe",
                "repl",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.lean_repl_path,
            )
        else:
            # Need to ensure repl is built - this is a bit hacky, as it might take a second to detect if already built
            subprocess.check_call(["lake", "build"], cwd=self.lean_repl_path)
            repl_bin_path = self.lean_repl_path / ".lake" / "build" / "bin" / "repl"
            self.process_future = asyncio.create_subprocess_exec(
                "lake",
                "env",
                str(repl_bin_path.resolve()),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_path,
            )
        self._env: Optional[LeanREPLEnvironment] = None
        self.process: Optional[asyncio.subprocess.Process] = None

    async def await_process(self) -> asyncio.subprocess.Process:
        if self.process is not None:
            return self.process
        self.process = await self.process_future
        return self.process

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

    async def send_command(self, command: str) -> None:
        return await self._send_json({"cmd": command})

    async def send_file(self, path: Path, all_tactics: bool = True) -> None:
        return await self._send_json(
            {"path": str(path.absolute()), "allTactics": all_tactics}
        )

    async def send_tactic(self, tactic: str, proof_state_idx: int) -> None:
        return await self._send_json({"tactic": tactic, "proofState": proof_state_idx})

    async def send_json_str(self, data: str) -> None:
        return await self._send_json(json.loads(data))

    async def _send_json(self, data: Dict[str, Union[str, int]]) -> None:
        """Send a JSON object to the Lean REPL."""
        if self.env is not None:
            data["env"] = self.env.env_index
        json_data = json.dumps(data, ensure_ascii=False)
        await self.await_process()
        self.process.stdin.write((json_data + "\n\n").encode())
        await self.process.stdin.drain()

    async def _readline_timeout(self, timeout: Optional[float] = None) -> str:
        try:
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Timeout while reading from Lean REPL.")
        return line.decode().strip()

    async def _get_output(self, timeout: Optional[float] = None) -> str:
        output = await self._readline_timeout(timeout)
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
            output += await self._readline_timeout(timeout)
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

    async def receive_json(
        self, timeout: Optional[float] = None
    ) -> Optional[
        Tuple[
            Union[Dict[str, Union[str, LeanREPLProofState]], LeanREPLNextProofState],
            Optional[LeanREPLEnvironment],
        ]
    ]:
        """Read a JSON object from the Lean REPL.

        :param timeout: The maximum time to wait for a response.
        :return: A tuple containing the JSON object and the environment.
        """
        output = await self._get_output(timeout)
        try:
            response = json.loads(output)
            # Env is not send in tactic mode
            if "env" in response:
                env = response["env"]
                del response["env"]
            else:
                env = None
            env = LeanREPLEnvironment(env_index=int(env)) if env is not None else None
            # If we have top level proof states, we can simply return this
            if self._is_next_proof_state(response):
                return LeanREPLNextProofState.model_validate(response), env
            # If we have sorries, we can return proof states
            if self._has_sorries(response):
                self._parse_sorries(response)
            if self._has_messages(response):
                self._parse_messages(response)
            return response, env
        except json.JSONDecodeError:
            return None

    async def pickle_env(
        self, pickle_to: Path, env: LeanREPLEnvironment
    ) -> Optional[Tuple[Dict[str, str], LeanREPLEnvironment]]:
        await self._send_json(
            {"pickleTo": str(pickle_to.absolute()), "env": env.env_index}
        )
        return await self.receive_json()

    async def pickle_proof_state(
        self, pickle_to: Path, proof_state_idx: int
    ) -> Optional[Dict[str, Union[str, int]]]:
        await self._send_json(
            {
                "pickleTo": str(pickle_to.absolute()),
                "proofState": proof_state_idx,
            }
        )
        return await self.receive_json()

    async def unpickle_env(self, env_from: Path) -> None:
        await self._send_json({"unpickleEnvFrom": str(env_from.absolute())})
        return await self.receive_json()

    async def unpickle_proof_state(self, proof_state_from: Path) -> None:
        await self._send_json(
            {"unpickleProofStateFrom": str(proof_state_from.absolute())}
        )
        return await self.receive_json()

    async def close(self):
        """Close the subprocess."""
        self.process.terminate()
        # Wait gracefully, kill if not done in 10 seconds
        try:
            await asyncio.wait_for(self.process.wait(), 10)
        except asyncio.TimeoutError:
            self.process.kill()
            await self.process.wait()

    def __del__(self):
        warnings.warn(
            "LeanREPLAsyncHandler should be closed explicitly with the close method.",
            ResourceWarning,
        )
