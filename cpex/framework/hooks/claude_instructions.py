# -*- coding: utf-8 -*-
"""Location: ./cpex/framework/hooks/claude_instructions.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0

Pydantic models for Claude Code instruction loading hooks.
"""

# Standard
from enum import Enum
from typing import Literal, Optional

# Third-Party
from pydantic import Field

# First-Party
from cpex.framework.models import PluginPayload, PluginResult


class ClaudeInstructionHookType(str, Enum):
    """Claude Code instruction hook points.

    Attributes:
        INSTRUCTIONS_LOADED: When Claude Code instructions (.claude files, etc.) are loaded.

    Examples:
        >>> ClaudeInstructionHookType.INSTRUCTIONS_LOADED
        <ClaudeInstructionHookType.INSTRUCTIONS_LOADED: 'claude_instructions_loaded'>
        >>> ClaudeInstructionHookType.INSTRUCTIONS_LOADED.value
        'claude_instructions_loaded'
    """

    INSTRUCTIONS_LOADED = "claude_instructions_loaded"


class InstructionsLoadedPayload(PluginPayload):
    """Payload for Claude Code instructions loaded hook.

    This hook fires when Claude Code loads instruction files like .claude files,
    memory files, or other configuration files.

    Attributes:
        file_path: Path to the loaded instructions file.
        memory_type: Scope of the file loaded (User, Project, Local, Managed).
        load_reason: Why the file was loaded.
        globs: Glob patterns used for file paths.
        trigger_file_path: Path to the file whose access triggered this load.
        parent_file_path: Path to the parent file.

    Examples:
        >>> payload = InstructionsLoadedPayload(
        ...     file_path="/workspace/.claude/instructions.md",
        ...     memory_type="Project",
        ...     load_reason="session_start"
        ... )
        >>> payload.file_path
        '/workspace/.claude/instructions.md'
        >>> payload.memory_type
        'Project'
    """

    file_path: str = Field(description="Path to the loaded instructions file")
    memory_type: Literal["User", "Project", "Local", "Managed"] = Field(
        description="Scope of the file loaded"
    )
    load_reason: Literal["session_start", "nested_traversal", "path_glob_match", "include", "compact"] = Field(
        description="Why the file loaded"
    )
    globs: str = Field(default="", description="Glob patterns used for file paths")
    trigger_file_path: str = Field(default="", description="Path to the file whose access triggered this load")
    parent_file_path: str = Field(default="", description="Path to the parent file")


InstructionsLoadedResult = PluginResult[InstructionsLoadedPayload]


def _register_claude_instruction_hooks() -> None:
    """Register Claude instruction hooks in the global registry.

    This is called lazily to avoid circular import issues.
    """
    # Import here to avoid circular dependency at module load time
    # First-Party
    from cpex.framework.hooks.registry import get_hook_registry  # pylint: disable=import-outside-toplevel

    registry = get_hook_registry()

    # Only register if not already registered (idempotent)
    if not registry.is_registered(ClaudeInstructionHookType.INSTRUCTIONS_LOADED):
        registry.register_hook(
            ClaudeInstructionHookType.INSTRUCTIONS_LOADED,
            InstructionsLoadedPayload,
            InstructionsLoadedResult
        )


_register_claude_instruction_hooks()