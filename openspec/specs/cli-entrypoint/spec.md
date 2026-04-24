## Purpose

Specification for the unified CLI entry point at `src/main.py` that exposes all pipeline flows as subcommands under a single `uv run python -m main` invocation.

## Requirements

### Requirement: Unified CLI entry point at src/main.py
The project SHALL provide a single CLI entry point at `src/main.py` invocable as `uv run python -m main`. It SHALL use argparse subparsers with one subcommand per flow. Running without a subcommand SHALL print help and exit with a non-zero code.

#### Scenario: No subcommand given
- **WHEN** `uv run python -m main` is run without arguments
- **THEN** the help text listing all available subcommands is printed and the process exits non-zero

#### Scenario: Unknown subcommand given
- **WHEN** `uv run python -m main foobar` is run
- **THEN** argparse prints an error and exits non-zero

### Requirement: One subcommand per flow with flow-specific flags
The CLI SHALL expose subcommands `scout`, `enrich`, `evaluate`, `report`, and `sync`. Each subcommand SHALL accept the same flags as its flow's existing `argparse` parser. Flags SHALL be nested under the subcommand and SHALL NOT be mixed across subcommands.

#### Scenario: enrich subcommand with flags
- **WHEN** `uv run python -m main enrich --limit 10 --concurrency 3` is run
- **THEN** the enrich flow is invoked with `limit=10` and `concurrency=3`

#### Scenario: scout subcommand with no extra flags
- **WHEN** `uv run python -m main scout` is run
- **THEN** the scout flow is invoked with its default arguments

#### Scenario: evaluate subcommand with limit
- **WHEN** `uv run python -m main evaluate --limit 5` is run
- **THEN** the evaluate flow is invoked with `limit=5`

### Requirement: sync subcommand runs all flows in sequence
The `sync` subcommand SHALL run scout → enrich → evaluate → report in order. It SHALL stop and report the error if any step fails. It SHALL NOT accept flow-specific flags (it uses defaults for each flow).

#### Scenario: Full sync succeeds
- **WHEN** `uv run python -m main sync` is run and all flows complete without error
- **THEN** all four flows execute in order and the process exits zero

#### Scenario: Sync stops on flow failure
- **WHEN** a flow raises an unhandled exception during sync
- **THEN** the error is logged, subsequent flows are skipped, and the process exits non-zero

### Requirement: Flow main.py entry functions remain directly callable
Each flow's `main.py` SHALL retain a `main()` or async entry function and its own `if __name__ == "__main__"` block. The unified CLI SHALL call these functions directly rather than spawning subprocesses. Individual flow modules SHALL remain independently executable via `uv run python -m flows.<flow>.main`.

#### Scenario: Direct flow invocation still works
- **WHEN** `uv run python -m flows.scout.main` is run
- **THEN** the scout flow executes identically to `uv run python -m main scout`

### Requirement: serve subcommand starts the API server
The CLI SHALL expose a `serve` subcommand that starts the FastAPI application via uvicorn. It SHALL accept `--host` (default `0.0.0.0`) and `--port` (default `8000`) flags. It SHALL block until the server is stopped.

#### Scenario: Default serve
- **WHEN** `python -m src serve` is run
- **THEN** uvicorn starts the FastAPI app on `0.0.0.0:8000` and the process blocks

#### Scenario: Custom host and port
- **WHEN** `python -m src serve --host 127.0.0.1 --port 9000` is run
- **THEN** uvicorn starts the FastAPI app on `127.0.0.1:9000`
