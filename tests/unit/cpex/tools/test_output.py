# -*- coding: utf-8 -*-
"""Unit tests for output formatting utilities.

Tests the InvocationResult and output formatting functions.
"""

import json
import pytest
from dataclasses import asdict

from cpex.tools.output import (
    ExitCode,
    InvocationResult,
    format_output,
    format_error,
    format_success
)


class TestExitCode:
    """Test suite for ExitCode enum."""

    def test_exit_code_values(self):
        """Test that exit codes have expected Unix-compatible values."""
        assert ExitCode.SUCCESS.value == 0
        assert ExitCode.EXECUTION_ERROR.value == 1
        assert ExitCode.BLOCKED_BY_VIOLATION.value == 2
        assert ExitCode.CONFIGURATION_ERROR.value == 3

    def test_exit_code_string_representation(self):
        """Test string representation of exit codes."""
        assert str(ExitCode.SUCCESS) == "ExitCode.SUCCESS"
        assert ExitCode.SUCCESS.name == "SUCCESS"

    def test_exit_code_comparison(self):
        """Test exit code comparison operations."""
        assert ExitCode.SUCCESS != ExitCode.EXECUTION_ERROR
        assert ExitCode.SUCCESS == ExitCode.SUCCESS
        assert ExitCode.BLOCKED_BY_VIOLATION.value > ExitCode.SUCCESS.value


class TestInvocationResult:
    """Test suite for InvocationResult dataclass."""

    def test_invocation_result_creation_success(self):
        """Test creation of successful InvocationResult."""
        data = {"continue_processing": True, "metadata": {"test": "value"}}
        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_pre_invoke",
            data=data
        )

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.hook_type == "tool_pre_invoke"
        assert result.data == data
        assert result.error is None
        assert result.metadata is None

    def test_invocation_result_creation_error(self):
        """Test creation of error InvocationResult."""
        result = InvocationResult(
            success=False,
            exit_code=ExitCode.EXECUTION_ERROR,
            hook_type="tool_pre_invoke",
            error="Something went wrong"
        )

        assert result.success is False
        assert result.exit_code == ExitCode.EXECUTION_ERROR
        assert result.hook_type == "tool_pre_invoke"
        assert result.error == "Something went wrong"
        assert result.data is None
        assert result.metadata is None

    def test_invocation_result_with_metadata(self):
        """Test InvocationResult with metadata."""
        metadata = {"processing_time": 0.123, "plugin_count": 3}
        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_post_invoke",
            metadata=metadata
        )

        assert result.metadata == metadata

    def test_to_dict_success_case(self):
        """Test conversion to dictionary for success case."""
        data = {"continue_processing": True, "modified_payload": None}
        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_pre_invoke",
            data=data
        )

        result_dict = result.to_dict()

        expected = {
            "success": True,
            "exit_code": 0,
            "hook_type": "tool_pre_invoke",
            "data": data
        }

        assert result_dict == expected

    def test_to_dict_error_case(self):
        """Test conversion to dictionary for error case."""
        result = InvocationResult(
            success=False,
            exit_code=ExitCode.CONFIGURATION_ERROR,
            hook_type="tool_pre_invoke",
            error="Invalid payload format"
        )

        result_dict = result.to_dict()

        expected = {
            "success": False,
            "exit_code": 3,
            "hook_type": "tool_pre_invoke",
            "error": "Invalid payload format"
        }

        assert result_dict == expected

    def test_to_dict_with_all_fields(self):
        """Test conversion to dictionary with all fields present."""
        data = {"result": "processed"}
        metadata = {"plugin": "test_plugin"}
        result = InvocationResult(
            success=True,
            exit_code=ExitCode.BLOCKED_BY_VIOLATION,
            hook_type="tool_post_invoke",
            data=data,
            error="Warning message",
            metadata=metadata
        )

        result_dict = result.to_dict()

        expected = {
            "success": True,
            "exit_code": 2,
            "hook_type": "tool_post_invoke",
            "data": data,
            "error": "Warning message",
            "metadata": metadata
        }

        assert result_dict == expected

    def test_to_dict_with_none_values(self):
        """Test that None values are excluded from dictionary."""
        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_pre_invoke",
            data=None,
            error=None,
            metadata=None
        )

        result_dict = result.to_dict()

        # Only non-None required fields should be present
        expected = {
            "success": True,
            "exit_code": 0,
            "hook_type": "tool_pre_invoke"
        }

        assert result_dict == expected


class TestFormatOutput:
    """Test suite for format_output function."""

    def test_format_output_pretty_success(self):
        """Test pretty formatting of successful result."""
        data = {"continue_processing": True, "metadata": {"test": True}}
        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_pre_invoke",
            data=data
        )

        output = format_output(result, pretty=True)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["success"] is True
        assert parsed["exit_code"] == 0
        assert parsed["data"]["continue_processing"] is True

        # Should be pretty-printed (contains newlines and indentation)
        assert "\n" in output
        assert "  " in output

    def test_format_output_compact(self):
        """Test compact formatting."""
        result = InvocationResult(
            success=False,
            exit_code=ExitCode.EXECUTION_ERROR,
            hook_type="tool_pre_invoke",
            error="Test error"
        )

        output = format_output(result, pretty=False)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["success"] is False
        assert parsed["error"] == "Test error"

        # Should be compact (no unnecessary whitespace)
        assert "\n" not in output
        assert "  " not in output

    def test_format_output_unicode_handling(self):
        """Test proper handling of Unicode characters."""
        data = {"message": "Test with émojis 🎉 and 中文"}
        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_pre_invoke",
            data=data
        )

        output = format_output(result, pretty=True)

        # Should preserve Unicode characters (ensure_ascii=False)
        assert "émojis 🎉 and 中文" in output

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["data"]["message"] == "Test with émojis 🎉 and 中文"

    def test_format_output_complex_data(self):
        """Test formatting with complex nested data structures."""
        complex_data = {
            "results": [
                {"id": 1, "status": "success", "details": {"time": 0.1}},
                {"id": 2, "status": "failed", "details": {"error": "timeout"}}
            ],
            "summary": {
                "total": 2,
                "successful": 1,
                "failed": 1,
                "metadata": {"version": "1.0", "nested": {"deep": {"value": 42}}}
            }
        }

        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_post_invoke",
            data=complex_data
        )

        output = format_output(result)

        # Should be valid JSON
        parsed = json.loads(output)
        assert len(parsed["data"]["results"]) == 2
        assert parsed["data"]["summary"]["metadata"]["nested"]["deep"]["value"] == 42


class TestFormatError:
    """Test suite for format_error function."""

    def test_format_error_basic(self):
        """Test basic error formatting."""
        output = format_error(
            message="Hook execution failed",
            exit_code=ExitCode.EXECUTION_ERROR,
            hook_type="tool_pre_invoke"
        )

        parsed = json.loads(output)
        assert parsed["success"] is False
        assert parsed["exit_code"] == 1
        assert parsed["hook_type"] == "tool_pre_invoke"
        assert parsed["error"] == "Hook execution failed"

    def test_format_error_default_values(self):
        """Test error formatting with default values."""
        output = format_error("Simple error message")

        parsed = json.loads(output)
        assert parsed["success"] is False
        assert parsed["exit_code"] == 1  # Default EXECUTION_ERROR
        assert parsed["hook_type"] == "unknown"  # Default hook type
        assert parsed["error"] == "Simple error message"

    def test_format_error_configuration_error(self):
        """Test error formatting for configuration errors."""
        output = format_error(
            message="Invalid configuration file",
            exit_code=ExitCode.CONFIGURATION_ERROR,
            hook_type="config_validation"
        )

        parsed = json.loads(output)
        assert parsed["exit_code"] == 3
        assert parsed["error"] == "Invalid configuration file"
        assert parsed["hook_type"] == "config_validation"

    def test_format_error_compact_mode(self):
        """Test error formatting in compact mode."""
        output = format_error(
            message="Compact error",
            pretty=False
        )

        # Should be compact
        assert "\n" not in output

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["error"] == "Compact error"


class TestFormatSuccess:
    """Test suite for format_success function."""

    def test_format_success_basic(self):
        """Test basic success formatting."""
        data = {"continue_processing": True, "modified_payload": None}
        output = format_success(
            data=data,
            hook_type="tool_pre_invoke"
        )

        parsed = json.loads(output)
        assert parsed["success"] is True
        assert parsed["exit_code"] == 0
        assert parsed["hook_type"] == "tool_pre_invoke"
        assert parsed["data"] == data

    def test_format_success_with_metadata(self):
        """Test success formatting with metadata."""
        data = {"result": "processed"}
        metadata = {"processing_time": 0.245, "plugins_executed": 2}

        output = format_success(
            data=data,
            hook_type="tool_post_invoke",
            metadata=metadata
        )

        parsed = json.loads(output)
        assert parsed["success"] is True
        assert parsed["data"] == data
        assert parsed["metadata"] == metadata

    def test_format_success_blocked_by_violation(self):
        """Test success formatting with violation exit code."""
        data = {"continue_processing": False, "violation": {"code": "BLOCKED"}}

        output = format_success(
            data=data,
            hook_type="tool_pre_invoke",
            exit_code=ExitCode.BLOCKED_BY_VIOLATION
        )

        parsed = json.loads(output)
        assert parsed["success"] is True  # Execution succeeded
        assert parsed["exit_code"] == 2    # But processing was blocked
        assert parsed["data"]["continue_processing"] is False

    def test_format_success_compact_mode(self):
        """Test success formatting in compact mode."""
        data = {"simple": "result"}

        output = format_success(
            data=data,
            hook_type="test_hook",
            pretty=False
        )

        # Should be compact
        assert "\n" not in output

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["data"] == data


class TestOutputFormattingIntegration:
    """Integration tests for output formatting functions."""

    def test_roundtrip_formatting(self):
        """Test that formatted output can be parsed back correctly."""
        # Create complex result
        complex_data = {
            "continue_processing": True,
            "modified_payload": {
                "name": "transformed_tool",
                "args": {"sanitized": True}
            },
            "violation": None,
            "metadata": {
                "transformations": ["sanitization", "validation"],
                "execution_stats": {
                    "duration": 0.123,
                    "memory_usage": "45MB"
                }
            }
        }

        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="tool_pre_invoke",
            data=complex_data,
            metadata={"cli_version": "1.0.0"}
        )

        # Format and parse back
        formatted = format_output(result)
        parsed = json.loads(formatted)

        # Verify all data is preserved
        assert parsed["success"] == result.success
        assert parsed["exit_code"] == result.exit_code.value
        assert parsed["hook_type"] == result.hook_type
        assert parsed["data"]["modified_payload"]["name"] == "transformed_tool"
        assert parsed["metadata"]["cli_version"] == "1.0.0"

    def test_error_vs_success_format_consistency(self):
        """Test that error and success formatting have consistent structure."""
        # Format error
        error_output = format_error(
            message="Test error",
            exit_code=ExitCode.EXECUTION_ERROR,
            hook_type="test_hook"
        )
        error_parsed = json.loads(error_output)

        # Format success
        success_output = format_success(
            data={"result": "ok"},
            hook_type="test_hook"
        )
        success_parsed = json.loads(success_output)

        # Both should have consistent base structure
        for parsed in [error_parsed, success_parsed]:
            assert "success" in parsed
            assert "exit_code" in parsed
            assert "hook_type" in parsed
            assert isinstance(parsed["success"], bool)
            assert isinstance(parsed["exit_code"], int)
            assert isinstance(parsed["hook_type"], str)

    def test_large_output_handling(self):
        """Test formatting of large data structures."""
        # Create large data structure
        large_data = {
            "items": [{"id": i, "data": f"item_{i}"} for i in range(1000)],
            "metadata": {
                f"key_{i}": f"value_{i}" for i in range(100)
            }
        }

        result = InvocationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            hook_type="bulk_operation",
            data=large_data
        )

        # Should handle large data without issues
        output = format_output(result)
        parsed = json.loads(output)

        assert len(parsed["data"]["items"]) == 1000
        assert len(parsed["data"]["metadata"]) == 100
        assert parsed["data"]["items"][999]["id"] == 999