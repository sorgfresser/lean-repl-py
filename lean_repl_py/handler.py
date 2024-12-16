import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Union, Tuple

# Max lines a single repl output is expected to be, will raise if longer than this
REPL_MAX_OUTPUT_LINES = 10000


@dataclass
class LeanREPLEnvironment:
    env_index: int


@dataclass
class LeanREPLProofState:
    proof_state_index: int


class LeanREPLHandler:
    def __init__(self):
        # Path to the Lean REPL executable
        self.lean_repl_path = Path(__file__).parent.parent / "repl"

        # Start the Lean REPL subprocess with pipes for stdin, stdout, and stderr
        self.process = subprocess.Popen(
            ["lake", "exe", "repl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # Handle input/output as text (string)
            bufsize=1,
            cwd=self.lean_repl_path,
        )
        self._env = None

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, environment: LeanREPLEnvironment):
        self._env = environment

    def send_command(self, command: str) -> None:
        return self._send_json({"cmd": command})

    def send_file(self, path: Path, all_tactics: bool = True) -> None:
        return self._send_json(
            {"path": str(path.absolute()), "allTactics": all_tactics}
        )

    def send_tactic(self, tactic: str, proof_state: LeanREPLProofState) -> None:
        return self._send_json(
            {"tactic": tactic, "proofState": proof_state.proof_state_index}
        )

    def send_json_str(self, data: str) -> None:
        return self._send_json(json.loads(data))

    def _send_json(self, data: Dict[str, Union[str, int]]) -> None:
        """Send a JSON object to the Lean REPL."""
        if self.env is not None:
            data["env"] = self.env
        json_data = json.dumps(data)
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

    def receive_json(self) -> Optional[Tuple[Dict[str, str], LeanREPLEnvironment]]:
        """Read a JSON object from the Lean REPL."""
        output = self._get_output()
        try:
            response = json.loads(output)
            env = response["env"]
            del response["env"]
            return response, LeanREPLEnvironment(env_index=int(env))
        except json.JSONDecodeError:
            return None

    def pickle_env(
        self, pickle_to: Path, env: LeanREPLEnvironment
    ) -> Optional[Tuple[Dict[str, str], LeanREPLEnvironment]]:
        self._send_json({"pickleTo": str(pickle_to.absolute()), "env": env.env_index})
        return self.receive_json()

    def pickle_proof_state(
        self, pickle_to: Path, proof_state: LeanREPLProofState
    ) -> Optional[Dict[str, Union[str, int]]]:
        self._send_json(
            {
                "pickleTo": str(pickle_to.absolute()),
                "proofState": proof_state.proof_state_index,
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


def main():
    handler = LeanREPLHandler()

    try:
        # Example of sending and receiving JSON continuously
        while True:
            # Prepare the JSON input
            user_input = input("Enter a Lean repl line (or 'quit' to exit): ")
            if user_input.strip().lower() == "quit":
                break
            elif user_input.strip().lower() == "unpickleenv":
                user_input = input("Enter a filepath to unpickle from")
                handler.unpickle_env(Path(user_input))
            elif user_input.strip().lower() == "unpickleproofstate":
                user_input = input("Enter a filepath to unpickle from")
                handler.unpickle_proof_state(Path(user_input))
            elif user_input.strip().lower() == "pickleenv":
                user_input = input("Enter a filepath to pickle to: ")
                user_input_2 = input("Enter an environment index to pickle: ")
                print(
                    handler.pickle_env(
                        Path(user_input), LeanREPLEnvironment(int(user_input_2))
                    )
                )
            elif user_input.strip().lower() == "pickleproofstate":
                user_input = input("Enter a filepath to pickle to: ")
                user_input_2 = input("Enter a proof state index to pickle: ")
                print(
                    handler.pickle_proof_state(
                        Path(user_input), LeanREPLProofState(int(user_input_2))
                    )
                )
            else:
                # Send the JSON command
                command = user_input
                handler.send_json_str(command)

                # Receive and print the response
                response = handler.receive_json()
                if response:
                    print("Response:", response)
                else:
                    print("Invalid JSON response from Lean REPL.")

    finally:
        handler.close()
        print("Lean REPL subprocess closed.")


if __name__ == "__main__":
    main()
