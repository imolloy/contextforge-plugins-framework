# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/schemas/base.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Claude Code

Schema Mapper Base Classes ─ abstract interfaces for payload transformation
This module provides the abstract base classes for implementing schema mappers
that transform external tool payloads to CPEX hook formats and vice versa.

Features
─────────
* Abstract base class for schema mappers
* Registry for schema mapper implementations
* Factory function for getting schema mappers

Classes
───────
* SchemaMapper: Abstract base class for all schema mappers
"""

# Standard
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel

# First-Party
from cpex.framework.models import PluginPayload, PluginResult
CPEXPayload = TypeVar('CPEXPayload', bound=BaseModel)
CPEXResult = TypeVar('CPEXResult', bound=PluginResult)


logger = logging.getLogger(__name__)


class SchemaMapper(ABC):
    """Abstract base class for schema mappers.

    Schema mappers transform external tool payloads to CPEX hook formats
    and transform CPEX hook results back to external tool formats.

    This enables seamless integration between external tools (like Claude Code)
    and the CPEX plugin ecosystem without requiring the external tools to
    understand CPEX's internal payload formats.

    Examples:
        >>> class MySchemaMapper(SchemaMapper):
        ...     def map_to_hook_payload(self, external_payload, hook_type):
        ...         return {"name": external_payload["tool_name"], "args": external_payload.get("args", {})}
        ...     def map_from_hook_result(self, hook_result, hook_type):
        ...         return {"success": hook_result.continue_processing, "data": hook_result.model_dump()}
    """

    @abstractmethod
    def map_to_hook_payload(self, external_payload: Dict[str, Any]) -> CPEXPayload:
        """Transform external tool payload to CPEX hook format.

        Args:
            external_payload: The payload from the external tool
            hook_type: The CPEX hook type being invoked

        Returns:
            Transformed payload in CPEX hook format

        Raises:
            ValueError: If the payload cannot be transformed or is invalid
            NotImplementedError: If the hook type is not supported by this mapper
        """

    @abstractmethod
    def map_from_hook_result(self, hook_result: PluginResult, hook_type: str) -> Dict[str, Any]:
        """Transform CPEX hook result to external tool format.

        Args:
            hook_result: The result from CPEX hook execution
            hook_type: The CPEX hook type that was invoked

        Returns:
            Transformed result in external tool format

        Raises:
            ValueError: If the result cannot be transformed
            NotImplementedError: If the hook type is not supported by this mapper
        """

    def get_supported_hooks(self) -> list[str]:
        """Get list of hook types supported by this mapper.

        Returns:
            List of supported hook type names

        Note:
            Default implementation returns empty list. Subclasses should
            override this to specify which hooks they support.
        """
        return []

    def validate_external_payload(self, external_payload: Dict[str, Any], hook_type: str) -> bool:
        """Validate that external payload is compatible with this mapper.

        Args:
            external_payload: The payload from the external tool
            hook_type: The CPEX hook type being invoked

        Returns:
            True if payload is valid, False otherwise

        Note:
            Default implementation always returns True. Subclasses can
            override this to provide custom validation logic.
        """
        return True


# Registry for schema mapper implementations
_schema_mappers: Dict[str, Type[SchemaMapper]] = {}


def register_schema_mapper(name: str, mapper_class: Type[SchemaMapper]) -> None:
    """Register a schema mapper implementation.

    Args:
        name: The name to register the mapper under
        mapper_class: The schema mapper class to register

    Examples:
        >>> register_schema_mapper("my-tool", MySchemaMapper)
    """
    _schema_mappers[name] = mapper_class
    logger.debug(f"Registered schema mapper '{name}': {mapper_class.__name__}")


def get_schema_mapper(name: str) -> SchemaMapper:
    """Get a schema mapper instance by name.

    Args:
        name: The name of the schema mapper to retrieve

    Returns:
        Instance of the requested schema mapper

    Raises:
        ValueError: If no mapper is registered with the given name

    Examples:
        >>> mapper = get_schema_mapper("claude-code")
        >>> isinstance(mapper, SchemaMapper)
        True
    """
    if name not in _schema_mappers:
        available_mappers = list(_schema_mappers.keys())
        raise ValueError(
            f"No schema mapper registered with name '{name}'. "
            f"Available mappers: {', '.join(available_mappers)}"
        )

    mapper_class = _schema_mappers[name]
    return mapper_class()


def list_schema_mappers() -> list[str]:
    """List all registered schema mapper names.

    Returns:
        List of registered schema mapper names

    Examples:
        >>> mappers = list_schema_mappers()
        >>> isinstance(mappers, list)
        True
    """
    return list(_schema_mappers.keys())