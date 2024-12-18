from lean_repl_py.handler import LeanREPLHandler, LeanREPLEnvironment
from pathlib import Path


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
                user_input = input("Enter a filepath to unpickle from: ")
                print(handler.unpickle_env(Path(user_input)))
            elif user_input.strip().lower() == "unpickleproofstate":
                user_input = input("Enter a filepath to unpickle from: ")
                print(handler.unpickle_proof_state(Path(user_input)))
            elif user_input.strip().lower() == "pickleenv":
                user_input = input("Enter a filepath to pickle to: ")
                user_input_2 = input("Enter an environment index to pickle: ")
                print(
                    handler.pickle_env(
                        Path(user_input),
                        LeanREPLEnvironment(env_index=int(user_input_2)),
                    )
                )
            elif user_input.strip().lower() == "pickleproofstate":
                user_input = input("Enter a filepath to pickle to: ")
                user_input_2 = input("Enter a proof state index to pickle: ")
                print(handler.pickle_proof_state(Path(user_input), int(user_input_2)))
            elif user_input.strip().lower() == "tactic":
                user_input = input("Enter a tactic: ")
                user_input_2 = input("Enter a proof state index: ")
                handler.send_tactic(user_input, int(user_input_2))
                print(handler.receive_json())
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
