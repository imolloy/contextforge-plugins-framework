# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/schemas/claude_code_improved.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0

Improved Claude Code Schema Mapper with Type Safety

This module provides a complete type-safe schema mapping system between
Claude Code hook events and CPEX formats using Pydantic models.

Key Improvements:
- Full type safety with Pydantic models
- Automatic validation
- Clear separation of input/output schemas
- Easy to extend for new hook types
- Generic mapping infrastructure
- Better error handling and debugging
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Generic, Literal, Optional, Type, TypeVar, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from cpex.framework.hooks.tools import ToolPreInvokePayload, ToolPostInvokePayload
from cpex.framework.models import PluginResult, PluginViolation
from cpex.tools.schemas.base import SchemaMapper, register_schema_mapper

logger = logging.getLogger(__name__)

# Type variables for generic mapping
ClaudeInput = TypeVar('ClaudeInput', bound=BaseModel)
ClaudeOutput = TypeVar('ClaudeOutput', bound=BaseModel)
CPEXPayload = TypeVar('CPEXPayload', bound=BaseModel)
CPEXResult = TypeVar('CPEXResult', bound=PluginResult)

# =============================================================================
# Claude Code Input Schemas
# =============================================================================


class ClaudeCommonFields(BaseModel):
    """Common fields present in all Claude Code hook events."""
    session_id: str = Field(description="Unique session identifier")
    transcript_path: str = Field(description="Path to conversation transcript")
    cwd: str = Field(description="Current working directory")
    permission_mode: Literal["default", "plan", "acceptEdits", "dontAsk", "bypassPermissions"] = Field(
        description="Current permission mode"
    )
    hook_event_name: str = Field(description="Name of the hook event")
    agent_id: Optional[str] = Field(default=None, description="Agent identifier if applicable")
    agent_type: Optional[str] = Field(default=None, description="Agent type if applicable")


class ClaudePreToolUseInput(ClaudeCommonFields):
    """Claude Code PreToolUse event input schema."""
    tool_name: str = Field(description="Name of the tool being invoked")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments for tool invocation")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers for passthrough")

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        return v.strip()


class ClaudePostToolUseInput(ClaudeCommonFields):
    """Claude Code PostToolUse event input schema."""
    tool_name: str = Field(description="Name of the tool that was invoked")
    result: Optional[Any] = Field(default=None, description="Tool execution result")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information if tool failed")
    execution_time: Optional[float] = Field(default=None, description="Tool execution time in seconds")
    success: bool = Field(default=True, description="Whether tool execution was successful")

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        return v.strip()

    @model_validator(mode='after')
    def validate_result_or_error(self):
        if not self.success and not self.error:
            raise ValueError("error field required when success=False")
        return self


# =============================================================================
# Claude Code Output Schemas
# =============================================================================

class ClaudeCommonOutput(BaseModel):
    """Common output fields for all Claude Code responses."""
    continue_: bool = Field(alias="_continue", description="Whether to continue processing")
    stop_reason: Optional[str] = Field(default=None, description="Reason for stopping if continue=False")
    suppress_output: bool = Field(default=False, description="Whether to suppress output to user")
    system_message: Optional[str] = Field(default=None, description="Message to display to user")

    model_config = {"populate_by_name": True}


class ClaudePreToolUseOutput(ClaudeCommonOutput):
    """Claude Code PreToolUse event output schema."""

    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PreToolUse"] = "PreToolUse"
        permission_decision: Literal["allow", "deny"] = Field(description="Permission decision")
        permission_decision_reason: Optional[str] = Field(default=None, description="Reason for denial")

    hook_specific_output: HookSpecificOutput = Field(description="PreToolUse specific output")
    modified_payload: Optional[Dict[str, Any]] = Field(default=None, description="Modified tool arguments")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ClaudePostToolUseOutput(ClaudeCommonOutput):
    """Claude Code PostToolUse event output schema."""

    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PostToolUse"] = "PostToolUse"
        # Add any PostToolUse specific fields here

    hook_specific_output: HookSpecificOutput = Field(description="PostToolUse specific output")
    modified_result: Optional[Any] = Field(default=None, description="Modified tool result")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# =============================================================================
# Generic Mapping Infrastructure
# =============================================================================

class HookMapper(ABC, Generic[ClaudeInput, ClaudeOutput, CPEXPayload, CPEXResult]):
    """Abstract base class for type-safe hook mapping."""

    def __init__(
        self,
        claude_input_type: Type[ClaudeInput],
        claude_output_type: Type[ClaudeOutput],
        cpex_payload_type: Type[CPEXPayload],
    ):
        self.claude_input_type = claude_input_type
        self.claude_output_type = claude_output_type
        self.cpex_payload_type = cpex_payload_type

    def map_to_cpex(self, claude_input: Dict[str, Any]) -> CPEXPayload:
        """Map Claude Code input to CPEX payload with validation."""
        try:
            # Validate and parse Claude input
            validated_input = self.claude_input_type.model_validate(claude_input)
            # Transform to CPEX format
            return self._transform_to_cpex(validated_input)
        except Exception as e:
            logger.error(f"Failed to map Claude input to CPEX: {e}")
            raise ValueError(f"Invalid Claude Code input: {e}") from e

    def map_from_cpex(self, cpex_result: PluginResult) -> Dict[str, Any]:
        """Map CPEX result to Claude Code output with validation."""
        try:
            # Transform to Claude format
            claude_output = self._transform_from_cpex(cpex_result)
            # Validate and return as dict
            return claude_output.model_dump(by_alias=True)
        except Exception as e:
            logger.error(f"Failed to map CPEX result to Claude output: {e}")
            raise ValueError(f"Invalid CPEX result: {e}") from e

    @abstractmethod
    def _transform_to_cpex(self, claude_input: ClaudeInput) -> CPEXPayload:
        """Transform validated Claude input to CPEX payload."""
        pass

    @abstractmethod
    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeOutput:
        """Transform CPEX result to Claude output."""
        pass


# =============================================================================
# Specific Hook Mappers
# =============================================================================

class PreToolUseMapper(HookMapper[ClaudePreToolUseInput, ClaudePreToolUseOutput, ToolPreInvokePayload, PluginResult]):
    """Mapper for PreToolUse events."""

    def __init__(self):
        super().__init__(ClaudePreToolUseInput, ClaudePreToolUseOutput, ToolPreInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudePreToolUseInput) -> ToolPreInvokePayload:
        """Transform Claude PreToolUse to CPEX ToolPreInvokePayload."""
        from cpex.framework.hooks.http import HttpHeaderPayload

        headers = None
        if claude_input.headers:
            headers = HttpHeaderPayload(claude_input.headers)

        return ToolPreInvokePayload(
            name=claude_input.tool_name,
            args=claude_input.tool_input,
            headers=headers
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudePreToolUseOutput:
        """Transform CPEX PluginResult to Claude PreToolUse output."""
        # Determine permission decision
        permission_decision = "allow" if cpex_result.continue_processing else "deny"
        permission_reason = None

        if cpex_result.violation:
            permission_reason = cpex_result.violation.reason

        hook_specific = ClaudePreToolUseOutput.HookSpecificOutput(
            permission_decision=permission_decision,
            permission_decision_reason=permission_reason
        )

        return ClaudePreToolUseOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hook_specific_output=hook_specific,
            modified_payload=cpex_result.modified_payload,
            metadata=cpex_result.metadata
        )


class PostToolUseMapper(HookMapper[ClaudePostToolUseInput, ClaudePostToolUseOutput, ToolPostInvokePayload, PluginResult]):
    """Mapper for PostToolUse events."""

    def __init__(self):
        super().__init__(ClaudePostToolUseInput, ClaudePostToolUseOutput, ToolPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudePostToolUseInput) -> ToolPostInvokePayload:
        """Transform Claude PostToolUse to CPEX ToolPostInvokePayload."""
        # Build result object, preferring explicit result field
        result = claude_input.result
        if result is None and claude_input.error:
            # For error cases, structure the result
            result = {
                "success": False,
                "error": claude_input.error,
                "execution_time": claude_input.execution_time
            }
        elif result is None:
            # Use available fields as result
            result = {
                "success": claude_input.success,
                "execution_time": claude_input.execution_time
            }

        return ToolPostInvokePayload(
            name=claude_input.tool_name,
            result=result
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudePostToolUseOutput:
        """Transform CPEX PluginResult to Claude PostToolUse output."""
        hook_specific = ClaudePostToolUseOutput.HookSpecificOutput()

        return ClaudePostToolUseOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hook_specific_output=hook_specific,
            modified_result=cpex_result.modified_payload,
            metadata=cpex_result.metadata
        )


# =============================================================================
# Main Schema Mapper
# =============================================================================

class ImprovedClaudeCodeSchemaMapper(SchemaMapper):
    """Improved type-safe schema mapper for Claude Code integration."""

    def __init__(self):
        self._mappers = {
            "tool_pre_invoke": PreToolUseMapper(),
            "tool_post_invoke": PostToolUseMapper(),
        }

    def get_supported_hooks(self) -> list[str]:
        """Get list of supported CPEX hook types."""
        return list(self._mappers.keys())

    def map_to_hook_payload(self, external_payload: Dict[str, Any], hook_type: str) -> Dict[str, Any]:
        """Transform Claude Code payload to CPEX format with full type safety."""
        if hook_type not in self._mappers:
            raise NotImplementedError(f"Hook type not supported: {hook_type}")

        mapper = self._mappers[hook_type]
        cpex_payload = mapper.map_to_cpex(external_payload)

        # Convert to dict for compatibility with existing interfaces
        result = cpex_payload.model_dump()
        logger.debug(f"Mapped {hook_type}: {external_payload.get('tool_name', 'unknown')} -> {result}")
        return result

    def map_from_hook_result(self, hook_result: PluginResult, hook_type: str) -> Dict[str, Any]:
        """Transform CPEX result to Claude Code format with full type safety."""
        if hook_type not in self._mappers:
            raise NotImplementedError(f"Hook type not supported: {hook_type}")

        mapper = self._mappers[hook_type]
        claude_output = mapper.map_from_cpex(hook_result)

        logger.debug(f"Mapped result for {hook_type}: continue={hook_result.continue_processing}")
        return claude_output

    def validate_external_payload(self, external_payload: Dict[str, Any], hook_type: str) -> bool:
        """Validate Claude Code payload using Pydantic validation."""
        if hook_type not in self._mappers:
            return False

        try:
            mapper = self._mappers[hook_type]
            # Attempt validation by trying to create the input model
            mapper.claude_input_type.model_validate(external_payload)
            return True
        except Exception as e:
            logger.debug(f"Validation failed for {hook_type}: {e}")
            return False

    def add_hook_mapper(self, hook_type: str, mapper: HookMapper) -> None:
        """Add a new hook mapper for extensibility."""
        self._mappers[hook_type] = mapper
        logger.info(f"Added mapper for hook type: {hook_type}")


# Register the improved schema mapper
register_schema_mapper("claude-code-improved", ImprovedClaudeCodeSchemaMapper)


# =============================================================================
# Usage Examples and Migration Helper
# =============================================================================

def migrate_from_old_mapper() -> ImprovedClaudeCodeSchemaMapper:
    """Helper function to migrate from old ClaudeCodeSchemaMapper.

    Returns:
        ImprovedClaudeCodeSchemaMapper instance ready to use

    Examples:
        >>> # Replace old mapper
        >>> # old_mapper = ClaudeCodeSchemaMapper()
        >>> mapper = migrate_from_old_mapper()
        >>>
        >>> # Same interface, better type safety
        >>> claude_payload = {
        ...     "tool_name": "search",
        ...     "tool_input": {"query": "test"},
        ...     "session_id": "123",
        ...     "transcript_path": "/tmp/transcript",
        ...     "cwd": "/workspace",
        ...     "permission_mode": "default",
        ...     "hook_event_name": "PreToolUse"
        ... }
        >>> cpex_payload = mapper.map_to_hook_payload(claude_payload, "tool_pre_invoke")
        >>> assert cpex_payload["name"] == "search"
        >>> assert cpex_payload["args"]["query"] == "test"
    """
    return ImprovedClaudeCodeSchemaMapper()


if __name__ == "__main__":
    # Example usage
    mapper = ImprovedClaudeCodeSchemaMapper()

    # Example Claude Code PreToolUse payload
    claude_payload = {
        "tool_name": "file_reader",
        "tool_input": {"path": "/example.txt", "mode": "read"},
        "session_id": "session_123",
        "transcript_path": "/tmp/transcript.log",
        "cwd": "/workspace",
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "headers": {"Authorization": "Bearer token123"}
    }

    # Map to CPEX format
    cpex_payload = mapper.map_to_hook_payload(claude_payload, "tool_pre_invoke")
    print("CPEX Payload:", cpex_payload)

    # Example CPEX result
    from cpex.framework.models import PluginViolation
    violation = PluginViolation(
        reason="File access denied",
        description="Cannot access system files",
        code="ACCESS_DENIED",
        details={"path": "/example.txt"}
    )
    cpex_result = PluginResult(
        continue_processing=False,
        violation=violation,
        metadata={"plugin": "security_checker"}
    )

    # Map back to Claude format
    claude_output = mapper.map_from_hook_result(cpex_result, "tool_pre_invoke")
    print("Claude Output:", claude_output)