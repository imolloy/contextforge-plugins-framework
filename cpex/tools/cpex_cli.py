# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/cpex_cli.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Claude Code

CPEX CLI ─ command line interface for hook invocation and introspection
This module is exposed as a **console-script** via:

    [project.scripts]
    cpex = "cpex.tools.cpex_cli:main"

so that a user can simply type `cpex ...` to use the CLI.

Features
─────────
* invoke: Invoke hooks programmatically with JSON payloads
* hooks list: List all registered hook types
* hooks describe: Show schema for a specific hook type

Typical usage
─────────────
```console
# Direct payload
$ cpex invoke --hook tool_pre_invoke --payload '{"name": "search", "args": {"query": "test"}}'

# From file
$ cpex invoke --hook tool_pre_invoke --payload ./payload.json

# From stdin (pipe)
$ echo '{"name": "search", "args": {"query": "test"}}' | cpex invoke --hook tool_pre_invoke

# Hook introspection
$ cpex hooks list
$ cpex hooks describe tool_pre_invoke
```
"""

# Standard
import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import os
from datetime import datetime

# Third-Party
import typer
from typing_extensions import Annotated

# First-Party
from cpex.framework.settings import settings
from cpex.tools.hook_invoker import HookInvoker
from cpex.tools.output import format_output, ExitCode

# Import to register schema mappers
try:
    from cpex.tools.schemas import claude_code  # noqa: F401
except ImportError:
    logger.warning("Could not import claude_code schema mapper")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CLI Configuration
# ---------------------------------------------------------------------------

markup_mode = settings.cli_markup_mode or typer.core.DEFAULT_MARKUP_MODE
app = typer.Typer(
    help="CPEX CLI - Command line interface for hook invocation and introspection.",
    add_completion=settings.cli_completion,
    rich_markup_mode=None if markup_mode == "disabled" else markup_mode,
)

# Sub-application for hooks commands
hooks_app = typer.Typer(help="Hook introspection commands.")
app.add_typer(hooks_app, name="hooks")


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def load_json_payload(payload_input: str) -> dict:
    """Load JSON payload from string or file path.

    Args:
        payload_input: Either a JSON string or path to a JSON file

    Returns:
        Parsed JSON as dictionary

    Raises:
        typer.Exit: If payload cannot be parsed or file cannot be read
    """
    # Try to parse as JSON string first
    try:
        return json.loads(payload_input)
    except json.JSONDecodeError:
        pass

    # Try to load as file path
    try:
        payload_path = Path(payload_input)
        if payload_path.exists():
            with open(payload_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read payload file {payload_input}: {e}")
        raise typer.Exit(ExitCode.CONFIGURATION_ERROR.value)

    # If neither worked, it's an invalid payload
    logger.error(f"Invalid payload: not valid JSON and not a readable file path: {payload_input}")
    raise typer.Exit(ExitCode.CONFIGURATION_ERROR.value)


def configure_logging(log_level: str = "info", log_file: Optional[str] = None) -> None:
    """Configure logging with file output and specified level.

    Args:
        log_level: Logging level (debug, info, warning, error)
        log_file: Optional path to log file. If None, uses default location.
    """
    # Convert string level to logging level
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR
    }
    level = level_map.get(log_level.lower(), logging.INFO)

    # Create logs directory if needed
    if log_file is None:
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"cpex_debug_{timestamp}.log"
    else:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure root logger
    root_logger.setLevel(level)

    # Create file handler
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Create console handler for errors only (unless debug level)
    console_handler = logging.StreamHandler(sys.stderr)
    if level == logging.DEBUG:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Log configuration info
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Working directory: {Path.cwd()}")
    logger.debug(f"Environment variables: {dict(os.environ)}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command(help="Invoke a hook with the provided JSON payload.")
def invoke(
    hook: Annotated[str, typer.Option("--hook", "-h", help="The hook type to invoke (e.g., 'tool_pre_invoke')")],
    payload: Annotated[Optional[str], typer.Option("--payload", "-p", help="JSON payload string or path to JSON file (reads from stdin if not provided)")] = None,
    context: Annotated[Optional[str], typer.Option("--context", "-c", help="Global context JSON string or file path")] = None,
    config: Annotated[Optional[Path], typer.Option("--config", "-f", help="Plugin configuration file path")] = None,
    schema: Annotated[Optional[str], typer.Option("--schema", "-s", help="Schema mapper for external tool integration (e.g., 'claude-code')")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose logging (deprecated: use --log-level debug)")] = False,
    log_level: Annotated[str, typer.Option("--log-level", "-l", help="Logging level: debug, info, warning, error")] = "info",
    log_file: Annotated[Optional[str], typer.Option("--log-file", help="Path to log file (default: logs/cpex_debug_<timestamp>.log)")] = None,
) -> None:
    """Invoke a hook with the provided JSON payload.

    The payload can be provided in three ways:
    1. As a JSON string: --payload '{"name": "test", "args": {}}'
    2. As a file path: --payload ./payload.json
    3. From stdin: echo '{"name": "test", "args": {}}' | cpex invoke --hook tool_pre_invoke

    Args:
        hook: The hook type to invoke
        payload: JSON payload string or path to JSON file (reads from stdin if not provided)
        context: Optional global context JSON string or file path
        config: Optional plugin configuration file path
        schema: Optional schema mapper for external tool integration
        verbose: Enable verbose logging (deprecated: use --log-level debug)
        log_level: Logging level (debug, info, warning, error)
        log_file: Optional path to log file (default: logs/cpex_debug_<timestamp>.log)
    """
    # Configure logging - handle deprecated verbose flag
    actual_log_level = log_level
    if verbose and log_level == "info":
        actual_log_level = "debug"

    configure_logging(log_level=actual_log_level, log_file=log_file)
    logger.info(f"Starting hook invocation - Hook: {hook}, Schema: {schema}")
    logger.debug(f"Command line arguments: hook={hook}, payload={payload}, context={context}, "
                f"config={config}, schema={schema}, log_level={actual_log_level}, log_file={log_file}")

    try:
        # Parse payload - read from stdin if not provided
        if payload is None:
            # Read from stdin
            if sys.stdin.isatty():
                logger.error("No payload provided and no data piped to stdin. Please provide --payload or pipe JSON data.")
                raise typer.Exit(ExitCode.CONFIGURATION_ERROR.value)

            stdin_data = sys.stdin.read().strip()
            if not stdin_data:
                logger.error("No payload provided and stdin is empty. Please provide --payload or pipe JSON data.")
                raise typer.Exit(ExitCode.CONFIGURATION_ERROR.value)

            logger.debug(f"Reading payload from stdin: {stdin_data[:100]}...")
            payload_data = load_json_payload(stdin_data)
        else:
            payload_data = load_json_payload(payload)

        logger.debug(f"Loaded payload: {payload_data}")

        # Parse context if provided
        context_data = None
        if context:
            context_data = load_json_payload(context)
            logger.debug(f"Loaded context: {context_data}")
        # print(f"Invoking hook '{hook}' with payload: {payload_data} and context: {context_data} and schema: {schema}")
        # Create hook invoker and execute
        invoker = HookInvoker(config_path=config)
        result = invoker.invoke_hook_sync(
            hook_type=hook,
            payload=payload_data,
            global_context=context_data,
            schema_mapper=schema
        )

        # Output result and exit with appropriate code
        output = format_output(result)
        print(output)

        # Only raise typer.Exit for non-success codes
        if result.exit_code != ExitCode.SUCCESS:
            raise typer.Exit(result.exit_code.value)

    except Exception as e:
        logger.error(f"Hook invocation failed: {e}")
        if actual_log_level == "debug":
            logger.exception("Full traceback:")
        raise typer.Exit(ExitCode.EXECUTION_ERROR.value)


@hooks_app.command("list", help="List all registered hook types.")
def list_hooks(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Include detailed information")] = False,
) -> None:
    """List all registered hook types.

    Args:
        verbose: Include detailed information
    """
    try:
        invoker = HookInvoker()
        hooks = invoker.list_hooks()

        if verbose:
            output = {
                "hooks": hooks,
                "count": len(hooks)
            }
            print(json.dumps(output, indent=2))
        else:
            for hook in hooks:
                print(hook)

    except Exception as e:
        logger.error(f"Failed to list hooks: {e}")
        raise typer.Exit(ExitCode.EXECUTION_ERROR.value)


@hooks_app.command("describe", help="Show schema information for a specific hook type.")
def describe_hook(
    hook_type: Annotated[str, typer.Argument(help="The hook type to describe")],
) -> None:
    """Show schema information for a specific hook type.

    Args:
        hook_type: The hook type to describe
    """
    try:
        invoker = HookInvoker()
        description = invoker.describe_hook(hook_type)
        print(json.dumps(description, indent=2))

    except Exception as e:
        logger.error(f"Failed to describe hook {hook_type}: {e}")
        raise typer.Exit(ExitCode.EXECUTION_ERROR.value)


@app.callback()
def callback() -> None:  # pragma: no cover
    """This function exists to force subcommands."""


def main() -> None:  # noqa: D401 - imperative mood is fine here
    """Entry point for the *cpex* console script.

    Environment Variables:
        PLUGINS_CLI_COMPLETION: Enable auto-completion for CLI (default: false)
        PLUGINS_CLI_MARKUP_MODE: Set markup mode for CLI (default: rich)
            Valid options:
                rich: use rich markup
                markdown: allow markdown in help strings
                disabled: disable markup
    """
    app()


if __name__ == "__main__":  # pragma: no cover - executed only when run directly
    main()