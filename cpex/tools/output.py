# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/output.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Claude Code

Output Utilities ─ JSON output formatting and exit code management
This module provides standardized output formatting and exit code handling
for the CPEX CLI interface.

Features
─────────
* Standardized exit codes for CLI operations
* JSON output formatting utilities
* Result container classes

Classes
───────
* ExitCode: Standard exit codes for CLI operations
* InvocationResult: Result container for hook invocations
"""

# Standard
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ExitCode(Enum):
    """Standard exit codes for CPEX CLI operations.

    These exit codes follow Unix conventions and provide meaningful
    feedback to external tools about the outcome of hook invocations.

    Attributes:
        SUCCESS: Hook execution successful, continue processing
        EXECUTION_ERROR: Hook execution failed due to error
        BLOCKED_BY_VIOLATION: Hook execution successful, but processing should be blocked
        CONFIGURATION_ERROR: Configuration, validation, or CLI usage error
    """

    SUCCESS = 0
    EXECUTION_ERROR = 1
    BLOCKED_BY_VIOLATION = 2
    CONFIGURATION_ERROR = 3


@dataclass
class InvocationResult:
    """Result container for hook invocations.

    Attributes:
        success: Whether the invocation was successful
        data: Result data (for successful invocations)
        error: Error message (for failed invocations)
        exit_code: Appropriate exit code
        hook_type: The hook type that was invoked
        metadata: Optional additional metadata
    """

    success: bool
    exit_code: ExitCode
    hook_type: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format.

        Returns:
            Dictionary representation of the result
        """
        result = {
            "success": self.success,
            "exit_code": self.exit_code.value,
            "hook_type": self.hook_type,
        }

        if self.data is not None:
            result["data"] = self.data

        if self.error is not None:
            result["error"] = self.error

        if self.metadata is not None:
            result["metadata"] = self.metadata

        return result


def format_output(result: InvocationResult, pretty: bool = True) -> str:
    """Format invocation result as JSON string.

    Args:
        result: The invocation result to format
        pretty: Whether to pretty-print the JSON

    Returns:
        JSON-formatted string representation of the result
    """
    data = result.to_dict()

    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False)
    else:
        return json.dumps(data, ensure_ascii=False)


def format_error(
    message: str,
    exit_code: ExitCode = ExitCode.EXECUTION_ERROR,
    hook_type: Optional[str] = None,
    pretty: bool = True
) -> str:
    """Format an error message as JSON string.

    Args:
        message: Error message
        exit_code: Appropriate exit code
        hook_type: Optional hook type associated with the error
        pretty: Whether to pretty-print the JSON

    Returns:
        JSON-formatted error string
    """
    result = InvocationResult(
        success=False,
        error=message,
        exit_code=exit_code,
        hook_type=hook_type or "unknown"
    )
    return format_output(result, pretty)


def format_success(
    data: Dict[str, Any],
    hook_type: str,
    exit_code: ExitCode = ExitCode.SUCCESS,
    metadata: Optional[Dict[str, Any]] = None,
    pretty: bool = True
) -> str:
    """Format a success result as JSON string.

    Args:
        data: Success data
        hook_type: Hook type that was invoked
        exit_code: Exit code (defaults to SUCCESS)
        metadata: Optional metadata
        pretty: Whether to pretty-print the JSON

    Returns:
        JSON-formatted success string
    """
    result = InvocationResult(
        success=True,
        data=data,
        exit_code=exit_code,
        hook_type=hook_type,
        metadata=metadata
    )
    return format_output(result, pretty)