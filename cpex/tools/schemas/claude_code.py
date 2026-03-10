# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/schemas/claude_code.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Claude Code

Claude Code Schema Mapper ─ transform Claude Code hook events to CPEX formats
This module provides schema mapping for Claude Code hook events, enabling
seamless integration between Claude Code's hook system and CPEX plugins.

Features
─────────
* Maps Claude Code tool events to CPEX tool hooks
* Transforms Claude Code payloads to CPEX payload formats
* Converts CPEX results back to Claude Code formats
* Supports all major Claude Code hook event types

Classes
───────
* ClaudeCodeSchemaMapper: Main schema mapper for Claude Code integration

Supported Hook Mappings
──────────────────────
* PreToolUse → tool_pre_invoke
* PostToolUse → tool_post_invoke
* PostToolUseFailure → tool_post_invoke (with error information)

Future Expansion
───────────────
* SessionStart, SessionEnd → custom session hooks
* UserPromptSubmit → custom user interaction hooks
* SubagentStart, SubagentStop → agent hooks
* PermissionRequest → custom authorization hooks
"""

# Standard
import logging
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

# First-Party
from cpex.framework.models import PluginResult
from cpex.tools.schemas.base import SchemaMapper, register_schema_mapper

logger = logging.getLogger(__name__)


# Hard code the mapping here for now
CLAUDE_CODE_CPEX_HOOK_MAPPING = {
    "PreToolUse": {
        "hook_type": "tool_pre_invoke",
        "payload": {
            "name": "command",
            "args": "",
            "headers": None
        }
    },
    "PostToolUse": "tool_post_invoke",
    "PostToolUseFailure": "tool_post_invoke",  # Map failures to post-invoke with error info
    # Future mappings:
    # "SessionStart": "session_start",
    # "SessionEnd": "session_end",
    # "UserPromptSubmit": "user_prompt_submit",
    # "SubagentStart": "agent_pre_invoke",
    # "SubagentStop": "agent_post_invoke",
    # "PermissionRequest": "permission_request",
}





class ClaudeCodeSchemaMapper(SchemaMapper):
    """Schema mapper for Claude Code hook events.

    This mapper transforms Claude Code hook event payloads into CPEX-compatible
    formats and converts CPEX results back to Claude Code formats.

    The mapper focuses on tool execution events initially, with support for
    additional event types to be added as needed.

    Examples:
        >>> mapper = ClaudeCodeSchemaMapper()
        >>> claude_payload = {
        ...     "tool_name": "search",
        ...     "arguments": {"query": "test"},
        ...     "session_id": "123"
        ... }
        >>> cpex_payload = mapper.map_to_hook_payload(claude_payload, "tool_pre_invoke")
        >>> cpex_payload["name"]
        'search'
        >>> cpex_payload["args"]["query"]
        'test'
    """

    def get_supported_hooks(self) -> list[str]:
        """Get list of CPEX hook types supported by this mapper.

        Returns:
            List of supported CPEX hook type names
        """
        return [
            "tool_pre_invoke",
            "tool_post_invoke",
            # Future additions:
            # "agent_pre_invoke",
            # "agent_post_invoke",
            # "session_start",
            # "session_end",
        ]

    def map_to_hook_payload(self, external_payload: Dict[str, Any], hook_type: str) -> Dict[str, Any]:
        """Transform Claude Code payload to CPEX hook format.

        Args:
            external_payload: Claude Code hook event payload
            hook_type: CPEX hook type being invoked

        Returns:
            Transformed payload in CPEX format

        Raises:
            ValueError: If payload cannot be transformed
            NotImplementedError: If hook type is not supported
        """
        if hook_type == "tool_pre_invoke":
            return self._map_pre_tool_use(external_payload)
        elif hook_type == "tool_post_invoke":
            return self._map_post_tool_use(external_payload)
        else:
            raise NotImplementedError(
                f"Claude Code schema mapping not implemented for hook type: {hook_type}"
            )

    def map_from_hook_result(self, hook_result: PluginResult, hook_type: str) -> Dict[str, Any]:
        """Transform CPEX hook result to Claude Code format.

        Args:
            hook_result: CPEX hook execution result
            hook_type: CPEX hook type that was invoked

        Returns:
            Transformed result in Claude Code format

        Raises:
            NotImplementedError: If hook type is not supported
        """
        if hook_type in ["tool_pre_invoke", "tool_post_invoke"]:
            return self._map_tool_result(hook_result, hook_type)
        else:
            raise NotImplementedError(
                f"Claude Code result mapping not implemented for hook type: {hook_type}"
            )

    def _map_pre_tool_use(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Map Claude Code PreToolUse event to tool_pre_invoke payload.

        Args:
            payload: Claude Code PreToolUse payload

        Returns:
            CPEX tool_pre_invoke payload
        """
        # Claude Code PreToolUse structure:
        # {
        #   "tool_name": "string",
        #   "arguments": {...},
        #   "session_id": "string",
        #   "user_id": "string",
        #   "timestamp": "string",
        #   ... other metadata
        # }

        tool_name = payload.get("tool_name")
        if not tool_name:
            raise ValueError("Claude Code payload missing required 'tool_name' field")

        # Build CPEX tool_pre_invoke payload
        cpex_payload = {
            "name": tool_name,
            "args": payload.get("tool_input", {}),
        }

        # Add headers if available (for HTTP passthrough)
        headers = payload.get("headers")
        if headers:
            cpex_payload["headers"] = headers

        logger.debug(f"Mapped Claude Code PreToolUse to CPEX: {tool_name}")
        return cpex_payload

    def _map_post_tool_use(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Map Claude Code PostToolUse/PostToolUseFailure event to tool_post_invoke payload.

        Args:
            payload: Claude Code PostToolUse or PostToolUseFailure payload

        Returns:
            CPEX tool_post_invoke payload
        """
        # Claude Code PostToolUse structure:
        # {
        #   "tool_name": "string",
        #   "result": {...} | "error": {...},
        #   "execution_time": number,
        #   "session_id": "string",
        #   "success": boolean,
        #   ... other metadata
        # }

        tool_name = payload.get("tool_name")
        if not tool_name:
            raise ValueError("Claude Code payload missing required 'tool_name' field")

        # Build result object - prefer 'result' field, fall back to 'error', or use whole payload
        result = payload.get("result")
        if result is None and "error" in payload:
            # For failure cases, wrap error in result
            result = {
                "success": False,
                "error": payload["error"],
                "execution_time": payload.get("execution_time")
            }
        elif result is None:
            # Use the entire payload as result (filtering out tool_name)
            result = {k: v for k, v in payload.items() if k != "tool_name"}

        cpex_payload = {
            "name": tool_name,
            "result": result,
        }

        logger.debug(f"Mapped Claude Code PostToolUse to CPEX: {tool_name}")
        return cpex_payload

    def _map_tool_result(self, hook_result: PluginResult, hook_type: str) -> Dict[str, Any]:
        """Map CPEX tool hook result to Claude Code format.

        Args:
            hook_result: CPEX hook result
            hook_type: CPEX hook type

        Returns:
            Claude Code formatted result
        """
        # Convert to dictionary and add Claude Code specific fields
        result = hook_result.model_dump()

        # Add Claude Code specific response format
        claude_result = {
            "continue": hook_result.continue_processing,
            # "cpex_result": result,
            # "hook_type": hook_type,
        }
        if hook_type == "tool_pre_invoke":
            claude_result["hookSpecificOutput"] = {
                "HookEventName": "PreToolUse",
                "PermissionDecision": "allow" if hook_result.continue_processing else "deny",
                # "PermissionDecisionReason": hook_result.violation.reason if hook_result.violation else None
            }

        # Include violation information if present
        if hook_result.violation:
            claude_result["stopReason"] = hook_result.violation.reason
            if hook_type == "tool_pre_invoke":
                claude_result["hookSpecificOutput"]["PermissionDecision"] = "deny"
                claude_result["hookSpecificOutput"]["PermissionDecisionReason"] = hook_result.violation.reason
            # claude_result["violation"] = {
            #     "stopReason": hook_result.violation.reason,
            #     "code": hook_result.violation.code,
            #     "details": hook_result.violation.details,
            # }

        # Include modified payload if present
        if hook_result.modified_payload:
            claude_result["modified_payload"] = hook_result.modified_payload

        # Include metadata if present
        if hook_result.metadata:
            claude_result["metadata"] = hook_result.metadata

        return claude_result

    def validate_external_payload(self, external_payload: Dict[str, Any], hook_type: str) -> bool:
        """Validate Claude Code payload for the specified hook type.

        Args:
            external_payload: Claude Code payload
            hook_type: CPEX hook type

        Returns:
            True if payload is valid, False otherwise
        """
        if hook_type in ["tool_pre_invoke", "tool_post_invoke"]:
            # Both tool hooks require tool_name
            return "tool_name" in external_payload and external_payload["tool_name"]

        # For unsupported hook types, return False
        return False


# Register the Claude Code schema mapper
register_schema_mapper("claude-code", ClaudeCodeSchemaMapper)


class ClaudeCommonInput(BaseModel):
    """Claude Code Hook Common Input Schema."""
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: Literal["default", "plan", "acceptEdits", "dontAsk", "bypassPermissions"]
    hook_event_name: str
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None


class ClaudeCommonOutput(BaseModel):
    _continue: bool
    stopReason: str
    suppressOutput: bool
    systemMessage: str


class PreToolUseModel(ClaudeCommonInput):
    """Claude Code PreToolUse Event Schema."""
    tool_name: str
    tool_input: Dict[str, Any]
