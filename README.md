# lean-repl-py

**lean-repl-py** is a Python application designed to interact with the Lean REPL (Read-Eval-Print Loop). It provides an interface for sending commands to Lean and processing responses, making it easier to automate theorem proving using Python.

## Features

- **Simple Interface**: Send Lean commands and receive responses seamlessly.
- **Automation**: Useful for scripting Lean interactions programmatically.
- **No Dependencies**: A lightweight tool with zero external dependencies.
- **Fast**: Adds no noticeable overhead on top of the lean REPL.

## Installation

You can install `lean-repl-py` via [PyPI](https://pypi.org/):

```bash
pip install lean-repl-py
```

## Prerequisites
Requires `lake` to be available on your system. That's it, no more strings attached.

Importantly, lean-repl-py ships with the correct version of the lean repl, so it is not needed separately.

## Important notices

The first start in a new python environment will take some time, as the repl must be built first.
