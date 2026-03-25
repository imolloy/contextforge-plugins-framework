# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/schemas/claude_code_extension_example.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0

Example of how to extend the improved Claude Code schema mapper
with new hook types using the generic infrastructure.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from cpex.framework.models import PluginPayload, PluginResult
from cpex.tools.schemas.claude_code_improved import (
    ClaudeCommonFields,
    ClaudeCommonOutput,
    HookMapper,
    ImprovedClaudeCodeSchemaMapper,
    register_schema_mapper
)

# =============================================================================
# Agent Hook Schemas (Example Extension)
# =============================================================================

class ClaudeAgentStartInput(ClaudeCommonFields):
    """Claude Code SubagentStart event input schema."""
    agent_name: str = Field(description="Name of the agent being started")
    agent_config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    parent_agent_id: Optional[str] = Field(default=None, description="Parent agent if this is a subagent")


class ClaudeAgentStartOutput(ClaudeCommonOutput):
    """Claude Code SubagentStart event output schema."""

    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["SubagentStart"] = "SubagentStart"
        agent_allowed: bool = Field(description="Whether agent start is allowed")
        modified_config: Optional[Dict[str, Any]] = Field(default=None, description="Modified agent config")

    hook_specific_output: HookSpecificOutput = Field(description="SubagentStart specific output")


# CPEX Agent payload (would typically be defined in cpex/framework/hooks/agents.py)
class AgentPreInvokePayload(PluginPayload):
    """CPEX agent pre-invoke payload."""
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[str] = None


class AgentStartMapper(HookMapper[ClaudeAgentStartInput, ClaudeAgentStartOutput, AgentPreInvokePayload, PluginResult]):
    """Mapper for Claude Code SubagentStart events."""

    def __init__(self):
        super().__init__(ClaudeAgentStartInput, ClaudeAgentStartOutput, AgentPreInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeAgentStartInput) -> AgentPreInvokePayload:
        """Transform Claude SubagentStart to CPEX AgentPreInvokePayload."""
        return AgentPreInvokePayload(
            name=claude_input.agent_name,
            config=claude_input.agent_config,
            parent_id=claude_input.parent_agent_id
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeAgentStartOutput:
        """Transform CPEX PluginResult to Claude SubagentStart output."""
        hook_specific = ClaudeAgentStartOutput.HookSpecificOutput(
            agent_allowed=cpex_result.continue_processing,
            modified_config=cpex_result.modified_payload
        )

        return ClaudeAgentStartOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hook_specific_output=hook_specific
        )


# =============================================================================
# Extended Schema Mapper
# =============================================================================

class ExtendedClaudeCodeSchemaMapper(ImprovedClaudeCodeSchemaMapper):
    """Extended Claude Code schema mapper with agent hooks."""

    def __init__(self):
        super().__init__()
        # Add new hook mappers
        self.add_hook_mapper("agent_pre_invoke", AgentStartMapper())
        # Could add more: agent_post_invoke, session_start, session_end, etc.


# Register the extended schema mapper
register_schema_mapper("claude-code-extended", ExtendedClaudeCodeSchemaMapper)


# =============================================================================
# Usage Example
# =============================================================================

if __name__ == "__main__":
    # Create extended mapper
    mapper = ExtendedClaudeCodeSchemaMapper()

    print("Supported hook types:", mapper.get_supported_hooks())

    # Example agent start payload
    claude_agent_payload = {
        "agent_name": "code_analyzer",
        "agent_config": {"max_depth": 5, "include_tests": True},
        "parent_agent_id": "main_agent_123",
        "session_id": "session_456",
        "transcript_path": "/tmp/transcript.log",
        "cwd": "/workspace",
        "permission_mode": "default",
        "hook_event_name": "SubagentStart",
    }

    # Map to CPEX format
    cpex_payload = mapper.map_to_hook_payload(claude_agent_payload, "agent_pre_invoke")
    print("CPEX Agent Payload:", cpex_payload)

    # Example result
    cpex_result = PluginResult(
        continue_processing=True,
        modified_payload={"max_depth": 3, "include_tests": True},  # Modified by policy
        metadata={"approved_by": "security_plugin"}
    )

    # Map back to Claude format
    claude_output = mapper.map_from_hook_result(cpex_result, "agent_pre_invoke")
    print("Claude Agent Output:", claude_output)