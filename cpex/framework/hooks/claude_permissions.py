# -*- coding: utf-8 -*-
"""Location: ./cpex/framework/hooks/claude_permissions.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0

Pydantic models for Claude Code permission system hooks.
"""

# Standard
from enum import Enum
from typing import Any, Dict, Literal, Optional

# Third-Party
from pydantic import Field

# First-Party
from cpex.framework.models import PluginPayload, PluginResult


class ClaudePermissionHookType(str, Enum):
    """Claude Code permission hook points.

    Attributes:
        PERMISSION_REQUEST: When Claude Code requests permission for a tool.
        PERMISSION_UPDATE: When a permission decision is made.

    Examples:
        >>> ClaudePermissionHookType.PERMISSION_REQUEST
        <ClaudePermissionHookType.PERMISSION_REQUEST: 'claude_permission_request'>
        >>> ClaudePermissionHookType.PERMISSION_UPDATE.value
        'claude_permission_update'
    """

    PERMISSION_REQUEST = "claude_permission_request"
    PERMISSION_UPDATE = "claude_permission_update"


class PermissionRequestPayload(PluginPayload):
    """Payload for Claude Code permission request hook.

    This hook fires when Claude Code is asking for permission to use a tool.

    Attributes:
        tool_name: Name of the tool for which permission is being requested.
        tool_input: Arguments for the tool invocation.
        permission_suggestions: Suggested permission decisions based on input.
        session_id: Unique session identifier.
        cwd: Current working directory.
        permission_mode: Current permission mode.

    Examples:
        >>> payload = PermissionRequestPayload(
        ...     tool_name="file_read",
        ...     tool_input={"path": "/etc/passwd"},
        ...     session_id="session-123",
        ...     cwd="/workspace"
        ... )
        >>> payload.tool_name
        'file_read'
        >>> payload.tool_input["path"]
        '/etc/passwd'
    """

    tool_name: str = Field(description="Name of the tool for which permission is being requested")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool invocation")
    permission_suggestions: Optional[Dict[str, Any]] = Field(
        default=None, description="Suggested permission decisions based on input"
    )
    session_id: str = Field(description="Unique session identifier")
    cwd: str = Field(description="Current working directory")
    permission_mode: Literal["default", "plan", "acceptEdits", "dontAsk", "bypassPermissions"] = Field(
        description="Current permission mode"
    )


class PermissionUpdatePayload(PluginPayload):
    """Payload for Claude Code permission update hook.

    This hook fires when a permission decision has been made.

    Attributes:
        tool_name: Name of the tool for which permission decision was made.
        tool_input: Arguments for the tool invocation.
        permission_decision: The permission decision that was made.
        permission_decision_reason: Reason for the permission decision.
        session_id: Unique session identifier.
        cwd: Current working directory.
        permission_mode: Current permission mode.

    Examples:
        >>> payload = PermissionUpdatePayload(
        ...     tool_name="file_read",
        ...     tool_input={"path": "/etc/passwd"},
        ...     permission_decision="deny",
        ...     permission_decision_reason="Access to sensitive system files denied",
        ...     session_id="session-123",
        ...     cwd="/workspace"
        ... )
        >>> payload.permission_decision
        'deny'
        >>> payload.permission_decision_reason
        'Access to sensitive system files denied'
    """

    tool_name: str = Field(description="Name of the tool for which permission decision was made")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool invocation")
    permission_decision: Literal["allow", "deny"] = Field(description="The permission decision that was made")
    permission_decision_reason: Optional[str] = Field(
        default=None, description="Reason for the permission decision"
    )
    session_id: str = Field(description="Unique session identifier")
    cwd: str = Field(description="Current working directory")
    permission_mode: Literal["default", "plan", "acceptEdits", "dontAsk", "bypassPermissions"] = Field(
        description="Current permission mode"
    )


PermissionRequestResult = PluginResult[PermissionRequestPayload]
PermissionUpdateResult = PluginResult[PermissionUpdatePayload]


def _register_claude_permission_hooks() -> None:
    """Register Claude permission hooks in the global registry.

    This is called lazily to avoid circular import issues.
    """
    # Import here to avoid circular dependency at module load time
    # First-Party
    from cpex.framework.hooks.registry import get_hook_registry  # pylint: disable=import-outside-toplevel

    registry = get_hook_registry()

    # Only register if not already registered (idempotent)
    if not registry.is_registered(ClaudePermissionHookType.PERMISSION_REQUEST):
        registry.register_hook(
            ClaudePermissionHookType.PERMISSION_REQUEST,
            PermissionRequestPayload,
            PermissionRequestResult
        )
        registry.register_hook(
            ClaudePermissionHookType.PERMISSION_UPDATE,
            PermissionUpdatePayload,
            PermissionUpdateResult
        )


_register_claude_permission_hooks()