# -*- coding: utf-8 -*-
"""Unit tests for Claude Code schema mapper.

Tests the conversion between PluginResult types and Claude Code hook return formats.
"""

import pytest
from unittest.mock import Mock

from cpex.framework.models import PluginResult, PluginViolation
from cpex.framework.hooks.tools import ToolPreInvokePayload, ToolPostInvokePayload
# from cpex.tools.schemas.claude_code import ClaudeCodeSchemaMapper, PreToolUseModel
from cpex.tools.schemas.claude_code_improved import ClaudeHookInput
from cpex.tools.schemas.base import register_schema_mapper, get_schema_mapper

from pydantic import TypeAdapter

class TestClaudeCodeSchemaMapper:
    """Test suite for Claude Code schema mapper conversions."""

    def setup_method(self):
        """Set up test fixtures."""
        # self.mapper = ClaudeCodeSchemaMapper()
        pass

    def test_map_from_claude_tool_pre_invoke_payload(self):
        claude_hook_payload = {
            "session_id": "abc123",
            "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
            "cwd": "/home/user/my-project",
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "npm test"
            }
            }
        adapter = TypeAdapter(ClaudeHookInput)
        payload = adapter.validate_python(claude_hook_payload)  # Should not raise validation error

        cpex_payload = payload.model_dump(by_alias=True)
        
        cpex_object = ToolPreInvokePayload(**cpex_payload)
        assert "name" in cpex_payload
        assert cpex_object.name == "Bash"
    
    
        claude_hook_payload_post = {
            "session_id": "abv123",
            "transcript_path": "/home/user/foo",
            "cwd": "/home/user/",
            "permission_mode": "default",
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/user/bar",
                "content": "Hello, World!"
            },
            "tool_response": {
                "type": "create",
                "filePath": "/home/user/bar",
                "content": "Goodbye, World!",
                "structuredPatch": [],
                "originalFile": None
            },
            "tool_use_id": "toolu_1234"
            }
        payload = adapter.validate_python(claude_hook_payload_post)
    
    # def test_map_from_hook_result_basic_success(self):
    #     """Test basic successful PluginResult to Claude Code conversion."""
    #     # Create a basic successful PluginResult
    #     plugin_result = PluginResult[ToolPreInvokePayload](
    #         continue_processing=True,
    #         modified_payload=None,
    #         violation=None,
    #         metadata={"plugin_name": "test_plugin"}
    #     )

    #     # Convert to Claude Code format
    #     claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

    #     # Verify the conversion
    #     assert claude_result["continue"] is True
    #     assert "hookSpecificOutput" in claude_result
    #     assert claude_result["hookSpecificOutput"]["HookEventName"] == "PreToolUse"
    #     assert claude_result["hookSpecificOutput"]["PermissionDecision"] == "allow"
        

    # def test_map_from_hook_result_with_violation(self):
    #     """Test PluginResult conversion when violation is present."""
    #     # Create a violation
    #     violation = PluginViolation(
    #         reason="Blocked for security",
    #         description="Tool execution blocked due to security policy",
    #         code="SECURITY_VIOLATION",
    #         details={"tool_name": "dangerous_tool", "risk_level": "high"}
    #     )

    #     # Create PluginResult with violation
    #     plugin_result = PluginResult[ToolPreInvokePayload](
    #         continue_processing=False,
    #         modified_payload=None,
    #         violation=violation,
    #         metadata={"blocked_by": "security_plugin"}
    #     )

    #     # Convert to Claude Code format
    #     claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

    #     # Verify the conversion
    #     assert claude_result["continue"] is False
    #     assert claude_result["stopReason"] == violation.reason
    #     assert "hookSpecificOutput" in claude_result
    #     assert claude_result["hookSpecificOutput"]["HookEventName"] == "PreToolUse"
    #     assert claude_result["hookSpecificOutput"]["PermissionDecision"] == "deny"
    #     assert claude_result["hookSpecificOutput"]["PermissionDecisionReason"] == violation.reason
        
        # assert claude_result["hook_type"] == "tool_pre_invoke"

        # Check violation mapping
        
        # assert "violation" in claude_result
        # assert claude_result["violation"]["reason"] == "Blocked for security"
        # assert claude_result["violation"]["code"] == "SECURITY_VIOLATION"
        # assert claude_result["violation"]["details"]["risk_level"] == "high"

        # # Check cpex_result contains the violation
        # assert claude_result["cpex_result"]["violation"] is not None

#     def test_map_from_hook_result_with_modified_payload(self):
#         """Test PluginResult conversion with modified payload."""
#         # Create modified payload
#         original_payload = ToolPreInvokePayload(name="search", args={"query": "test"})
#         modified_payload = ToolPreInvokePayload(
#             name="search",
#             args={"query": "sanitized_test", "limit": 10}
#         )

#         # Create PluginResult with modified payload
#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=True,
#             modified_payload=modified_payload,
#             violation=None,
#             metadata={"transformation": "query_sanitization"}
#         )

#         # Convert to Claude Code format
#         claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify the conversion
#         assert claude_result["continue_processing"] is True
#         assert "modified_payload" in claude_result
#         assert claude_result["modified_payload"] is not None

#         # Check that modified payload is included in cpex_result
#         assert claude_result["cpex_result"]["modified_payload"] is not None

#     def test_map_from_hook_result_post_invoke(self):
#         """Test PluginResult conversion for tool_post_invoke hook type."""
#         # Create a tool post-invoke payload
#         post_payload = ToolPostInvokePayload(
#             name="calculator",
#             result={"answer": 42, "execution_time": 0.1}
#         )

#         plugin_result = PluginResult[ToolPostInvokePayload](
#             continue_processing=True,
#             modified_payload=None,
#             violation=None,
#             metadata={"audit_logged": True, "cached": False}
#         )

#         # Convert to Claude Code format
#         claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_post_invoke")

#         # Verify the conversion
#         assert claude_result["continue_processing"] is True
#         assert claude_result["hook_type"] == "tool_post_invoke"
#         assert claude_result["metadata"]["audit_logged"] is True
#         assert claude_result["metadata"]["cached"] is False

#     def test_map_from_hook_result_complex_scenario(self):
#         """Test complex scenario with violation, modified payload, and metadata."""
#         # Create modified payload
#         modified_payload = ToolPreInvokePayload(
#             name="file_read",
#             args={"path": "/safe/path/file.txt", "mode": "read_only"}
#         )

#         # Create violation (plugin allows processing but logs violation)
#         violation = PluginViolation(
#             reason="Path sanitization applied",
#             description="Original path was modified for security",
#             code="PATH_SANITIZATION",
#             details={"original_path": "/etc/passwd", "sanitized_path": "/safe/path/file.txt"}
#         )

#         # Create complex PluginResult
#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=True,  # Allow processing with sanitized payload
#             modified_payload=modified_payload,
#             violation=violation,
#             metadata={
#                 "sanitization_applied": True,
#                 "security_level": "strict",
#                 "plugin_chain": ["path_sanitizer", "security_checker"]
#             }
#         )

#         # Convert to Claude Code format
#         claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify comprehensive conversion
#         assert claude_result["continue_processing"] is True
#         assert claude_result["hook_type"] == "tool_pre_invoke"

#         # Check violation is preserved
#         assert "violation" in claude_result
#         assert claude_result["violation"]["code"] == "PATH_SANITIZATION"

#         # Check modified payload is preserved
#         assert "modified_payload" in claude_result
#         assert claude_result["modified_payload"] is not None

#         # Check metadata is preserved
#         assert "metadata" in claude_result
#         assert claude_result["metadata"]["sanitization_applied"] is True
#         assert claude_result["metadata"]["security_level"] == "strict"

#     def test_map_from_hook_result_unsupported_hook_type(self):
#         """Test error handling for unsupported hook types."""
#         plugin_result = PluginResult[ToolPreInvokePayload](continue_processing=True)

#         with pytest.raises(NotImplementedError) as exc_info:
#             self.mapper.map_from_hook_result(plugin_result, "unsupported_hook_type")

#         assert "Claude Code result mapping not implemented" in str(exc_info.value)
#         assert "unsupported_hook_type" in str(exc_info.value)

#     def test_map_from_hook_result_empty_metadata(self):
#         """Test conversion with empty metadata."""
#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=True,
#             metadata={}  # Empty but not None
#         )

#         claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         assert claude_result["continue_processing"] is True
#         # Empty metadata should still be included
#         assert "metadata" in claude_result
#         assert claude_result["metadata"] == {}

#     def test_map_from_hook_result_none_metadata(self):
#         """Test conversion with None metadata."""
#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=True,
#             metadata=None
#         )

#         claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         assert claude_result["continue_processing"] is True
#         # None metadata should not be included in the result
#         assert "metadata" not in claude_result or claude_result["metadata"] is None

#     def test_hook_result_model_dump_preservation(self):
#         """Test that the original PluginResult model_dump is preserved in cpex_result."""
#         # Create PluginResult with specific structure
#         violation = PluginViolation(
#             reason="Test violation",
#             description="Test description",
#             code="TEST_CODE"
#         )

#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=False,
#             violation=violation,
#             metadata={"test": "data"}
#         )

#         # Get the original model dump
#         original_dump = plugin_result.model_dump()

#         # Convert to Claude Code format
#         claude_result = self.mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify that cpex_result contains the complete original data
#         cpex_result = claude_result["cpex_result"]
#         assert cpex_result["continue_processing"] == original_dump["continue_processing"]
#         assert cpex_result["violation"]["reason"] == original_dump["violation"]["reason"]
#         assert cpex_result["metadata"] == original_dump["metadata"]


# class TestClaudeCodeSchemaMapperIntegration:
#     """Integration tests for Claude Code schema mapper with the registry system."""

#     def test_schema_mapper_registration(self):
#         """Test that Claude Code schema mapper is properly registered."""
#         # Should be auto-registered when module is imported
#         mapper = get_schema_mapper("claude-code")
#         assert isinstance(mapper, ClaudeCodeSchemaMapper)

#     def test_roundtrip_conversion_tool_pre_invoke(self):
#         """Test complete roundtrip: Claude payload -> CPEX -> PluginResult -> Claude result."""
#         mapper = ClaudeCodeSchemaMapper()

#         # 1. Start with Claude Code payload
#         claude_payload = {
#             "tool_name": "search_files",
#             "arguments": {"pattern": "*.py", "directory": "/src"},
#             "session_id": "sess-123",
#             "timestamp": "2025-03-06T10:30:00Z"
#         }

#         # 2. Convert to CPEX format
#         cpex_payload = mapper.map_to_hook_payload(claude_payload, "tool_pre_invoke")
#         assert cpex_payload["name"] == "search_files"
#         assert cpex_payload["args"]["pattern"] == "*.py"

#         # 3. Simulate plugin processing (create PluginResult)
#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=True,
#             modified_payload=None,
#             violation=None,
#             metadata={"processed_at": "2025-03-06T10:30:01Z"}
#         )

#         # 4. Convert back to Claude Code format
#         claude_result = mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # 5. Verify roundtrip integrity
#         assert claude_result["continue_processing"] is True
#         assert claude_result["hook_type"] == "tool_pre_invoke"
#         assert "cpex_result" in claude_result
#         assert claude_result["metadata"]["processed_at"] == "2025-03-06T10:30:01Z"

#     def test_roundtrip_conversion_with_blocking(self):
#         """Test roundtrip when plugin blocks processing."""
#         mapper = ClaudeCodeSchemaMapper()

#         # Claude payload for dangerous operation
#         claude_payload = {
#             "tool_name": "execute_command",
#             "arguments": {"command": "rm -rf /", "shell": "bash"},
#             "session_id": "sess-456"
#         }

#         # Convert to CPEX
#         cpex_payload = mapper.map_to_hook_payload(claude_payload, "tool_pre_invoke")

#         # Simulate security plugin blocking
#         violation = PluginViolation(
#             reason="Dangerous command blocked",
#             description="Command would cause system damage",
#             code="DANGEROUS_OPERATION",
#             details={"command": "rm -rf /", "risk": "critical"}
#         )

#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=False,  # Block execution
#             violation=violation,
#             metadata={"blocked_by": "security_plugin"}
#         )

#         # Convert back to Claude Code format
#         claude_result = mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify blocking is properly communicated
#         assert claude_result["continue_processing"] is False
#         assert claude_result["violation"]["code"] == "DANGEROUS_OPERATION"
#         assert claude_result["violation"]["details"]["risk"] == "critical"


# class TestPluginResultClaudeCodeConversions:
#     """Focused tests on PluginResult to Claude Code conversion edge cases."""

#     def test_nested_violation_details_preservation(self):
#         """Test that complex nested violation details are preserved."""
#         mapper = ClaudeCodeSchemaMapper()

#         # Create violation with complex nested details
#         violation = PluginViolation(
#             reason="Complex validation failure",
#             description="Multiple validation errors occurred",
#             code="MULTI_VALIDATION_ERROR",
#             details={
#                 "errors": [
#                     {"field": "email", "message": "Invalid format"},
#                     {"field": "age", "message": "Out of range"}
#                 ],
#                 "metadata": {
#                     "validation_version": "2.1",
#                     "strict_mode": True
#                 },
#                 "context": {
#                     "form_id": "user_registration",
#                     "section": "personal_info"
#                 }
#             }
#         )

#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=False,
#             violation=violation
#         )

#         claude_result = mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify complex nested structure is preserved
#         details = claude_result["violation"]["details"]
#         assert len(details["errors"]) == 2
#         assert details["errors"][0]["field"] == "email"
#         assert details["metadata"]["validation_version"] == "2.1"
#         assert details["context"]["form_id"] == "user_registration"

#     def test_large_metadata_preservation(self):
#         """Test handling of large metadata objects."""
#         mapper = ClaudeCodeSchemaMapper()

#         # Create large metadata object
#         large_metadata = {
#             "processing_stats": {
#                 "tokens_processed": 15000,
#                 "processing_time_ms": 250,
#                 "memory_usage_mb": 128
#             },
#             "plugin_chain": [f"plugin_{i}" for i in range(50)],  # Large list
#             "debug_info": {
#                 f"step_{i}": {"status": "success", "duration": i * 10}
#                 for i in range(100)  # Large dict
#             },
#             "configuration": {
#                 "feature_flags": {f"flag_{i}": i % 2 == 0 for i in range(200)},
#                 "settings": {"nested": {"deeply": {"buried": {"value": "found"}}}}
#             }
#         }

#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=True,
#             metadata=large_metadata
#         )

#         claude_result = mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify large metadata is preserved
#         result_metadata = claude_result["metadata"]
#         assert result_metadata["processing_stats"]["tokens_processed"] == 15000
#         assert len(result_metadata["plugin_chain"]) == 50
#         assert len(result_metadata["debug_info"]) == 100
#         assert result_metadata["configuration"]["settings"]["nested"]["deeply"]["buried"]["value"] == "found"

#     def test_unicode_and_special_characters(self):
#         """Test handling of Unicode and special characters in conversion."""
#         mapper = ClaudeCodeSchemaMapper()

#         # Create violation with Unicode content
#         violation = PluginViolation(
#             reason="Contenu bloqué pour sécurité 🔒",
#             description="Le contenu contient des caractères spéciaux: éàüñ™",
#             code="UNICODE_CONTENT_ERROR",
#             details={
#                 "emoji_found": "🚨⚠️💀",
#                 "languages": ["français", "español", "中文"],
#                 "special_chars": "!@#$%^&*()_+-=[]{}|;:'\",.<>?/~`"
#             }
#         )

#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=False,
#             violation=violation,
#             metadata={"unicode_test": "测试文本 🧪"}
#         )

#         claude_result = mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify Unicode preservation
#         assert "🔒" in claude_result["violation"]["reason"]
#         assert "éàüñ™" in claude_result["violation"]["description"]
#         assert claude_result["violation"]["details"]["emoji_found"] == "🚨⚠️💀"
#         assert "中文" in claude_result["violation"]["details"]["languages"]
#         assert claude_result["metadata"]["unicode_test"] == "测试文本 🧪"

#     def test_null_and_empty_values_handling(self):
#         """Test proper handling of null and empty values."""
#         mapper = ClaudeCodeSchemaMapper()

#         # Create plugin result with various null/empty values
#         plugin_result = PluginResult[ToolPreInvokePayload](
#             continue_processing=True,
#             modified_payload=None,  # Explicitly None
#             violation=None,         # Explicitly None
#             metadata={
#                 "empty_string": "",
#                 "empty_list": [],
#                 "empty_dict": {},
#                 "null_value": None,
#                 "zero_value": 0,
#                 "false_value": False
#             }
#         )

#         claude_result = mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")

#         # Verify proper null/empty handling
#         assert claude_result["continue_processing"] is True

#         # modified_payload should not be present or should be None
#         if "modified_payload" in claude_result:
#             assert claude_result["modified_payload"] is None

#         # violation should not be present or should be None
#         if "violation" in claude_result:
#             assert claude_result["violation"] is None

#         # Check metadata preservation of empty values
#         metadata = claude_result["metadata"]
#         assert metadata["empty_string"] == ""
#         assert metadata["empty_list"] == []
#         assert metadata["empty_dict"] == {}
#         assert metadata["null_value"] is None
#         assert metadata["zero_value"] == 0
#         assert metadata["false_value"] is False