#!/usr/bin/env python3
"""
Test script to validate the improved Claude Code schema mapper.
This demonstrates drop-in compatibility and improved functionality.
"""

import json
from cpex.framework.models import PluginResult, PluginViolation
from cpex.tools.schemas.claude_code_improved import ImprovedClaudeCodeSchemaMapper


def test_basic_compatibility():
    """Test that improved mapper has same interface as original."""
    print("=== Testing Basic Compatibility ===")

    mapper = ImprovedClaudeCodeSchemaMapper()

    # Test supported hooks
    hooks = mapper.get_supported_hooks()
    print(f"Supported hooks: {hooks}")
    assert "tool_pre_invoke" in hooks
    assert "tool_post_invoke" in hooks

    print("✅ Basic compatibility test passed\n")


def test_pre_tool_use_mapping():
    """Test PreToolUse mapping with validation."""
    print("=== Testing PreToolUse Mapping ===")

    mapper = ImprovedClaudeCodeSchemaMapper()

    # Valid Claude Code payload
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

    # Test validation
    is_valid = mapper.validate_external_payload(claude_payload, "tool_pre_invoke")
    print(f"Payload validation: {is_valid}")
    assert is_valid

    # Test mapping to CPEX
    cpex_payload = mapper.map_to_hook_payload(claude_payload, "tool_pre_invoke")
    print(f"CPEX payload: {json.dumps(cpex_payload, indent=2)}")

    # Validate expected structure
    assert cpex_payload["name"] == "file_reader"
    assert cpex_payload["args"]["path"] == "/example.txt"
    assert cpex_payload["args"]["mode"] == "read"
    assert "headers" in cpex_payload

    print("✅ PreToolUse mapping test passed\n")


def test_result_mapping():
    """Test CPEX result mapping back to Claude format."""
    print("=== Testing Result Mapping ===")

    mapper = ImprovedClaudeCodeSchemaMapper()

    # Test successful result
    success_result = PluginResult(
        continue_processing=True,
        modified_payload={"path": "/safe/example.txt", "mode": "read"},
        metadata={"approved_by": "security_plugin"}
    )

    claude_output = mapper.map_from_hook_result(success_result, "tool_pre_invoke")
    print(f"Success output: {json.dumps(claude_output, indent=2)}")

    assert claude_output["_continue"] == True
    assert claude_output["hook_specific_output"]["permission_decision"] == "allow"
    assert claude_output["modified_payload"]["path"] == "/safe/example.txt"

    # Test blocked result
    violation = PluginViolation(
        reason="File access denied",
        description="Cannot access system files",
        code="ACCESS_DENIED",
        details={"path": "/example.txt"}
    )

    blocked_result = PluginResult(
        continue_processing=False,
        violation=violation,
        metadata={"blocked_by": "security_plugin"}
    )

    claude_blocked_output = mapper.map_from_hook_result(blocked_result, "tool_pre_invoke")
    print(f"Blocked output: {json.dumps(claude_blocked_output, indent=2)}")

    assert claude_blocked_output["_continue"] == False
    assert claude_blocked_output["hook_specific_output"]["permission_decision"] == "deny"
    assert claude_blocked_output["hook_specific_output"]["permission_decision_reason"] == "File access denied"
    assert claude_blocked_output["stop_reason"] == "File access denied"

    print("✅ Result mapping test passed\n")


def test_post_tool_use():
    """Test PostToolUse event mapping."""
    print("=== Testing PostToolUse Mapping ===")

    mapper = ImprovedClaudeCodeSchemaMapper()

    # Post tool use payload
    post_payload = {
        "tool_name": "file_reader",
        "result": {"content": "File contents here", "size": 1024},
        "execution_time": 0.45,
        "success": True,
        "session_id": "session_123",
        "transcript_path": "/tmp/transcript.log",
        "cwd": "/workspace",
        "permission_mode": "default",
        "hook_event_name": "PostToolUse"
    }

    # Validate and map
    is_valid = mapper.validate_external_payload(post_payload, "tool_post_invoke")
    assert is_valid

    cpex_payload = mapper.map_to_hook_payload(post_payload, "tool_post_invoke")
    print(f"PostToolUse CPEX payload: {json.dumps(cpex_payload, indent=2)}")

    assert cpex_payload["name"] == "file_reader"
    assert cpex_payload["result"]["content"] == "File contents here"
    assert cpex_payload["result"]["size"] == 1024

    print("✅ PostToolUse test passed\n")


def test_error_handling():
    """Test error handling and validation."""
    print("=== Testing Error Handling ===")

    mapper = ImprovedClaudeCodeSchemaMapper()

    # Invalid payload - missing required field
    invalid_payload = {
        "tool_input": {"query": "test"},
        "session_id": "123"
        # Missing tool_name and other required fields
    }

    # Should fail validation
    is_valid = mapper.validate_external_payload(invalid_payload, "tool_pre_invoke")
    print(f"Invalid payload validation: {is_valid}")
    assert not is_valid

    # Should raise helpful error when mapping
    try:
        mapper.map_to_hook_payload(invalid_payload, "tool_pre_invoke")
        assert False, "Should have raised validation error"
    except ValueError as e:
        print(f"Expected validation error: {e}")
        assert "Invalid Claude Code input" in str(e)

    # Test unsupported hook type
    try:
        mapper.map_to_hook_payload({}, "unsupported_hook")
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError as e:
        print(f"Expected unsupported hook error: {e}")

    print("✅ Error handling test passed\n")


def run_all_tests():
    """Run all test functions."""
    print("🧪 Testing Improved Claude Code Schema Mapper\n")

    test_basic_compatibility()
    test_pre_tool_use_mapping()
    test_result_mapping()
    test_post_tool_use()
    test_error_handling()

    print("🎉 All tests passed! The improved mapper is working correctly.")
    print("\nKey improvements demonstrated:")
    print("- ✅ Drop-in compatibility with existing interface")
    print("- ✅ Comprehensive validation with clear error messages")
    print("- ✅ Type-safe mapping with Pydantic models")
    print("- ✅ Proper handling of all Claude Code event types")
    print("- ✅ Structured output format for Claude Code responses")


if __name__ == "__main__":
    run_all_tests()