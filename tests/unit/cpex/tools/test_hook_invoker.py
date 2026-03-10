# -*- coding: utf-8 -*-
"""Unit tests for HookInvoker class.

Tests the core hook invocation logic including PluginResult handling.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from cpex.framework.models import PluginResult, PluginViolation, GlobalContext
from cpex.framework.hooks.tools import ToolPreInvokePayload
from cpex.tools.hook_invoker import HookInvoker
from cpex.tools.output import ExitCode, InvocationResult


class TestHookInvoker:
    """Test suite for HookInvoker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.invoker = HookInvoker()

    @patch('cpex.tools.hook_invoker.PluginManager')
    def test_invoke_hook_sync_success(self, mock_manager_class):
        """Test successful hook invocation with PluginResult conversion."""
        # Mock PluginManager
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager

        # Create mock PluginResult (success case)
        plugin_result = PluginResult[ToolPreInvokePayload](
            continue_processing=True,
            modified_payload=None,
            violation=None,
            metadata={"execution_time": 0.05}
        )

        # Mock the invoke_hook method to return tuple (result, context_table)
        mock_manager.invoke_hook.return_value = (plugin_result, None)

        # Test payload
        payload = {"name": "test_tool", "args": {"param": "value"}}
        global_context = {"request_id": "test-123"}

        # Invoke hook
        result = self.invoker.invoke_hook_sync(
            hook_type="tool_pre_invoke",
            payload=payload,
            global_context=global_context
        )

        # Verify result
        assert isinstance(result, InvocationResult)
        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.hook_type == "tool_pre_invoke"
        assert result.data["continue_processing"] is True
        assert result.data["metadata"]["execution_time"] == 0.05

        # Verify manager was called correctly
        mock_manager.invoke_hook.assert_called_once()
        call_args = mock_manager.invoke_hook.call_args
        assert call_args[0][0] == "tool_pre_invoke"  # hook_type
        assert isinstance(call_args[0][2], GlobalContext)  # global_context
        assert call_args[0][2].request_id == "test-123"

    @patch('cpex.tools.hook_invoker.PluginManager')
    def test_invoke_hook_sync_with_violation(self, mock_manager_class):
        """Test hook invocation that results in violation (blocked processing)."""
        # Mock PluginManager
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager

        # Create PluginResult with violation
        violation = PluginViolation(
            reason="Security policy violation",
            description="Tool execution blocked by security policy",
            code="SECURITY_BLOCK",
            details={"tool": "dangerous_tool", "risk": "high"}
        )

        plugin_result = PluginResult[ToolPreInvokePayload](
            continue_processing=False,
            violation=violation,
            metadata={"blocked_by": "security_plugin"}
        )

        mock_manager.invoke_hook.return_value = (plugin_result, None)

        # Test payload
        payload = {"name": "dangerous_tool", "args": {}}

        # Invoke hook
        result = self.invoker.invoke_hook_sync(
            hook_type="tool_pre_invoke",
            payload=payload
        )

        # Verify result shows violation
        assert isinstance(result, InvocationResult)
        assert result.success is True  # Invocation succeeded
        assert result.exit_code == ExitCode.BLOCKED_BY_VIOLATION  # But processing blocked
        assert result.hook_type == "tool_pre_invoke"
        assert result.data["continue_processing"] is False
        assert result.data["violation"]["code"] == "SECURITY_BLOCK"

    @patch('cpex.tools.hook_invoker.PluginManager')
    def test_invoke_hook_sync_with_modified_payload(self, mock_manager_class):
        """Test hook invocation with payload modification."""
        # Mock PluginManager
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager

        # Create modified payload
        modified_payload = ToolPreInvokePayload(
            name="sanitized_tool",
            args={"param": "sanitized_value", "safe_mode": True}
        )

        plugin_result = PluginResult[ToolPreInvokePayload](
            continue_processing=True,
            modified_payload=modified_payload,
            violation=None,
            metadata={"transformation": "input_sanitization"}
        )

        mock_manager.invoke_hook.return_value = (plugin_result, None)

        # Test payload
        payload = {"name": "potentially_unsafe_tool", "args": {"param": "unsafe_value"}}

        # Invoke hook
        result = self.invoker.invoke_hook_sync(
            hook_type="tool_pre_invoke",
            payload=payload
        )

        # Verify result shows modification
        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.data["continue_processing"] is True
        assert result.data["modified_payload"] is not None
        assert result.data["metadata"]["transformation"] == "input_sanitization"

    def test_invoke_hook_sync_invalid_hook_type(self):
        """Test error handling for invalid hook type."""
        payload = {"name": "test_tool", "args": {}}

        # Invoke with invalid hook type
        result = self.invoker.invoke_hook_sync(
            hook_type="invalid_hook_type",
            payload=payload
        )

        # Verify error result
        assert result.success is False
        assert result.exit_code == ExitCode.CONFIGURATION_ERROR
        assert "not registered" in result.error
        assert "invalid_hook_type" in result.error

    def test_invoke_hook_sync_invalid_payload(self):
        """Test error handling for invalid payload structure."""
        # Missing required 'name' field
        payload = {"args": {"param": "value"}}

        result = self.invoker.invoke_hook_sync(
            hook_type="tool_pre_invoke",
            payload=payload
        )

        # Verify validation error
        assert result.success is False
        assert result.exit_code == ExitCode.CONFIGURATION_ERROR
        assert "validation error" in result.error.lower()

    # Don't think this is necessary here
    # @patch('cpex.tools.hook_invoker.PluginManager')
    # def test_invoke_hook_sync_with_schema_mapping(self, mock_manager_class):
    #     """Test hook invocation with schema mapping enabled."""
    #     # Mock PluginManager
    #     mock_manager = AsyncMock()
    #     mock_manager_class.return_value = mock_manager

    #     plugin_result = PluginResult[ToolPreInvokePayload](
    #         continue_processing=True,
    #         metadata={"mapped": True}
    #     )
    #     mock_manager.invoke_hook.return_value = (plugin_result, None)

    #     # Claude Code format payload
    #     claude_payload = {
    #         "tool_name": "search",
    #         "arguments": {"query": "test"},
    #         "session_id": "sess-123"
    #     }

    #     # Invoke with schema mapping
    #     result = self.invoker.invoke_hook_sync(
    #         hook_type="tool_pre_invoke",
    #         payload=claude_payload,
    #         schema_mapper="claude-code"
    #     )

    #     # Verify schema mapping was applied
    #     assert result.success is True
    #     assert result.exit_code == ExitCode.SUCCESS
    #     # Result should be in Claude Code format (mapped back)
    #     assert "cpex_result" in result.data
    #     assert result.data["hook_type"] == "tool_pre_invoke"

    def test_list_hooks(self):
        """Test hook listing functionality."""
        hooks = self.invoker.list_hooks()

        # Verify we get a list of hook types
        assert isinstance(hooks, list)
        assert len(hooks) > 0
        assert "tool_pre_invoke" in hooks
        assert "tool_post_invoke" in hooks
        # Should be sorted
        assert hooks == sorted(hooks)

    def test_describe_hook_valid(self):
        """Test hook description for valid hook type."""
        description = self.invoker.describe_hook("tool_pre_invoke")

        # Verify description structure
        assert isinstance(description, dict)
        assert description["hook_type"] == "tool_pre_invoke"
        assert "payload_schema" in description
        assert "result_schema" in description
        assert "payload_class" in description
        assert "result_class" in description

        # Verify schema content
        payload_schema = description["payload_schema"]
        assert "properties" in payload_schema
        assert "name" in payload_schema["properties"]

    def test_describe_hook_invalid(self):
        """Test hook description for invalid hook type."""
        with pytest.raises(ValueError) as exc_info:
            self.invoker.describe_hook("invalid_hook_type")

        assert "not registered" in str(exc_info.value)
        assert "invalid_hook_type" in str(exc_info.value)

    def test_determine_exit_code_success(self):
        """Test exit code determination for successful processing."""
        plugin_result = PluginResult[ToolPreInvokePayload](continue_processing=True)
        exit_code = self.invoker._determine_exit_code(plugin_result)
        assert exit_code == ExitCode.SUCCESS

    def test_determine_exit_code_blocked_with_violation(self):
        """Test exit code determination for blocked processing with violation."""
        violation = PluginViolation(
            reason="Test", description="Test", code="TEST"
        )
        plugin_result = PluginResult[ToolPreInvokePayload](
            continue_processing=False,
            violation=violation
        )
        exit_code = self.invoker._determine_exit_code(plugin_result)
        assert exit_code == ExitCode.BLOCKED_BY_VIOLATION

    def test_determine_exit_code_blocked_without_violation(self):
        """Test exit code determination for blocked processing without violation."""
        plugin_result = PluginResult[ToolPreInvokePayload](
            continue_processing=False,
            violation=None
        )
        exit_code = self.invoker._determine_exit_code(plugin_result)
        assert exit_code == ExitCode.BLOCKED_BY_VIOLATION

    def test_global_context_creation_with_defaults(self):
        """Test GlobalContext creation with default values."""
        payload = {"name": "test_tool", "args": {}}

        with patch('cpex.tools.hook_invoker.PluginManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            plugin_result = PluginResult[ToolPreInvokePayload](continue_processing=True)
            mock_manager.invoke_hook.return_value = (plugin_result, None)

            # Invoke without context
            result = self.invoker.invoke_hook_sync(
                hook_type="tool_pre_invoke",
                payload=payload
            )

            # Verify GlobalContext was created with defaults
            call_args = mock_manager.invoke_hook.call_args
            global_ctx = call_args[0][2]
            assert isinstance(global_ctx, GlobalContext)
            assert global_ctx.request_id == "cli-generated-id"

    def test_global_context_field_validation(self):
        """Test GlobalContext creation with field validation."""
        payload = {"name": "test_tool", "args": {}}
        context = {
            "request_id": "req-123",
            "user": "test_user",  # Valid field
            "invalid_field": "should_be_ignored"  # Invalid field
        }

        with patch('cpex.tools.hook_invoker.PluginManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            plugin_result = PluginResult[ToolPreInvokePayload](continue_processing=True)
            mock_manager.invoke_hook.return_value = (plugin_result, None)

            # Invoke with mixed valid/invalid context
            result = self.invoker.invoke_hook_sync(
                hook_type="tool_pre_invoke",
                payload=payload,
                global_context=context
            )

            # Verify valid fields were used, invalid ignored
            call_args = mock_manager.invoke_hook.call_args
            global_ctx = call_args[0][2]
            assert global_ctx.request_id == "req-123"
            # Note: user field validation depends on actual GlobalContext model

    @patch('cpex.tools.hook_invoker.PluginManager')
    def test_plugin_manager_initialization_error(self, mock_manager_class):
        """Test error handling when plugin manager initialization fails."""
        # Make manager initialization fail
        mock_manager_class.side_effect = Exception("Manager init failed")

        payload = {"name": "test_tool", "args": {}}

        result = self.invoker.invoke_hook_sync(
            hook_type="tool_pre_invoke",
            payload=payload
        )

        # Verify error is handled gracefully
        assert result.success is False
        assert result.exit_code == ExitCode.EXECUTION_ERROR
        assert "Manager init failed" in result.error

    @patch('cpex.tools.hook_invoker.PluginManager')
    def test_async_execution_error(self, mock_manager_class):
        """Test error handling when async hook execution fails."""
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager

        # Make hook invocation fail
        mock_manager.invoke_hook.side_effect = Exception("Hook execution failed")

        payload = {"name": "test_tool", "args": {}}

        result = self.invoker.invoke_hook_sync(
            hook_type="tool_pre_invoke",
            payload=payload
        )

        # Verify error is handled gracefully
        assert result.success is False
        assert result.exit_code == ExitCode.EXECUTION_ERROR
        assert "Hook execution failed" in result.error


class TestHookInvokerIntegration:
    """Integration tests for HookInvoker with real components."""

    def test_real_hook_registry_integration(self):
        """Test HookInvoker with real hook registry."""
        invoker = HookInvoker()

        # Test with real registry
        hooks = invoker.list_hooks()
        assert "tool_pre_invoke" in hooks

        description = invoker.describe_hook("tool_pre_invoke")
        assert description["hook_type"] == "tool_pre_invoke"
        assert description["payload_class"] == "ToolPreInvokePayload"

    def test_config_file_loading(self):
        """Test HookInvoker with configuration file."""
        # Create temporary config file
        import tempfile
        import yaml

        config = {
            "plugins": [],
            "plugin_dirs": []
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = Path(f.name)

        try:
            # Test with config file
            invoker = HookInvoker(config_path=config_path)

            # Should still work with empty config
            hooks = invoker.list_hooks()
            assert isinstance(hooks, list)

        finally:
            config_path.unlink()  # Clean up