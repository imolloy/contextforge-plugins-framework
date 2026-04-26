# -*- coding: utf-8 -*-
# flake8: noqa
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
from typing import Annotated, Any, Dict, Generic, List, Literal, Optional, Type, TypeVar, Union
from xml.parsers.expat import model

from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator, AliasChoices

from cpex.framework.hooks.tools import ToolPreInvokePayload, ToolPostInvokePayload
from cpex.framework.hooks.prompts import PromptPrehookPayload, PromptPosthookPayload
from cpex.framework.hooks.agents import AgentPreInvokePayload, AgentPostInvokePayload
from cpex.framework.hooks.resources import ResourcePreFetchPayload, ResourcePostFetchPayload
from cpex.framework.hooks.claude_instructions import InstructionsLoadedPayload
from cpex.framework.hooks.claude_permissions import PermissionRequestPayload, PermissionUpdatePayload
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
    agent_id: Optional[str] = Field(default=None, description="Agent identifier if applicable")
    agent_type: Optional[str] = Field(default=None, description="Agent name")


class ClaudeSessionStartInput(ClaudeCommonFields):
    """Claude Code SessionStart event input schema."""
    hook_event_name: Literal["SessionStart"]
    source: str = Field(description="Indicates how a session was started")
    model: str = Field(description="Model being used for the session")


class ClaudeInstructionsLoaded(ClaudeCommonFields):
    """Claude Code InstructionsLoaded event input schema."""
    hook_event_name: Literal["InstructionsLoaded"]
    file_path: str = Field(description="Path to the loaded instructions file")
    memory_type: Literal["User", "Project", "Local", "Managed"] = Field(description="Scope of the file loaded")
    load_reason: Literal["session_start", "nested_traversal", "path_glob_match", "include", "compact"] = Field(description="Why the file loaded")
    globs: str = Field(description="Glob patterns used for file paths")
    trigger_file_path: str = Field(description="Path to the file whose access triggered this load, for lazy loads")
    parent_file_path: str   = Field(description="Path to the parent file")


class ClaudeUserPromptSubmitInput(ClaudeCommonFields):
    """Claude Code UserPromptSubmit event input schema."""
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str = Field(description="Content of the user prompt")


class ClaudePermissionRequestInput(ClaudeCommonFields):
    """Claude Code PermissionRequest event input schema."""
    hook_event_name: Literal["PermissionRequest"]
    tool_name: str = Field(description="Name of the tool for which permission is being requested")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool invocation")
    permission_suggestions: Optional[Dict[str, Any]] = Field(default=None, description="Suggested permission decisions based on input")
    # TODO Add a better type of permission suggestion

class ClaudePermissionUpdateInput(ClaudeCommonFields):
    """Claude Code PermissionUpdate event input schema."""
    hook_event_name: Literal["PermissionUpdate"]
    tool_name: str = Field(description="Name of the tool for which permission decision was made")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool invocation")
    permission_decision: Literal["allow", "deny"] = Field(description="The permission decision that was made")
    permission_decision_reason: Optional[str] = Field(default=None, description="Reason for the permission decision")

class ClaudePreToolUseInput(ClaudeCommonFields):
    """Claude Code PreToolUse event input schema."""
    hook_event_name: Literal["PreToolUse"]
    tool_name: str = Field(description="Name of the tool being invoked",
                           validation_alias=AliasChoices("name", "tool_name"),
                           serialization_alias="name")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments for tool invocation",
                                       validation_alias=AliasChoices("tool_input", "args"),
                                       serialization_alias="args")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers for passthrough")

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        return v.strip()


class ClaudePostToolUseInput(ClaudeCommonFields):
    """Claude Code PostToolUse event input schema."""
    hook_event_name: Literal["PostToolUse"]
    tool_name: str = Field(description="Name of the tool that was invoked")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments that were used for tool invocation")    
    tool_response: Optional[Dict[str, Any]] = Field(default=None, description="Raw response from the tool")
    tool_use_id: str

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        return v.strip()


class ClaudePostToolUseFailureInput(ClaudeCommonFields):
    """Claude Code PostToolUse event input schema for failed tool invocations."""
    hook_event_name: Literal["PostToolUseFailure"]
    tool_name: str = Field(description="Name of the tool that was invoked")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="Arguments that were used for tool invocation")    
    tool_response: Dict[str, Any] = Field(default=None, description="Raw response from the tool")
    tool_use_id: str
    error: str = Field(description="Error message describing the failure")
    is_interrupt: Optional[bool] = Field(default=False, description="Whether the failure was due to an interrupt")


class ClaudeNotificationInput(ClaudeCommonFields):
    """Claude Code Notification event input schema."""
    hook_event_name: Literal["Notification"]
    message: str = Field(description="Content of the notification")
    title: str = Field(description="Title of the notification")
    notification_type: Literal["permission_prompt", "idle_prompt", "auth_success", "elicitation_dialog"]
    

class ClaudeSubAgentStartupInput(ClaudeCommonFields):
    hook_event_name: Literal["SubAgentStartup"]
    agent_id: str = Field(description="Identifier for the sub-agent that is starting up")
    agent_type: str = Field(description="Type or name of the sub-agent that is starting up")
    

class ClaudeSubAgentStopInput(ClaudeCommonFields):
    hook_event_name: Literal["SubAgentStop"]
    stop_hook_active: bool = Field(description="Whether the stop hook is active and can be used to intercept the shutdown process")
    agent_id: str = Field(description="Identifier for the sub-agent that is shutting down")
    agent_type: str = Field(description="Type or name of the sub-agent that is shutting down")
    agent_transcript_path: str = Field(description="Path to the sub-agent's transcript file that can be accessed during shutdown")
    last_assistant_message: str = Field(description="Content of the last message sent by the assistant before shutdown")


class ClaudeStopInput(ClaudeCommonFields):
    hook_event_name: Literal["Stop"]
    stop_hook_active: bool = Field(description="Whether the stop hook is active and can be used to intercept the shutdown process")
    last_assistant_message: str = Field(description="Content of the last message sent by the assistant before shutdown")


class ClaudeStopFailureInput(ClaudeCommonFields):
    hook_event_name: Literal["StopFailure"]
    stop_hook_active: bool = Field(description="Whether the stop hook is active and can be used to intercept the shutdown process")
    last_assistant_message: str = Field(description="Content of the last message sent by the assistant before shutdown")
    error: str = Field(description="Error message describing the failure")
    error_details: Optional[str] = Field(default=None, description="Additional details about the error")


class ClaudeTeammateIdleInput(ClaudeCommonFields):
    hook_event_name: Literal["TeammateIdle"]
    teammate_name: str = Field(description="Name of the teammate who is idle")
    team_name: str = Field(description="Name of the team that the idle teammate belongs to")


class ClaudeTaskCompletedInput(ClaudeCommonFields):
    hook_event_name: Literal["TaskCompleted"]
    task_id: str = Field(description="Identifier of the task being completed")
    task_subject: str = Field(description="Title of the task")
    task_description: Optional[str] = Field(default=None, description="Detailed description of the task. May be absent")
    teammate_name: Optional[str] = Field(default=None, description="Name of the teammate completing the task. May be absent")
    team_name: Optional[str] = Field(default=None, description="Name of the team. May be absent")
    

class ClaudeConfigChangeInput(ClaudeCommonFields):
    hook_event_name: Literal["ConfigChange"]
    source: str = Field(description="Indicates which configuration type changed")
    file_path: Optional[str] = Field(default=None, description="The path to the specific file that was modified")


class ClaudeWorktreeCreateInput(ClaudeCommonFields):
    hook_event_name: Literal["WorktreeCreate"]
    name: str = Field(description="Slug identifier for the new worktree, either specified by the user or auto-generated")


class ClaudeWorktreeRemoveInput(ClaudeCommonFields):
    hook_event_name: Literal["WorktreeRemove"]
    worktree_path: str = Field(description="Path to the worktree that is being removed")


class ClaudePreCompactInput(ClaudeCommonFields):
    hook_event_name: Literal["PreCompact"]
    trigger: Literal["manual", "auto"] = Field(description="What triggered the compaction process")
    custom_instructions: str = Field(description="The custom instructions that will be used for the compaction process, if applicable")
    # No additional fields for now, but can be extended in the future


class ClaudePostCompactInput(ClaudeCommonFields):
    hook_event_name: Literal["PostCompact"]
    trigger: Literal["manual", "auto"] = Field(description="What triggered the compaction process")
    compact_summary: str = Field(description="The custom instructions that were used for the compaction process, if applicable")

class ClaudeSessionEndInput(ClaudeCommonFields):
    hook_event_name: Literal["SessionEnd"]
    reason: Literal["clear", "resume", "logout", "prompt_input_exit", "bypass_permissions_disabled", "other"] = Field(description="Reason for session end")
    

class ClaudeElicitationInput(ClaudeCommonFields):
    hook_event_name: Literal["Elicitation"]
    mcp_server_name: str = Field(description="Name of the MCP server that is eliciting information")
    message: str = Field(description="The message content eliciting information from the user")
    # mode: Optional[str] = Field(default=None, description="The mode of elicitation, if applicable")
    mode: Optional[Literal["form", "url"]] = Field(default=None, description="The mode of elicitation, if applicable")
    url: Optional[str] = Field(default=None, description="A URL related to the elicitation, if applicable")
    elicitation_id: Optional[str] = Field(default=None, description="An identifier for the elicitation event, if applicable")
    requested_schema: Optional[Dict[str, Any]] = Field(default=None, description="The schema for the information being elicited, if applicable")
    

class ClaudeElicitationResultInput(ClaudeCommonFields):
    hook_event_name: Literal["ElicitationResult"]
    mcp_server_name: str = Field(description="Name of the MCP server that elicited information")
    action: str = Field(description="The action that the user took in response to the elicitation")
    elicitation_id: Optional[str] = Field(default=None, description="An identifier for the elicitation event, if applicable")
    mode: Optional[Literal["form", "url"]] = Field(default=None, description="The mode of elicitation, if applicable")
    elicitation_id: Optional[str] = Field(default=None, description="An identifier for the elicitation event, if applicable")
    content: Optional[Union[str, Dict[str, Any]]] = Field(default=None, description="The content of the user's response to the elicitation, which may be a string or structured data depending on the elicitation mode and requested schema")
 
                                    
ClaudeHookInput = Annotated[
    Union[ClaudeSessionStartInput,
        ClaudeUserPromptSubmitInput,
        ClaudePreToolUseInput,
        ClaudePostToolUseInput,
        ClaudePostToolUseFailureInput,
        ClaudePermissionRequestInput,
        ClaudePermissionUpdateInput,
        ClaudeNotificationInput,
        ClaudeSubAgentStartupInput,
        ClaudeSubAgentStopInput,
        ClaudeStopInput,
        ClaudeStopFailureInput,
        ClaudeTeammateIdleInput,
        ClaudeTaskCompletedInput,
        ClaudeConfigChangeInput,
        ClaudeWorktreeCreateInput,
        ClaudeWorktreeRemoveInput,
        ClaudePreCompactInput,
        ClaudePostCompactInput,
        ClaudeElicitationInput,
        ClaudeElicitationResultInput,
        ClaudeSessionEndInput,
        ClaudeInstructionsLoaded
        ],
    Field(discriminator="hook_event_name")
]

# =============================================================================
# Claude Code Output Schemas
# =============================================================================

# TODO Verify these common fields
class ClaudeCommonOutput(BaseModel):
    """Common output fields for all Claude Code responses."""
    continue_: Optional[bool] = Field(alias="_continue", description="Whether to continue processing")
    stop_reason: Optional[str] = Field(default=None, description="Reason for stopping if continue=False")
    suppress_output: Optional[bool] = Field(default=False, description="Whether to suppress output to user")
    system_message: Optional[str] = Field(default=None, description="Message to display to user")
    model_config = {"populate_by_name": True}


class ClaudePreToolUseOutput(ClaudeCommonOutput):
    """Claude Code PreToolUse event output schema."""

    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PreToolUse"] = "PreToolUse"
        permission_decision: Literal["allow", "deny"] = Field(description="Permission decision")
        permission_decision_reason: Optional[str] = Field(default=None, description="Reason for denial")
        updatedInput: Optional[Dict[str, Any]] = Field(default=None, description="Updated tool input arguments if modified by the hook")
        additionalContext: Optional[str] = Field(default=None, description="Additional context added to the model")
    hookSpecificOutput: HookSpecificOutput = Field(description="PreToolUse specific output")


class ClaudePostToolUseOutput(ClaudeCommonOutput):
    """Claude Code PostToolUse event output schema."""

    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PostToolUse"] = "PostToolUse"
        # Add any PostToolUse specific fields here

    hookSpecificOutput: HookSpecificOutput = Field(description="PostToolUse specific output")
    modified_result: Optional[Any] = Field(default=None, description="Modified tool result")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ClaudeSessionStartOutput(ClaudeCommonOutput):
    """Claude Code SessionStart event output schema."""
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["SessionStart"] = "SessionStart"
        additionalContext: str = Field(description="Additional context to provide for the session")
    hookSpecificOutput: HookSpecificOutput = Field(description="SessionStart specific output")


class ClaudeInstructionsLoadedOutput(ClaudeCommonOutput):
    """InstructionsLoaded hooks have no decision control.
    They cannot block or modify instruction loading.
    Use this event for audit logging, compliance tracking, or observability."""


class ClaudeUserPromptSubmitOutput(ClaudeCommonOutput):
    """UserPromptSubmit hooks have no decision control. They cannot block or modify the user prompt. Use this event for audit logging, compliance tracking, or observability."""
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["UserPromptSubmit"] = "UserPromptSubmit"
        addditionalContext: Optional[str] = Field(default=None, description="Additional context added to the model")
    decision: Optional[Literal["block"]] = Field(default=None, description="Whether to block the user prompt")
    reason: str = Field(default="", description="Reason for blocking the user prompt if decision is block. Shown to the user")
    hookSpecificOutput: Optional[HookSpecificOutput] = Field(default=None, description="UserPromptSubmit specific output")


class ClaudePreToolUseOutput(ClaudeCommonOutput):
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PreToolUse"] = "PreToolUse"
        permission_decision: Literal["allow", "deny", "ask"] = Field(description="Permission decision")
        permissionDecisionReason: Optional[str] = Field(default=None, description="Reason for denial")
        updatedInput: Optional[Dict[str, Any]] = Field(default=None, description="Updated tool input arguments if modified by the hook")
        additionalContext: Optional[str] = Field(default=None, description="Additional context added to the model")
    hookSpecificOutput: HookSpecificOutput = Field(description="PreToolUse specific output")


class ClaudePermissionRequestOutput(ClaudeCommonOutput):
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PermissionRequest"] = "PermissionRequest"
        behavior: Literal["allow", "deny"] = Field(description="Behavior for the permission request")
        updatedInput: Optional[Dict[str, Any]] = Field(default=None, description="Updated tool input arguments if modified by the hook")
        # TODO Add a better type of permission suggestion
        updatedPermissions: Optional[List[Any]] = Field(default=None, description="Updated permissions if modified by the hook")
        message: Optional[str] = Field(default=None, description="Message to model regarding the permission request")
        interrupt: Optional[bool] = Field(default=False, description="If `deny` stop the model")
    hookSpecificOutput: HookSpecificOutput = Field(description="PermissionRequest specific output")


class ClaudePostToolUseOutput(ClaudeCommonOutput):
    decision: Optional[Literal["block"]] = Field(default=None, description="Whether to block the tool response from being sent to the model")
    reason: str = Field(default="", description="Reason for blocking the tool response if decision is block")
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PostToolUse"] = "PostToolUse"
        additionalContext: Optional[str] = Field(default=None, description="Additional context added to the model")
        updatedMCPToolOutput: Optional[Any] = Field(default=None, description="Updated tool output if modified by the hook")
    hookSpecificOutput: Optional[HookSpecificOutput] = Field(default=None, description="PostToolUse specific output")


class ClaudePostToolUseFailureOutput(ClaudeCommonOutput):
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["PostToolUseFailure"] = "PostToolUseFailure"
        additionalContext: Optional[str] = Field(default=None, description="Additional context added to the model")
    hookSpecificOutput: Optional[HookSpecificOutput] = Field(default=None, description="PostToolUseFailure specific output")


class ClaudeNotificationOutput(ClaudeCommonOutput):
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["Notification"] = "Notification"
        additionalContext: Optional[str] = Field(default=None, description="Additional context added to the model")
    hookSpecificOutput: Optional[HookSpecificOutput] = Field(default=None, description="Notification specific output")


class ClaudeSubAgentStartupOutput(ClaudeCommonOutput):
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["SubAgentStartup"] = "SubAgentStartup"
        additionalContext: Optional[str] = Field(default=None, description="Additional context added to the model")
    hookSpecificOutput: Optional[HookSpecificOutput] = Field(default=None, description="SubAgentStartup specific output")


class ClaudeSubAgentStopOutput(ClaudeCommonOutput):
    decision: Optional[Literal["block"]] = Field(default=None, description="Whether to block the sub-agent shutdown process")
    reason: str = Field(default="", description="Reason for blocking the sub-agent shutdown if decision is block")


class ClaudeStopOutput(ClaudeCommonOutput):
    """StopFailure hooks have no decision control.
    They run for notification and logging purposes only."""


# TODO Fix this. There is some very different behavior here we need to look into
class ClaudeTeammateIdleOutput(ClaudeCommonOutput):
    continue_: bool = Field(default=True, alias="_continue", description="Whether to continue processing")
    stopReason: Optional[str] = Field(default=None, description="Reason for stopping if continue=False")


# TODO Fix this. There is some very different behavior here we need to look into
class ClaudeTaskCompletedOutput(ClaudeCommonOutput):
    continue_: bool = Field(default=True, alias="_continue", description="Whether to continue processing")
    stopReason: Optional[str] = Field(default=None, description="Reason for stopping if continue=False")


class ClaudeConfigChangeOutput(ClaudeCommonOutput):
    decision: Optional[Literal["block"]] = Field(default=True, alias="_continue", description="Whether to continue processing")
    reason: Optional[str] = Field(default=None, description="Reason for stopping if continue=False")

# TODO Worktree outputs are different. Not currently supported


class ClaudeElicitationOutput(ClaudeCommonOutput):
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["Elicitation"] = "Elicitation"
        action: Literal["accept", "decline", "cancel"] = Field(default=None, description="Whether to accept, decline, or cancel the request")
        content: Optional[Dict[str, Any]] = Field(default=None, description="Form field values to submit. Only used when action is accept")
    hookSpecificOutput: Optional[HookSpecificOutput] = Field(default=None, description="Elicitation specific output")

class ClaudeElicitationResultOutput(ClaudeCommonOutput):
    class HookSpecificOutput(BaseModel):
        hook_event_name: Literal["ElicitationResult"] = "ElicitationResult"
        action: Literal["accept", "decline", "cancel"] = Field(default=None, description="Whether to accept, decline, or cancel the request")
        content: Optional[Dict[str, Any]] = Field(default=None, description="Form field values to submit. Only used when action is accept")
    hookSpecificOutput: Optional[HookSpecificOutput] = Field(default=None, description="Elicitation specific output")


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

    
    def _transform_to_cpex(self, claude_input: ClaudeInput) -> CPEXPayload:
        """Transform validated Claude input to CPEX payload."""
        return self.cpex_payload_type(**claude_input.model_dump(by_alias=True))
        
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

    # def _transform_to_cpex(self, claude_input: ClaudePreToolUseInput) -> ToolPreInvokePayload:
    #     """Transform Claude PreToolUse to CPEX ToolPreInvokePayload."""
    #     from cpex.framework.hooks.http import HttpHeaderPayload

    #     headers = None
    #     if claude_input.headers:
    #         headers = HttpHeaderPayload(claude_input.headers)

    #     return ToolPreInvokePayload(
    #         name=claude_input.tool_name,
    #         args=claude_input.tool_input,
    #         headers=headers
    #     )

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
            hookSpecificOutput={"permission_decision": cpex_result.continue_processing,
                                "permission_decision_reason": cpex_result.violation.reason if cpex_result.violation else None,
                                "updatedInput": cpex_result.modified_payload if cpex_result.modified_payload else None
                                },
        )


class PostToolUseMapper(HookMapper[ClaudePostToolUseInput, ClaudePostToolUseOutput, ToolPostInvokePayload, PluginResult]):
    """Mapper for PostToolUse events."""

    def __init__(self):
        super().__init__(ClaudePostToolUseInput, ClaudePostToolUseOutput, ToolPostInvokePayload)

    # def _transform_to_cpex(self, claude_input: ClaudePostToolUseInput) -> ToolPostInvokePayload:
    #     """Transform Claude PostToolUse to CPEX ToolPostInvokePayload."""
    #     # Build result object, preferring explicit result field
    #     result = claude_input.result
    #     if result is None and claude_input.error:
    #         # For error cases, structure the result
    #         result = {
    #             "success": False,
    #             "error": claude_input.error,
    #             "execution_time": claude_input.execution_time
    #         }
    #     elif result is None:
    #         # Use available fields as result
    #         result = {
    #             "success": claude_input.success,
    #             "execution_time": claude_input.execution_time
    #         }

    #     return ToolPostInvokePayload(
    #         name=claude_input.tool_name,
    #         result=result
    #     )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudePostToolUseOutput:
        """Transform CPEX PluginResult to Claude PostToolUse output."""
        hook_specific = ClaudePostToolUseOutput.HookSpecificOutput()

        return ClaudePostToolUseOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
            modified_result=cpex_result.modified_payload,
            metadata=cpex_result.metadata
        )


class UserPromptSubmitMapper(HookMapper[ClaudeUserPromptSubmitInput, ClaudeUserPromptSubmitOutput, PromptPosthookPayload, PluginResult]):
    """Mapper for UserPromptSubmit events."""

    def __init__(self):
        super().__init__(ClaudeUserPromptSubmitInput, ClaudeUserPromptSubmitOutput, PromptPosthookPayload)
    
    def _transform_to_cpex(self, claude_input: ClaudeUserPromptSubmitInput) -> PromptPosthookPayload:
        """Transform Claude UserPromptSubmit to CPEX PromptPosthookPayload."""
        return PromptPosthookPayload(
            prompt_id="",  # Claude does not provide a prompt ID, so we can leave this blank or generate one if needed
            result=claude_input.prompt
        )
    
    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeUserPromptSubmitOutput:
        """Transform CPEX PluginResult to Claude UserPromptSubmit output."""
        hook_specific = ClaudeUserPromptSubmitOutput.HookSpecificOutput()

        return ClaudeUserPromptSubmitOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


class SubAgentStartupMapper(HookMapper[ClaudeSubAgentStartupInput, ClaudeSubAgentStartupOutput, AgentPreInvokePayload, PluginResult]):
    """Mapper for SubAgentStartup events."""

    def __init__(self):
        super().__init__(ClaudeSubAgentStartupInput, ClaudeSubAgentStartupOutput, AgentPreInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeSubAgentStartupInput) -> AgentPreInvokePayload:
        """Transform Claude SubAgentStartup to CPEX AgentPreInvokePayload."""
        return AgentPreInvokePayload(
            agent_id=claude_input.agent_id,
            messages=[],  # No messages in startup event
            tools=None,
            headers=None,
            model=None,
            system_prompt=None,
            parameters={"agent_type": claude_input.agent_type}
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeSubAgentStartupOutput:
        """Transform CPEX PluginResult to Claude SubAgentStartup output."""
        hook_specific = ClaudeSubAgentStartupOutput.HookSpecificOutput()

        return ClaudeSubAgentStartupOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


class SubAgentStopMapper(HookMapper[ClaudeSubAgentStopInput, ClaudeSubAgentStopOutput, AgentPostInvokePayload, PluginResult]):
    """Mapper for SubAgentStop events."""

    def __init__(self):
        super().__init__(ClaudeSubAgentStopInput, ClaudeSubAgentStopOutput, AgentPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeSubAgentStopInput) -> AgentPostInvokePayload:
        """Transform Claude SubAgentStop to CPEX AgentPostInvokePayload."""
        # Create a simple message representing the agent's final state
        final_message = {
            "role": "assistant",
            "content": claude_input.last_assistant_message
        }

        return AgentPostInvokePayload(
            agent_id=claude_input.agent_id,
            messages=[final_message],
            tool_calls=None
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeSubAgentStopOutput:
        """Transform CPEX PluginResult to Claude SubAgentStop output."""
        decision = "block" if not cpex_result.continue_processing else None
        reason = cpex_result.violation.reason if cpex_result.violation else ""

        return ClaudeSubAgentStopOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            decision=decision,
            reason=reason
        )


class PostToolUseFailureMapper(HookMapper[ClaudePostToolUseFailureInput, ClaudePostToolUseFailureOutput, ToolPostInvokePayload, PluginResult]):
    """Mapper for PostToolUseFailure events."""

    def __init__(self):
        super().__init__(ClaudePostToolUseFailureInput, ClaudePostToolUseFailureOutput, ToolPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudePostToolUseFailureInput) -> ToolPostInvokePayload:
        """Transform Claude PostToolUseFailure to CPEX ToolPostInvokePayload."""
        # Structure the result to include error information
        result = {
            "success": False,
            "error": claude_input.error,
            "is_interrupt": claude_input.is_interrupt,
            "tool_response": claude_input.tool_response,
            "tool_use_id": claude_input.tool_use_id
        }

        return ToolPostInvokePayload(
            name=claude_input.tool_name,
            result=result
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudePostToolUseFailureOutput:
        """Transform CPEX PluginResult to Claude PostToolUseFailure output."""
        hook_specific = ClaudePostToolUseFailureOutput.HookSpecificOutput()

        return ClaudePostToolUseFailureOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


class InstructionsLoadedMapper(HookMapper[ClaudeInstructionsLoaded, ClaudeInstructionsLoadedOutput, InstructionsLoadedPayload, PluginResult]):
    """Mapper for InstructionsLoaded events."""

    def __init__(self):
        super().__init__(ClaudeInstructionsLoaded, ClaudeInstructionsLoadedOutput, InstructionsLoadedPayload)

    def _transform_to_cpex(self, claude_input: ClaudeInstructionsLoaded) -> InstructionsLoadedPayload:
        """Transform Claude InstructionsLoaded to CPEX InstructionsLoadedPayload."""
        return InstructionsLoadedPayload(
            file_path=claude_input.file_path,
            memory_type=claude_input.memory_type,
            load_reason=claude_input.load_reason,
            globs=claude_input.globs,
            trigger_file_path=claude_input.trigger_file_path,
            parent_file_path=claude_input.parent_file_path
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeInstructionsLoadedOutput:
        """Transform CPEX PluginResult to Claude InstructionsLoaded output."""
        # InstructionsLoaded hooks are audit-only - they cannot block or modify
        return ClaudeInstructionsLoadedOutput(
            continue_=True,  # Always continue for audit-only hooks
            stop_reason=None
        )


class PermissionRequestMapper(HookMapper[ClaudePermissionRequestInput, ClaudePermissionRequestOutput, PermissionRequestPayload, PluginResult]):
    """Mapper for PermissionRequest events."""

    def __init__(self):
        super().__init__(ClaudePermissionRequestInput, ClaudePermissionRequestOutput, PermissionRequestPayload)

    def _transform_to_cpex(self, claude_input: ClaudePermissionRequestInput) -> PermissionRequestPayload:
        """Transform Claude PermissionRequest to CPEX PermissionRequestPayload."""
        return PermissionRequestPayload(
            tool_name=claude_input.tool_name,
            tool_input=claude_input.tool_input,
            permission_suggestions=claude_input.permission_suggestions,
            session_id=claude_input.session_id,
            cwd=claude_input.cwd,
            permission_mode=claude_input.permission_mode
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudePermissionRequestOutput:
        """Transform CPEX PluginResult to Claude PermissionRequest output."""
        # Determine behavior based on continue_processing
        behavior = "allow" if cpex_result.continue_processing else "deny"

        hook_specific = ClaudePermissionRequestOutput.HookSpecificOutput(
            behavior=behavior,
            updatedInput=cpex_result.modified_payload.tool_input if cpex_result.modified_payload else None,
            message=cpex_result.violation.reason if cpex_result.violation else None,
            interrupt=not cpex_result.continue_processing
        )

        return ClaudePermissionRequestOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


class PermissionUpdateMapper(HookMapper[ClaudePermissionUpdateInput, ClaudePermissionRequestOutput, PermissionUpdatePayload, PluginResult]):
    """Mapper for PermissionUpdate events."""

    def __init__(self):
        super().__init__(ClaudePermissionUpdateInput, ClaudePermissionRequestOutput, PermissionUpdatePayload)

    def _transform_to_cpex(self, claude_input: ClaudePermissionUpdateInput) -> PermissionUpdatePayload:
        """Transform Claude PermissionUpdate to CPEX PermissionUpdatePayload."""
        return PermissionUpdatePayload(
            tool_name=claude_input.tool_name,
            tool_input=claude_input.tool_input,
            permission_decision=claude_input.permission_decision,
            permission_decision_reason=claude_input.permission_decision_reason,
            session_id=claude_input.session_id,
            cwd=claude_input.cwd,
            permission_mode=claude_input.permission_mode
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudePermissionRequestOutput:
        """Transform CPEX PluginResult to Claude PermissionUpdate output."""
        # PermissionUpdate hooks are primarily audit-only
        behavior = "allow" if cpex_result.continue_processing else "deny"

        hook_specific = ClaudePermissionRequestOutput.HookSpecificOutput(
            behavior=behavior,
            message=cpex_result.violation.reason if cpex_result.violation else None,
        )

        return ClaudePermissionRequestOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


# =============================================================================
# Session Lifecycle Event Mappers
# =============================================================================

class SessionStartMapper(HookMapper[ClaudeSessionStartInput, ClaudeSessionStartOutput, AgentPreInvokePayload, PluginResult]):
    """Mapper for SessionStart events."""

    def __init__(self):
        super().__init__(ClaudeSessionStartInput, ClaudeSessionStartOutput, AgentPreInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeSessionStartInput) -> AgentPreInvokePayload:
        """Transform Claude SessionStart to CPEX AgentPreInvokePayload."""
        return AgentPreInvokePayload(
            agent_id=f"claude_session_{claude_input.session_id}",
            messages=[],
            tools=None,
            headers=None,
            model=claude_input.model,
            system_prompt=None,
            parameters={
                "source": claude_input.source,
                "session_id": claude_input.session_id,
                "cwd": claude_input.cwd,
                "permission_mode": claude_input.permission_mode
            }
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeSessionStartOutput:
        """Transform CPEX PluginResult to Claude SessionStart output."""
        additional_context = ""
        if cpex_result.metadata:
            # Extract any additional context from metadata
            additional_context = cpex_result.metadata.get("additional_context", "")

        hook_specific = ClaudeSessionStartOutput.HookSpecificOutput(
            additionalContext=additional_context
        )

        return ClaudeSessionStartOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


class SessionEndMapper(HookMapper[ClaudeSessionEndInput, ClaudeCommonOutput, AgentPostInvokePayload, PluginResult]):
    """Mapper for SessionEnd events."""

    def __init__(self):
        super().__init__(ClaudeSessionEndInput, ClaudeCommonOutput, AgentPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeSessionEndInput) -> AgentPostInvokePayload:
        """Transform Claude SessionEnd to CPEX AgentPostInvokePayload."""
        # Create a simple message representing the session end
        end_message = {
            "role": "system",
            "content": f"Session ended: {claude_input.reason}"
        }

        return AgentPostInvokePayload(
            agent_id=f"claude_session_{claude_input.session_id}",
            messages=[end_message],
            tool_calls=None
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeCommonOutput:
        """Transform CPEX PluginResult to Claude SessionEnd output."""
        # SessionEnd hooks are primarily audit-only
        return ClaudeCommonOutput(
            continue_=True,  # Always continue for audit-only hooks
            stop_reason=None
        )


class StopMapper(HookMapper[ClaudeStopInput, ClaudeStopOutput, AgentPostInvokePayload, PluginResult]):
    """Mapper for Stop events."""

    def __init__(self):
        super().__init__(ClaudeStopInput, ClaudeStopOutput, AgentPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeStopInput) -> AgentPostInvokePayload:
        """Transform Claude Stop to CPEX AgentPostInvokePayload."""
        stop_message = {
            "role": "assistant",
            "content": claude_input.last_assistant_message
        }

        return AgentPostInvokePayload(
            agent_id=f"claude_session_{claude_input.session_id}",
            messages=[stop_message],
            tool_calls=None
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeStopOutput:
        """Transform CPEX PluginResult to Claude Stop output."""
        # Stop hooks are notification/logging only
        return ClaudeStopOutput(
            continue_=True,  # Always continue for audit-only hooks
            stop_reason=None
        )


class StopFailureMapper(HookMapper[ClaudeStopFailureInput, ClaudeCommonOutput, AgentPostInvokePayload, PluginResult]):
    """Mapper for StopFailure events."""

    def __init__(self):
        super().__init__(ClaudeStopFailureInput, ClaudeCommonOutput, AgentPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeStopFailureInput) -> AgentPostInvokePayload:
        """Transform Claude StopFailure to CPEX AgentPostInvokePayload."""
        failure_message = {
            "role": "system",
            "content": f"Stop failed: {claude_input.error}"
        }

        if claude_input.last_assistant_message:
            # Also include the last assistant message
            failure_message_assistant = {
                "role": "assistant",
                "content": claude_input.last_assistant_message
            }
            messages = [failure_message_assistant, failure_message]
        else:
            messages = [failure_message]

        return AgentPostInvokePayload(
            agent_id=f"claude_session_{claude_input.session_id}",
            messages=messages,
            tool_calls=None
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeCommonOutput:
        """Transform CPEX PluginResult to Claude StopFailure output."""
        # StopFailure hooks are notification/logging only
        return ClaudeCommonOutput(
            continue_=True,  # Always continue for audit-only hooks
            stop_reason=None
        )


# =============================================================================
# Notification Event Mappers
# =============================================================================

class NotificationMapper(HookMapper[ClaudeNotificationInput, ClaudeNotificationOutput, PromptPosthookPayload, PluginResult]):
    """Mapper for Notification events."""

    def __init__(self):
        super().__init__(ClaudeNotificationInput, ClaudeNotificationOutput, PromptPosthookPayload)

    def _transform_to_cpex(self, claude_input: ClaudeNotificationInput) -> PromptPosthookPayload:
        """Transform Claude Notification to CPEX PromptPosthookPayload."""
        # Treat the notification as a prompt result
        notification_result = {
            "title": claude_input.title,
            "message": claude_input.message,
            "notification_type": claude_input.notification_type,
            "session_id": claude_input.session_id
        }

        return PromptPosthookPayload(
            prompt_id=f"notification_{claude_input.notification_type}",
            result=notification_result
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeNotificationOutput:
        """Transform CPEX PluginResult to Claude Notification output."""
        additional_context = ""
        if cpex_result.metadata:
            additional_context = cpex_result.metadata.get("additional_context", "")

        hook_specific = ClaudeNotificationOutput.HookSpecificOutput(
            additionalContext=additional_context
        )

        return ClaudeNotificationOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


class TaskCompletedMapper(HookMapper[ClaudeTaskCompletedInput, ClaudeTaskCompletedOutput, ToolPostInvokePayload, PluginResult]):
    """Mapper for TaskCompleted events."""

    def __init__(self):
        super().__init__(ClaudeTaskCompletedInput, ClaudeTaskCompletedOutput, ToolPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeTaskCompletedInput) -> ToolPostInvokePayload:
        """Transform Claude TaskCompleted to CPEX ToolPostInvokePayload."""
        # Treat the task as a completed tool execution
        task_result = {
            "task_id": claude_input.task_id,
            "task_subject": claude_input.task_subject,
            "task_description": claude_input.task_description,
            "teammate_name": claude_input.teammate_name,
            "team_name": claude_input.team_name,
            "success": True,
            "completed": True
        }

        return ToolPostInvokePayload(
            name=f"task_{claude_input.task_id}",
            result=task_result
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeTaskCompletedOutput:
        """Transform CPEX PluginResult to Claude TaskCompleted output."""
        # TaskCompleted hooks are audit-only
        return ClaudeTaskCompletedOutput(
            continue_=True,
            stopReason=None
        )


class TeammateIdleMapper(HookMapper[ClaudeTeammateIdleInput, ClaudeTeammateIdleOutput, AgentPostInvokePayload, PluginResult]):
    """Mapper for TeammateIdle events."""

    def __init__(self):
        super().__init__(ClaudeTeammateIdleInput, ClaudeTeammateIdleOutput, AgentPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeTeammateIdleInput) -> AgentPostInvokePayload:
        """Transform Claude TeammateIdle to CPEX AgentPostInvokePayload."""
        idle_message = {
            "role": "system",
            "content": f"Teammate {claude_input.teammate_name} is idle in team {claude_input.team_name}"
        }

        return AgentPostInvokePayload(
            agent_id=claude_input.teammate_name,
            messages=[idle_message],
            tool_calls=None
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeTeammateIdleOutput:
        """Transform CPEX PluginResult to Claude TeammateIdle output."""
        # TeammateIdle hooks are notification-only
        return ClaudeTeammateIdleOutput(
            continue_=True,
            stopReason=None
        )


# =============================================================================
# Configuration Event Mappers
# =============================================================================

class ConfigChangeMapper(HookMapper[ClaudeConfigChangeInput, ClaudeConfigChangeOutput, ResourcePostFetchPayload, PluginResult]):
    """Mapper for ConfigChange events."""

    def __init__(self):
        super().__init__(ClaudeConfigChangeInput, ClaudeConfigChangeOutput, ResourcePostFetchPayload)

    def _transform_to_cpex(self, claude_input: ClaudeConfigChangeInput) -> ResourcePostFetchPayload:
        """Transform Claude ConfigChange to CPEX ResourcePostFetchPayload."""
        # Treat the config change as a resource fetch event
        config_content = {
            "source": claude_input.source,
            "file_path": claude_input.file_path,
            "session_id": claude_input.session_id,
            "change_type": "config_change"
        }

        # Use file path if available, otherwise use source as URI
        uri = claude_input.file_path if claude_input.file_path else f"config://{claude_input.source}"

        return ResourcePostFetchPayload(
            uri=uri,
            content=config_content
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeConfigChangeOutput:
        """Transform CPEX PluginResult to Claude ConfigChange output."""
        # ConfigChange hooks can potentially block
        decision = "block" if not cpex_result.continue_processing else None
        reason = cpex_result.violation.reason if cpex_result.violation else None

        return ClaudeConfigChangeOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            decision=decision,
            reason=reason
        )


# =============================================================================
# Worktree Event Mappers
# =============================================================================

class WorktreeCreateMapper(HookMapper[ClaudeWorktreeCreateInput, ClaudeCommonOutput, ToolPreInvokePayload, PluginResult]):
    """Mapper for WorktreeCreate events."""

    def __init__(self):
        super().__init__(ClaudeWorktreeCreateInput, ClaudeCommonOutput, ToolPreInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeWorktreeCreateInput) -> ToolPreInvokePayload:
        """Transform Claude WorktreeCreate to CPEX ToolPreInvokePayload."""
        worktree_args = {
            "name": claude_input.name,
            "session_id": claude_input.session_id,
            "cwd": claude_input.cwd,
            "action": "create"
        }

        return ToolPreInvokePayload(
            name="worktree_create",
            args=worktree_args
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeCommonOutput:
        """Transform CPEX PluginResult to Claude WorktreeCreate output."""
        # WorktreeCreate hooks are primarily audit-only
        return ClaudeCommonOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None
        )


class WorktreeRemoveMapper(HookMapper[ClaudeWorktreeRemoveInput, ClaudeCommonOutput, ToolPostInvokePayload, PluginResult]):
    """Mapper for WorktreeRemove events."""

    def __init__(self):
        super().__init__(ClaudeWorktreeRemoveInput, ClaudeCommonOutput, ToolPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudeWorktreeRemoveInput) -> ToolPostInvokePayload:
        """Transform Claude WorktreeRemove to CPEX ToolPostInvokePayload."""
        worktree_result = {
            "worktree_path": claude_input.worktree_path,
            "session_id": claude_input.session_id,
            "action": "remove",
            "success": True
        }

        return ToolPostInvokePayload(
            name="worktree_remove",
            result=worktree_result
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeCommonOutput:
        """Transform CPEX PluginResult to Claude WorktreeRemove output."""
        # WorktreeRemove hooks are primarily audit-only
        return ClaudeCommonOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None
        )


# =============================================================================
# Compaction Event Mappers
# =============================================================================

class PreCompactMapper(HookMapper[ClaudePreCompactInput, ClaudeCommonOutput, ToolPreInvokePayload, PluginResult]):
    """Mapper for PreCompact events."""

    def __init__(self):
        super().__init__(ClaudePreCompactInput, ClaudeCommonOutput, ToolPreInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudePreCompactInput) -> ToolPreInvokePayload:
        """Transform Claude PreCompact to CPEX ToolPreInvokePayload."""
        compact_args = {
            "trigger": claude_input.trigger,
            "custom_instructions": claude_input.custom_instructions,
            "session_id": claude_input.session_id,
            "action": "pre_compact"
        }

        return ToolPreInvokePayload(
            name="compaction",
            args=compact_args
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeCommonOutput:
        """Transform CPEX PluginResult to Claude PreCompact output."""
        return ClaudeCommonOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None
        )


class PostCompactMapper(HookMapper[ClaudePostCompactInput, ClaudeCommonOutput, ToolPostInvokePayload, PluginResult]):
    """Mapper for PostCompact events."""

    def __init__(self):
        super().__init__(ClaudePostCompactInput, ClaudeCommonOutput, ToolPostInvokePayload)

    def _transform_to_cpex(self, claude_input: ClaudePostCompactInput) -> ToolPostInvokePayload:
        """Transform Claude PostCompact to CPEX ToolPostInvokePayload."""
        compact_result = {
            "trigger": claude_input.trigger,
            "compact_summary": claude_input.compact_summary,
            "session_id": claude_input.session_id,
            "action": "post_compact",
            "success": True
        }

        return ToolPostInvokePayload(
            name="compaction",
            result=compact_result
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeCommonOutput:
        """Transform CPEX PluginResult to Claude PostCompact output."""
        return ClaudeCommonOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None
        )


# =============================================================================
# Elicitation Event Mappers
# =============================================================================

class ElicitationMapper(HookMapper[ClaudeElicitationInput, ClaudeElicitationOutput, PromptPrehookPayload, PluginResult]):
    """Mapper for Elicitation events."""

    def __init__(self):
        super().__init__(ClaudeElicitationInput, ClaudeElicitationOutput, PromptPrehookPayload)

    def _transform_to_cpex(self, claude_input: ClaudeElicitationInput) -> PromptPrehookPayload:
        """Transform Claude Elicitation to CPEX PromptPrehookPayload."""
        # Convert all args to strings as required by PromptPrehookPayload
        elicitation_args = {
            "mcp_server_name": claude_input.mcp_server_name,
            "message": claude_input.message,
            "mode": claude_input.mode or "",
            "url": claude_input.url or "",
            "elicitation_id": claude_input.elicitation_id or "",
            "requested_schema": str(claude_input.requested_schema) if claude_input.requested_schema else ""
        }

        return PromptPrehookPayload(
            prompt_id=claude_input.elicitation_id or f"elicitation_{claude_input.mcp_server_name}",
            args=elicitation_args
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeElicitationOutput:
        """Transform CPEX PluginResult to Claude Elicitation output."""
        # Default action based on continue_processing
        action = "accept" if cpex_result.continue_processing else "decline"
        content = None

        # Extract action and content from metadata if available
        if cpex_result.metadata:
            action = cpex_result.metadata.get("action", action)
            content = cpex_result.metadata.get("content", content)

        hook_specific = ClaudeElicitationOutput.HookSpecificOutput(
            action=action,
            content=content
        )

        return ClaudeElicitationOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )


class ElicitationResultMapper(HookMapper[ClaudeElicitationResultInput, ClaudeElicitationResultOutput, PromptPosthookPayload, PluginResult]):
    """Mapper for ElicitationResult events."""

    def __init__(self):
        super().__init__(ClaudeElicitationResultInput, ClaudeElicitationResultOutput, PromptPosthookPayload)

    def _transform_to_cpex(self, claude_input: ClaudeElicitationResultInput) -> PromptPosthookPayload:
        """Transform Claude ElicitationResult to CPEX PromptPosthookPayload."""
        elicitation_result = {
            "mcp_server_name": claude_input.mcp_server_name,
            "action": claude_input.action,
            "elicitation_id": claude_input.elicitation_id,
            "mode": claude_input.mode,
            "content": claude_input.content
        }

        return PromptPosthookPayload(
            prompt_id=claude_input.elicitation_id or f"elicitation_result_{claude_input.mcp_server_name}",
            result=elicitation_result
        )

    def _transform_from_cpex(self, cpex_result: PluginResult) -> ClaudeElicitationResultOutput:
        """Transform CPEX PluginResult to Claude ElicitationResult output."""
        # Default action based on continue_processing
        action = "accept" if cpex_result.continue_processing else "decline"
        content = None

        # Extract action and content from metadata if available
        if cpex_result.metadata:
            action = cpex_result.metadata.get("action", action)
            content = cpex_result.metadata.get("content", content)

        hook_specific = ClaudeElicitationResultOutput.HookSpecificOutput(
            action=action,
            content=content
        )

        return ClaudeElicitationResultOutput(
            continue_=cpex_result.continue_processing,
            stop_reason=cpex_result.violation.reason if cpex_result.violation else None,
            hookSpecificOutput=hook_specific,
        )

# =============================================================================
# Main Schema Mapper
# =============================================================================

class ImprovedClaudeCodeSchemaMapper(SchemaMapper):
    """Improved type-safe schema mapper for Claude Code integration."""

    def __init__(self):
        self._mappers = {
            # Original mappers
            "PreToolUse": PreToolUseMapper(),
            "PostToolUse": PostToolUseMapper(),
            "UserPromptSubmit": UserPromptSubmitMapper(),

            # Phase 1: Direct CPEX mappings
            "SubAgentStartup": SubAgentStartupMapper(),
            "SubAgentStop": SubAgentStopMapper(),
            "PostToolUseFailure": PostToolUseFailureMapper(),

            # Phase 2: Claude Code specific payloads
            "InstructionsLoaded": InstructionsLoadedMapper(),
            "PermissionRequest": PermissionRequestMapper(),
            "PermissionUpdate": PermissionUpdateMapper(),

            # Phase 3: Session lifecycle events
            "SessionStart": SessionStartMapper(),
            "SessionEnd": SessionEndMapper(),
            "Stop": StopMapper(),
            "StopFailure": StopFailureMapper(),

            # Phase 4: Notification events
            "Notification": NotificationMapper(),
            "TaskCompleted": TaskCompletedMapper(),
            "TeammateIdle": TeammateIdleMapper(),

            # Phase 5: Configuration events
            "ConfigChange": ConfigChangeMapper(),

            # Phase 6: Worktree events
            "WorktreeCreate": WorktreeCreateMapper(),
            "WorktreeRemove": WorktreeRemoveMapper(),

            # Phase 7: Compaction events
            "PreCompact": PreCompactMapper(),
            "PostCompact": PostCompactMapper(),

            # Phase 8: Elicitation events
            "Elicitation": ElicitationMapper(),
            "ElicitationResult": ElicitationResultMapper()
        }
        self.adapter = TypeAdapter(ClaudeHookInput)

    def get_supported_hooks(self) -> list[str]:
        """Get list of supported CPEX hook types."""
        return list(self._mappers.keys())

    def map_to_hook_payload(self, external_payload: Dict[str, Any]) -> CPEXPayload:
        """Transform Claude Code payload to CPEX format with full type safety."""
        payload = self.adapter.validate_python(external_payload)
        
        if payload.hook_event_name not in self._mappers:
            raise NotImplementedError(f"Hook type not supported: {payload.hook_event_name}")

        mapper = self._mappers[payload.hook_event_name]
        cpex_payload = mapper.map_to_cpex(payload)
        return cpex_payload


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


# # =============================================================================
# # Usage Examples and Migration Helper
# # =============================================================================

# def migrate_from_old_mapper() -> ImprovedClaudeCodeSchemaMapper:
#     """Helper function to migrate from old ClaudeCodeSchemaMapper.

#     Returns:
#         ImprovedClaudeCodeSchemaMapper instance ready to use

#     Examples:
#         >>> # Replace old mapper
#         >>> # old_mapper = ClaudeCodeSchemaMapper()
#         >>> mapper = migrate_from_old_mapper()
#         >>>
#         >>> # Same interface, better type safety
#         >>> claude_payload = {
#         ...     "tool_name": "search",
#         ...     "tool_input": {"query": "test"},
#         ...     "session_id": "123",
#         ...     "transcript_path": "/tmp/transcript",
#         ...     "cwd": "/workspace",
#         ...     "permission_mode": "default",
#         ...     "hook_event_name": "PreToolUse"
#         ... }
#         >>> cpex_payload = mapper.map_to_hook_payload(claude_payload, "tool_pre_invoke")
#         >>> assert cpex_payload["name"] == "search"
#         >>> assert cpex_payload["args"]["query"] == "test"
#     """
#     return ImprovedClaudeCodeSchemaMapper()


