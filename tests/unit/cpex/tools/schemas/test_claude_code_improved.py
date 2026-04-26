# -*- coding: utf-8 -*-
"""Unit tests for Improved Claude Code schema mapper.

Tests the new hook mappers and their input/output conversions.
"""

import pytest
from unittest.mock import Mock

from cpex.framework.models import PluginResult, PluginViolation
from cpex.framework.hooks.tools import ToolPreInvokePayload, ToolPostInvokePayload
from cpex.framework.hooks.agents import AgentPreInvokePayload, AgentPostInvokePayload
from cpex.framework.hooks.claude_instructions import InstructionsLoadedPayload
from cpex.framework.hooks.claude_permissions import PermissionRequestPayload, PermissionUpdatePayload

from cpex.tools.schemas.claude_code_improved import (
    ImprovedClaudeCodeSchemaMapper,
    SubAgentStartupMapper,
    SubAgentStopMapper,
    PostToolUseFailureMapper,
    InstructionsLoadedMapper,
    PermissionRequestMapper,
    PermissionUpdateMapper,
    ClaudeSubAgentStartupInput,
    ClaudeSubAgentStopInput,
    ClaudePostToolUseFailureInput,
    ClaudeInstructionsLoaded,
    ClaudePermissionRequestInput,
    ClaudePermissionUpdateInput
)


class TestSubAgentStartupMapper:
    """Test suite for SubAgentStartupMapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = SubAgentStartupMapper()

    def test_input_validation_valid(self):
        """Test valid SubAgentStartup input validation."""
        valid_input = {
            "hook_event_name": "SubAgentStartup",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "agent_id": "agent-123",
            "agent_type": "explore"
        }

        validated = ClaudeSubAgentStartupInput.model_validate(valid_input)
        assert validated.agent_id == "agent-123"
        assert validated.agent_type == "explore"
        assert validated.hook_event_name == "SubAgentStartup"

    def test_transform_to_cpex(self):
        """Test transformation to CPEX AgentPreInvokePayload."""
        claude_input = ClaudeSubAgentStartupInput(
            hook_event_name="SubAgentStartup",
            session_id="test-session",
            transcript_path="/tmp/transcript.jsonl",
            cwd="/workspace",
            permission_mode="default",
            agent_id="agent-123",
            agent_type="explore"
        )

        cpex_payload = self.mapper._transform_to_cpex(claude_input)

        assert isinstance(cpex_payload, AgentPreInvokePayload)
        assert cpex_payload.agent_id == "agent-123"
        assert cpex_payload.messages == []
        assert cpex_payload.tools is None
        assert cpex_payload.parameters["agent_type"] == "explore"

    def test_transform_from_cpex_success(self):
        """Test transformation from CPEX result (success case)."""
        plugin_result = PluginResult(
            continue_processing=True,
            modified_payload=None,
            violation=None,
            metadata={"test": "data"}
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.continue_ is True
        assert claude_output.stop_reason is None
        assert claude_output.hookSpecificOutput is not None

    def test_transform_from_cpex_with_violation(self):
        """Test transformation from CPEX result with violation."""
        violation = PluginViolation(
            reason="Agent startup blocked",
            description="Security policy violation",
            code="AGENT_BLOCKED"
        )

        plugin_result = PluginResult(
            continue_processing=False,
            violation=violation,
            metadata={}
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.continue_ is False
        assert claude_output.stop_reason == "Agent startup blocked"


class TestSubAgentStopMapper:
    """Test suite for SubAgentStopMapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = SubAgentStopMapper()

    def test_input_validation_valid(self):
        """Test valid SubAgentStop input validation."""
        valid_input = {
            "hook_event_name": "SubAgentStop",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "stop_hook_active": True,
            "agent_id": "agent-123",
            "agent_type": "explore",
            "agent_transcript_path": "/tmp/agent_transcript.jsonl",
            "last_assistant_message": "Task completed successfully"
        }

        validated = ClaudeSubAgentStopInput.model_validate(valid_input)
        assert validated.agent_id == "agent-123"
        assert validated.last_assistant_message == "Task completed successfully"
        assert validated.stop_hook_active is True

    def test_transform_to_cpex(self):
        """Test transformation to CPEX AgentPostInvokePayload."""
        claude_input = ClaudeSubAgentStopInput(
            hook_event_name="SubAgentStop",
            session_id="test-session",
            transcript_path="/tmp/transcript.jsonl",
            cwd="/workspace",
            permission_mode="default",
            stop_hook_active=True,
            agent_id="agent-123",
            agent_type="explore",
            agent_transcript_path="/tmp/agent_transcript.jsonl",
            last_assistant_message="Final response from agent"
        )

        cpex_payload = self.mapper._transform_to_cpex(claude_input)

        assert isinstance(cpex_payload, AgentPostInvokePayload)
        assert cpex_payload.agent_id == "agent-123"
        assert len(cpex_payload.messages) == 1
        assert cpex_payload.messages[0].role == "assistant"
        assert cpex_payload.messages[0].content == "Final response from agent"

    def test_transform_from_cpex_allow_stop(self):
        """Test transformation when stop is allowed."""
        plugin_result = PluginResult(
            continue_processing=True,
            metadata={}
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.continue_ is True
        assert claude_output.decision is None
        assert claude_output.reason == ""

    def test_transform_from_cpex_block_stop(self):
        """Test transformation when stop is blocked."""
        violation = PluginViolation(
            reason="Stop blocked - agent needs more time",
            description="Agent stop was blocked by policy",
            code="STOP_BLOCKED"
        )

        plugin_result = PluginResult(
            continue_processing=False,
            violation=violation
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        # Check the actual attributes that exist
        continue_attr = getattr(claude_output, 'continue_', None)
        assert continue_attr is False
        assert claude_output.decision == "block"
        assert claude_output.reason == "Stop blocked - agent needs more time"


class TestPostToolUseFailureMapper:
    """Test suite for PostToolUseFailureMapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = PostToolUseFailureMapper()

    def test_input_validation_valid(self):
        """Test valid PostToolUseFailure input validation."""
        valid_input = {
            "hook_event_name": "PostToolUseFailure",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "tool_name": "file_read",
            "tool_input": {"path": "/nonexistent.txt"},
            "tool_response": {"error": "File not found"},
            "tool_use_id": "tool-123",
            "error": "FileNotFoundError: No such file or directory",
            "is_interrupt": False
        }

        validated = ClaudePostToolUseFailureInput.model_validate(valid_input)
        assert validated.tool_name == "file_read"
        assert validated.error == "FileNotFoundError: No such file or directory"
        assert validated.is_interrupt is False

    def test_input_validation_with_interrupt(self):
        """Test input validation with interrupt flag."""
        valid_input = {
            "hook_event_name": "PostToolUseFailure",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "tool_name": "long_running_task",
            "tool_input": {"timeout": 30},
            "tool_response": {"status": "interrupted"},
            "tool_use_id": "tool-456",
            "error": "Operation interrupted by user",
            "is_interrupt": True
        }

        validated = ClaudePostToolUseFailureInput.model_validate(valid_input)
        assert validated.is_interrupt is True

    def test_transform_to_cpex(self):
        """Test transformation to CPEX ToolPostInvokePayload."""
        claude_input = ClaudePostToolUseFailureInput(
            hook_event_name="PostToolUseFailure",
            session_id="test-session",
            transcript_path="/tmp/transcript.jsonl",
            cwd="/workspace",
            permission_mode="default",
            tool_name="file_write",
            tool_input={"path": "/readonly.txt", "content": "test"},
            tool_response={"error": "Permission denied"},
            tool_use_id="tool-789",
            error="PermissionError: Permission denied",
            is_interrupt=False
        )

        cpex_payload = self.mapper._transform_to_cpex(claude_input)

        assert isinstance(cpex_payload, ToolPostInvokePayload)
        assert cpex_payload.name == "file_write"
        assert cpex_payload.result["success"] is False
        assert cpex_payload.result["error"] == "PermissionError: Permission denied"
        assert cpex_payload.result["is_interrupt"] is False
        assert cpex_payload.result["tool_use_id"] == "tool-789"

    def test_transform_from_cpex(self):
        """Test transformation from CPEX result."""
        plugin_result = PluginResult(
            continue_processing=True,
            metadata={"logged": True}
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.continue_ is True
        assert claude_output.stop_reason is None
        assert claude_output.hookSpecificOutput is not None


class TestInstructionsLoadedMapper:
    """Test suite for InstructionsLoadedMapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = InstructionsLoadedMapper()

    def test_input_validation_valid(self):
        """Test valid InstructionsLoaded input validation."""
        valid_input = {
            "hook_event_name": "InstructionsLoaded",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "file_path": "/workspace/.claude/instructions.md",
            "memory_type": "Project",
            "load_reason": "session_start",
            "globs": "**/.claude/*.md",
            "trigger_file_path": "/workspace/main.py",
            "parent_file_path": "/workspace/.claude/context.md"
        }

        validated = ClaudeInstructionsLoaded.model_validate(valid_input)
        assert validated.file_path == "/workspace/.claude/instructions.md"
        assert validated.memory_type == "Project"
        assert validated.load_reason == "session_start"

    def test_input_validation_minimal(self):
        """Test input validation with minimal required fields."""
        minimal_input = {
            "hook_event_name": "InstructionsLoaded",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "file_path": "/home/user/.claude/global.md",
            "memory_type": "User",
            "load_reason": "include",
            "globs": "",
            "trigger_file_path": "",
            "parent_file_path": ""
        }

        validated = ClaudeInstructionsLoaded.model_validate(minimal_input)
        assert validated.memory_type == "User"
        assert validated.globs == ""

    def test_transform_to_cpex(self):
        """Test transformation to CPEX InstructionsLoadedPayload."""
        claude_input = ClaudeInstructionsLoaded(
            hook_event_name="InstructionsLoaded",
            session_id="test-session",
            transcript_path="/tmp/transcript.jsonl",
            cwd="/workspace",
            permission_mode="default",
            file_path="/workspace/.claude/security.md",
            memory_type="Local",
            load_reason="nested_traversal",
            globs="*.md",
            trigger_file_path="/workspace/src/auth.py",
            parent_file_path="/workspace/.claude/main.md"
        )

        cpex_payload = self.mapper._transform_to_cpex(claude_input)

        assert isinstance(cpex_payload, InstructionsLoadedPayload)
        assert cpex_payload.file_path == "/workspace/.claude/security.md"
        assert cpex_payload.memory_type == "Local"
        assert cpex_payload.load_reason == "nested_traversal"
        assert cpex_payload.globs == "*.md"
        assert cpex_payload.trigger_file_path == "/workspace/src/auth.py"

    def test_transform_from_cpex_audit_only(self):
        """Test transformation - InstructionsLoaded is audit-only."""
        # Even with violations, InstructionsLoaded hooks can't block
        violation = PluginViolation(
            reason="Suspicious content detected",
            description="Audit alert for instruction content",
            code="AUDIT_ALERT"
        )

        plugin_result = PluginResult(
            continue_processing=False,  # This is ignored for audit-only hooks
            violation=violation
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        # InstructionsLoaded hooks always continue (audit-only)
        continue_attr = getattr(claude_output, 'continue_', None)
        assert continue_attr is True
        assert claude_output.stop_reason is None


class TestPermissionRequestMapper:
    """Test suite for PermissionRequestMapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = PermissionRequestMapper()

    def test_input_validation_valid(self):
        """Test valid PermissionRequest input validation."""
        valid_input = {
            "hook_event_name": "PermissionRequest",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "tool_name": "file_read",
            "tool_input": {"path": "/etc/passwd"},
            "permission_suggestions": {"recommended": "deny", "reason": "sensitive file"}
        }

        validated = ClaudePermissionRequestInput.model_validate(valid_input)
        assert validated.tool_name == "file_read"
        assert validated.tool_input["path"] == "/etc/passwd"
        assert validated.permission_suggestions["recommended"] == "deny"

    def test_input_validation_without_suggestions(self):
        """Test input validation without permission suggestions."""
        valid_input = {
            "hook_event_name": "PermissionRequest",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "dontAsk",
            "tool_name": "echo",
            "tool_input": {"message": "hello"}
        }

        validated = ClaudePermissionRequestInput.model_validate(valid_input)
        assert validated.permission_suggestions is None

    def test_transform_to_cpex(self):
        """Test transformation to CPEX PermissionRequestPayload."""
        claude_input = ClaudePermissionRequestInput(
            hook_event_name="PermissionRequest",
            session_id="test-session",
            transcript_path="/tmp/transcript.jsonl",
            cwd="/workspace",
            permission_mode="plan",
            tool_name="bash",
            tool_input={"command": "rm important_file.txt"},
            permission_suggestions={"risk_level": "high"}
        )

        cpex_payload = self.mapper._transform_to_cpex(claude_input)

        assert isinstance(cpex_payload, PermissionRequestPayload)
        assert cpex_payload.tool_name == "bash"
        assert cpex_payload.tool_input["command"] == "rm important_file.txt"
        assert cpex_payload.permission_suggestions["risk_level"] == "high"
        assert cpex_payload.session_id == "test-session"
        assert cpex_payload.permission_mode == "plan"

    def test_transform_from_cpex_allow(self):
        """Test transformation when permission is granted."""
        plugin_result = PluginResult(
            continue_processing=True,
            metadata={}
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.continue_ is True
        assert claude_output.hookSpecificOutput.behavior == "allow"
        assert claude_output.hookSpecificOutput.interrupt is False

    def test_transform_from_cpex_deny(self):
        """Test transformation when permission is denied."""
        violation = PluginViolation(
            reason="Dangerous operation not allowed",
            description="Operation was denied by security policy",
            code="OPERATION_DENIED"
        )

        plugin_result = PluginResult(
            continue_processing=False,
            violation=violation
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.continue_ is False
        hook_output = claude_output.hookSpecificOutput
        assert hook_output.behavior == "deny"
        assert hook_output.message == "Dangerous operation not allowed"
        assert hook_output.interrupt is True

    def test_transform_from_cpex_with_modified_input(self):
        """Test transformation with modified tool input."""
        from cpex.tools.schemas.claude_code_improved import PermissionRequestPayload as ModifiedPayload
        modified_payload = PermissionRequestPayload(
            tool_name="file_read",
            tool_input={"path": "/safe/file.txt"},  # Modified path
            session_id="test",
            cwd="/workspace",
            permission_mode="default"
        )

        plugin_result = PluginResult(
            continue_processing=True,
            modified_payload=modified_payload
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.hookSpecificOutput.updatedInput == {"path": "/safe/file.txt"}


class TestPermissionUpdateMapper:
    """Test suite for PermissionUpdateMapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = PermissionUpdateMapper()

    def test_input_validation_valid(self):
        """Test valid PermissionUpdate input validation."""
        valid_input = {
            "hook_event_name": "PermissionUpdate",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "tool_name": "file_write",
            "tool_input": {"path": "output.txt", "content": "test"},
            "permission_decision": "allow",
            "permission_decision_reason": "Safe file operation"
        }

        validated = ClaudePermissionUpdateInput.model_validate(valid_input)
        assert validated.tool_name == "file_write"
        assert validated.permission_decision == "allow"
        assert validated.permission_decision_reason == "Safe file operation"

    def test_input_validation_denial(self):
        """Test input validation for permission denial."""
        valid_input = {
            "hook_event_name": "PermissionUpdate",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "tool_name": "system_shutdown",
            "tool_input": {"force": True},
            "permission_decision": "deny",
            "permission_decision_reason": "Too dangerous"
        }

        validated = ClaudePermissionUpdateInput.model_validate(valid_input)
        assert validated.permission_decision == "deny"
        assert validated.permission_decision_reason == "Too dangerous"

    def test_transform_to_cpex(self):
        """Test transformation to CPEX PermissionUpdatePayload."""
        claude_input = ClaudePermissionUpdateInput(
            hook_event_name="PermissionUpdate",
            session_id="test-session",
            transcript_path="/tmp/transcript.jsonl",
            cwd="/workspace",
            permission_mode="acceptEdits",
            tool_name="git_commit",
            tool_input={"message": "Add new feature", "files": ["src/feature.py"]},
            permission_decision="allow",
            permission_decision_reason="Code review passed"
        )

        cpex_payload = self.mapper._transform_to_cpex(claude_input)

        assert isinstance(cpex_payload, PermissionUpdatePayload)
        assert cpex_payload.tool_name == "git_commit"
        assert cpex_payload.permission_decision == "allow"
        assert cpex_payload.permission_decision_reason == "Code review passed"
        assert cpex_payload.permission_mode == "acceptEdits"

    def test_transform_from_cpex_audit(self):
        """Test transformation - PermissionUpdate is primarily audit-only."""
        plugin_result = PluginResult(
            continue_processing=True,
            metadata={"audit_logged": True}
        )

        claude_output = self.mapper._transform_from_cpex(plugin_result)

        assert claude_output.continue_ is True
        assert claude_output.hookSpecificOutput.behavior == "allow"


class TestImprovedClaudeCodeSchemaMapperIntegration:
    """Integration tests for the improved schema mapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = ImprovedClaudeCodeSchemaMapper()

    def test_all_new_mappers_registered(self):
        """Test that all new mappers are registered."""
        supported_hooks = self.mapper.get_supported_hooks()

        expected_new_hooks = [
            "SubAgentStartup",
            "SubAgentStop",
            "PostToolUseFailure",
            "InstructionsLoaded",
            "PermissionRequest",
            "PermissionUpdate"
        ]

        for hook in expected_new_hooks:
            assert hook in supported_hooks, f"Hook {hook} not found in supported hooks"

    def test_total_hook_count(self):
        """Test that we have the expected total number of hooks."""
        supported_hooks = self.mapper.get_supported_hooks()
        # Original 3 + all Claude Code hooks implemented = 23 total
        assert len(supported_hooks) == 23

    def test_roundtrip_subagent_startup(self):
        """Test roundtrip conversion for SubAgentStartup."""
        claude_payload = {
            "hook_event_name": "SubAgentStartup",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "agent_id": "agent-456",
            "agent_type": "plan"
        }

        # Claude -> CPEX
        cpex_payload = self.mapper.map_to_hook_payload(claude_payload)
        assert isinstance(cpex_payload, AgentPreInvokePayload)
        assert cpex_payload.agent_id == "agent-456"

        # Simulate plugin processing
        plugin_result = PluginResult(continue_processing=True, metadata={})

        # CPEX -> Claude
        claude_result = self.mapper.map_from_hook_result(plugin_result, "SubAgentStartup")
        # Check that the result contains the expected fields (result is a dict)
        # The model_dump() uses aliases, so it should be "_continue"
        assert claude_result.get("_continue") is True or claude_result.get("continue_") is True

    def test_roundtrip_permission_request_with_blocking(self):
        """Test roundtrip for PermissionRequest with blocking."""
        claude_payload = {
            "hook_event_name": "PermissionRequest",
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "tool_name": "rm",
            "tool_input": {"path": "/important/data"},
            "permission_suggestions": {"risk": "critical"}
        }

        # Convert to CPEX
        cpex_payload = self.mapper.map_to_hook_payload(claude_payload)
        assert isinstance(cpex_payload, PermissionRequestPayload)

        # Simulate blocking
        violation = PluginViolation(
            reason="Critical path blocked",
            description="Critical path access denied",
            code="PATH_BLOCKED"
        )
        plugin_result = PluginResult(continue_processing=False, violation=violation)

        # Convert back to Claude
        claude_result = self.mapper.map_from_hook_result(plugin_result, "PermissionRequest")
        # Check the result format (it's a dict from model_dump)
        # The field is _continue and should be False for blocking
        assert claude_result["_continue"] is False
        hook_output = claude_result["hookSpecificOutput"]
        assert hook_output["behavior"] == "deny"

    def test_error_handling_unsupported_hook(self):
        """Test error handling for unsupported hook types."""
        # This will fail validation before reaching the mapper
        claude_payload = {
            "hook_event_name": "UnsupportedHook",
            "session_id": "test"
        }

        with pytest.raises(ValueError) as exc_info:
            self.mapper.map_to_hook_payload(claude_payload)

        # The error should be about validation, not unsupported hook type
        assert "validation error" in str(exc_info.value).lower()

    def test_validation_failure_handling(self):
        """Test handling of validation failures."""
        invalid_payload = {
            "hook_event_name": "SubAgentStartup",
            "session_id": "test",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/workspace",
            "permission_mode": "default",
            "agent_id": "agent-123",
            # Missing required agent_type - this will cause validation failure
        }

        with pytest.raises(ValueError) as exc_info:
            self.mapper.map_to_hook_payload(invalid_payload)

        # Check that we get a validation error
        assert "validation error" in str(exc_info.value).lower()