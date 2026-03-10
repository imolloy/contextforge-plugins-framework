# -*- coding: utf-8 -*-
"""Unit tests for schema mapper base classes and registry.

Tests the abstract base class and registration system for schema mappers.
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock

from cpex.framework.models import PluginResult
from cpex.tools.schemas.base import (
    SchemaMapper,
    register_schema_mapper,
    get_schema_mapper,
    list_schema_mappers,
    _schema_mappers
)


class TestSchemaMapperRegistry:
    """Test suite for schema mapper registry functions."""

    def setup_method(self):
        """Set up test fixtures - clear registry."""
        # Save original state and clear for testing
        self.original_mappers = _schema_mappers.copy()
        _schema_mappers.clear()

    def teardown_method(self):
        """Restore original registry state."""
        _schema_mappers.clear()
        _schema_mappers.update(self.original_mappers)

    def test_register_schema_mapper(self):
        """Test registering a schema mapper."""
        class TestMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        # Register the mapper
        register_schema_mapper("test-mapper", TestMapper)

        # Verify registration
        assert "test-mapper" in _schema_mappers
        assert _schema_mappers["test-mapper"] == TestMapper

    def test_get_schema_mapper_success(self):
        """Test successful retrieval of registered mapper."""
        class TestMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        # Register and retrieve
        register_schema_mapper("test-mapper", TestMapper)
        mapper = get_schema_mapper("test-mapper")

        # Verify we get an instance of the correct type
        assert isinstance(mapper, TestMapper)
        assert isinstance(mapper, SchemaMapper)

    def test_get_schema_mapper_not_found(self):
        """Test error when requesting non-existent mapper."""
        with pytest.raises(ValueError) as exc_info:
            get_schema_mapper("non-existent-mapper")

        error_msg = str(exc_info.value)
        assert "No schema mapper registered" in error_msg
        assert "non-existent-mapper" in error_msg
        assert "Available mappers:" in error_msg

    def test_get_schema_mapper_with_available_mappers(self):
        """Test error message includes available mappers."""
        class TestMapper1(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        class TestMapper2(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        # Register multiple mappers
        register_schema_mapper("mapper1", TestMapper1)
        register_schema_mapper("mapper2", TestMapper2)

        # Try to get non-existent mapper
        with pytest.raises(ValueError) as exc_info:
            get_schema_mapper("non-existent")

        error_msg = str(exc_info.value)
        assert "mapper1" in error_msg
        assert "mapper2" in error_msg

    def test_list_schema_mappers_empty(self):
        """Test listing mappers when registry is empty."""
        mappers = list_schema_mappers()
        assert mappers == []

    def test_list_schema_mappers_with_entries(self):
        """Test listing mappers with registered entries."""
        class TestMapper1(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        class TestMapper2(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        # Register mappers
        register_schema_mapper("zebra-mapper", TestMapper1)
        register_schema_mapper("alpha-mapper", TestMapper2)

        mappers = list_schema_mappers()

        # Should return all registered mapper names
        assert len(mappers) == 2
        assert "zebra-mapper" in mappers
        assert "alpha-mapper" in mappers

    def test_register_multiple_mappers_same_name(self):
        """Test that registering with same name overwrites."""
        class TestMapper1(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return {"mapper": "1"}

            def map_from_hook_result(self, hook_result, hook_type):
                return {"mapper": "1"}

        class TestMapper2(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return {"mapper": "2"}

            def map_from_hook_result(self, hook_result, hook_type):
                return {"mapper": "2"}

        # Register first mapper
        register_schema_mapper("test-mapper", TestMapper1)
        mapper1 = get_schema_mapper("test-mapper")
        assert mapper1.map_to_hook_payload({}, "test") == {"mapper": "1"}

        # Register second mapper with same name (should overwrite)
        register_schema_mapper("test-mapper", TestMapper2)
        mapper2 = get_schema_mapper("test-mapper")
        assert mapper2.map_to_hook_payload({}, "test") == {"mapper": "2"}


class TestSchemaMapperAbstractBase:
    """Test suite for SchemaMapper abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that SchemaMapper cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SchemaMapper()

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented by subclasses."""
        # Missing map_to_hook_payload implementation
        class IncompleteMapper1(SchemaMapper):
            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        with pytest.raises(TypeError):
            IncompleteMapper1()

        # Missing map_from_hook_result implementation
        class IncompleteMapper2(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

        with pytest.raises(TypeError):
            IncompleteMapper2()

    def test_concrete_implementation_can_be_instantiated(self):
        """Test that properly implemented subclass can be instantiated."""
        class ConcreteMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        # Should not raise any errors
        mapper = ConcreteMapper()
        assert isinstance(mapper, SchemaMapper)

    def test_default_get_supported_hooks(self):
        """Test default implementation of get_supported_hooks."""
        class ConcreteMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        mapper = ConcreteMapper()
        supported_hooks = mapper.get_supported_hooks()

        # Default implementation returns empty list
        assert supported_hooks == []

    def test_custom_get_supported_hooks(self):
        """Test custom implementation of get_supported_hooks."""
        class ConcreteMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

            def get_supported_hooks(self):
                return ["tool_pre_invoke", "tool_post_invoke"]

        mapper = ConcreteMapper()
        supported_hooks = mapper.get_supported_hooks()

        assert supported_hooks == ["tool_pre_invoke", "tool_post_invoke"]

    def test_default_validate_external_payload(self):
        """Test default implementation of validate_external_payload."""
        class ConcreteMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

        mapper = ConcreteMapper()

        # Default implementation always returns True
        assert mapper.validate_external_payload({}, "any_hook") is True
        assert mapper.validate_external_payload({"complex": "payload"}, "hook") is True

    def test_custom_validate_external_payload(self):
        """Test custom implementation of validate_external_payload."""
        class ConcreteMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return external_payload

            def map_from_hook_result(self, hook_result, hook_type):
                return hook_result.model_dump()

            def validate_external_payload(self, external_payload, hook_type):
                # Custom validation: require 'tool_name' field
                return "tool_name" in external_payload

        mapper = ConcreteMapper()

        # Should return False for invalid payload
        assert mapper.validate_external_payload({}, "tool_pre_invoke") is False

        # Should return True for valid payload
        assert mapper.validate_external_payload(
            {"tool_name": "test"}, "tool_pre_invoke"
        ) is True


class TestSchemaMapperFunctional:
    """Functional tests for schema mapper implementations."""

    def test_functional_mapper_implementation(self):
        """Test a functional schema mapper implementation."""
        class FunctionalMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload: Dict[str, Any], hook_type: str) -> Dict[str, Any]:
                """Convert external tool format to CPEX format."""
                if hook_type == "tool_pre_invoke":
                    return {
                        "name": external_payload.get("tool_name"),
                        "args": external_payload.get("arguments", {}),
                        "headers": external_payload.get("headers")
                    }
                else:
                    raise NotImplementedError(f"Hook type {hook_type} not supported")

            def map_from_hook_result(self, hook_result: PluginResult, hook_type: str) -> Dict[str, Any]:
                """Convert CPEX result to external tool format."""
                if hook_type == "tool_pre_invoke":
                    result = {
                        "continue_processing": hook_result.continue_processing,
                        "cpex_result": hook_result.model_dump(),
                        "hook_type": hook_type
                    }

                    if hook_result.violation:
                        result["violation"] = {
                            "reason": hook_result.violation.reason,
                            "code": hook_result.violation.code,
                            "details": hook_result.violation.details
                        }

                    return result
                else:
                    raise NotImplementedError(f"Hook type {hook_type} not supported")

            def get_supported_hooks(self):
                return ["tool_pre_invoke"]

            def validate_external_payload(self, external_payload, hook_type):
                if hook_type == "tool_pre_invoke":
                    return "tool_name" in external_payload
                return False

        # Test the functional mapper
        mapper = FunctionalMapper()

        # Test map_to_hook_payload
        external_payload = {
            "tool_name": "calculator",
            "arguments": {"operation": "add", "a": 5, "b": 3},
            "session_id": "sess-123"
        }

        cpex_payload = mapper.map_to_hook_payload(external_payload, "tool_pre_invoke")
        assert cpex_payload["name"] == "calculator"
        assert cpex_payload["args"]["operation"] == "add"

        # Test map_from_hook_result
        from cpex.framework.models import PluginViolation
        from cpex.framework.hooks.tools import ToolPreInvokePayload

        violation = PluginViolation(
            reason="Test violation",
            description="Test description",
            code="TEST_CODE"
        )

        plugin_result = PluginResult[ToolPreInvokePayload](
            continue_processing=False,
            violation=violation,
            metadata={"test": "data"}
        )

        external_result = mapper.map_from_hook_result(plugin_result, "tool_pre_invoke")
        assert external_result["continue_processing"] is False
        assert external_result["violation"]["code"] == "TEST_CODE"
        assert external_result["cpex_result"]["metadata"]["test"] == "data"

        # Test get_supported_hooks
        assert mapper.get_supported_hooks() == ["tool_pre_invoke"]

        # Test validate_external_payload
        assert mapper.validate_external_payload(external_payload, "tool_pre_invoke") is True
        assert mapper.validate_external_payload({}, "tool_pre_invoke") is False

    def test_error_handling_in_mapper(self):
        """Test error handling in mapper implementations."""
        class ErrorHandlingMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                if hook_type not in ["tool_pre_invoke"]:
                    raise NotImplementedError(f"Unsupported hook type: {hook_type}")

                if "tool_name" not in external_payload:
                    raise ValueError("Missing required field: tool_name")

                return {
                    "name": external_payload["tool_name"],
                    "args": external_payload.get("arguments", {})
                }

            def map_from_hook_result(self, hook_result, hook_type):
                if hook_type not in ["tool_pre_invoke"]:
                    raise NotImplementedError(f"Unsupported hook type: {hook_type}")

                return hook_result.model_dump()

        mapper = ErrorHandlingMapper()

        # Test NotImplementedError for unsupported hook types
        with pytest.raises(NotImplementedError) as exc_info:
            mapper.map_to_hook_payload({}, "unsupported_hook")
        assert "Unsupported hook type: unsupported_hook" in str(exc_info.value)

        # Test ValueError for invalid payload
        with pytest.raises(ValueError) as exc_info:
            mapper.map_to_hook_payload({}, "tool_pre_invoke")
        assert "Missing required field: tool_name" in str(exc_info.value)

        # Test successful case
        valid_payload = {"tool_name": "test_tool", "arguments": {"param": "value"}}
        result = mapper.map_to_hook_payload(valid_payload, "tool_pre_invoke")
        assert result["name"] == "test_tool"

    def test_mapper_inheritance_and_composition(self):
        """Test that mappers can be extended through inheritance."""
        class BaseMapper(SchemaMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                return {"base": True, "payload": external_payload}

            def map_from_hook_result(self, hook_result, hook_type):
                return {"base": True, "result": hook_result.model_dump()}

        class ExtendedMapper(BaseMapper):
            def map_to_hook_payload(self, external_payload, hook_type):
                # Call parent implementation and extend
                base_result = super().map_to_hook_payload(external_payload, hook_type)
                base_result["extended"] = True
                return base_result

            def map_from_hook_result(self, hook_result, hook_type):
                # Call parent implementation and extend
                base_result = super().map_from_hook_result(hook_result, hook_type)
                base_result["extended"] = True
                return base_result

            def get_supported_hooks(self):
                return ["tool_pre_invoke", "tool_post_invoke"]

        # Test inheritance
        mapper = ExtendedMapper()

        payload_result = mapper.map_to_hook_payload({"test": "data"}, "hook")
        assert payload_result["base"] is True
        assert payload_result["extended"] is True
        assert payload_result["payload"]["test"] == "data"

        from cpex.framework.hooks.tools import ToolPreInvokePayload
        plugin_result = PluginResult[ToolPreInvokePayload](continue_processing=True)
        result = mapper.map_from_hook_result(plugin_result, "hook")
        assert result["base"] is True
        assert result["extended"] is True

        assert mapper.get_supported_hooks() == ["tool_pre_invoke", "tool_post_invoke"]