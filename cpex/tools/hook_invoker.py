# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/hook_invoker.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Claude Code

Hook Invoker ─ orchestration engine for CLI hook invocation
This module provides the core logic for invoking hooks through the CLI interface.

Features
─────────
* Synchronous wrapper for async hook invocation
* JSON payload validation and conversion using HookRegistry
* Schema mapping for external tool integration
* Standardized result formatting and exit code handling

Classes
───────
* HookInvoker: Main orchestration class
* InvocationResult: Standardized result container
"""

# Standard
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# First-Party
from cpex.framework.hooks.registry import get_hook_registry
from cpex.framework.loader.config import ConfigLoader
from cpex.framework.manager import PluginManager
from cpex.framework.models import GlobalContext, PluginResult
from cpex.tools.output import ExitCode, InvocationResult
from cpex.tools.schemas.base import get_schema_mapper

# Import hook modules to trigger registration
from cpex.framework.hooks import tools, agents, resources, prompts, http, policies  # noqa: F401

logger = logging.getLogger(__name__)


class HookInvoker:
    """Hook invocation orchestration engine.

    This class provides a synchronous interface for invoking hooks through
    the CLI, handling JSON payload conversion, schema mapping, and result
    formatting.

    Examples:
        >>> invoker = HookInvoker()
        >>> result = invoker.invoke_hook_sync(
        ...     hook_type="tool_pre_invoke",
        ...     payload={"name": "test", "args": {}},
        ...     global_context={"request_id": "123"}
        ... )
        >>> result.exit_code
        <ExitCode.SUCCESS: 0>
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the hook invoker.

        Args:
            config_path: Optional path to plugin configuration file
        """
        self.config_path = config_path
        self._plugin_manager: Optional[PluginManager] = None

    def _get_plugin_manager(self) -> PluginManager:
        """Get or create plugin manager instance.

        Returns:
            Initialized plugin manager

        Raises:
            RuntimeError: If plugin manager initialization fails
        """
        if self._plugin_manager is None:
            try:
                if self.config_path:
                    config = ConfigLoader.load_config(self.config_path)
                    self._plugin_manager = PluginManager(config)
                else:
                    # Use default configuration
                    self._plugin_manager = PluginManager()

                # Initialize plugin manager asynchronously
                asyncio.get_event_loop().run_until_complete(
                    self._plugin_manager.initialize()
                )
            except Exception as e:
                logger.error(f"Failed to initialize plugin manager: {e}")
                raise RuntimeError(f"Plugin manager initialization failed: {e}")

        return self._plugin_manager

    def invoke_hook_sync(
        self,
        hook_type: str,
        payload: Dict[str, Any],
        global_context: Optional[Dict[str, Any]] = None,
        schema_mapper: Optional[str] = None
    ) -> InvocationResult:
        """Synchronously invoke a hook with the provided payload.

        Args:
            hook_type: The hook type to invoke
            payload: JSON payload as dictionary
            global_context: Optional global context as dictionary
            schema_mapper: Optional schema mapper name for external tool integration

        Returns:
            Invocation result with exit code and formatted output

        Raises:
            ValueError: If hook type is not registered or payload is invalid
            RuntimeError: If hook invocation fails
        """
        try:
            # Apply schema mapping if specified
            if schema_mapper:
                mapper = get_schema_mapper(schema_mapper)
                payload = mapper.map_to_hook_payload(payload, hook_type)

            # Validate hook type is registered
            registry = get_hook_registry()
            if not registry.is_registered(hook_type):
                available_hooks = registry.get_registered_hooks()
                raise ValueError(
                    f"Hook type '{hook_type}' is not registered. "
                    f"Available hooks: {', '.join(available_hooks)}"
                )

            # Convert JSON payload to Pydantic model
            plugin_payload = registry.json_to_payload(hook_type, payload)
            logger.debug(f"Converted payload: {plugin_payload}")

            # Create global context
            if global_context:
                # Extract request_id (required field) with default
                request_id = global_context.get("request_id", "cli-generated-id")

                # Filter valid GlobalContext fields
                valid_fields = {}
                for key, value in global_context.items():
                    if key != "request_id" and hasattr(GlobalContext, key):
                        valid_fields[key] = value
                    elif key != "request_id":
                        logger.warning(f"Unknown global context field: {key}")

                global_ctx = GlobalContext(request_id=request_id, **valid_fields)
            else:
                # Use default values when no context provided
                global_ctx = GlobalContext(request_id="cli-generated-id")

            # Get plugin manager and invoke hook
            manager = self._get_plugin_manager()

            # Run async hook invocation
            result, _ = asyncio.get_event_loop().run_until_complete(
                manager.invoke_hook(hook_type, plugin_payload, global_ctx)
            )

            # Apply reverse schema mapping if specified
            if schema_mapper:
                mapper = get_schema_mapper(schema_mapper)
                output_data = mapper.map_from_hook_result(result, hook_type)
            else:
                output_data = result.model_dump()

            # Determine exit code based on result
            exit_code = self._determine_exit_code(result)

            return InvocationResult(
                success=True,
                data=output_data,
                exit_code=exit_code,
                hook_type=hook_type
            )

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return InvocationResult(
                success=False,
                error=str(e),
                exit_code=ExitCode.CONFIGURATION_ERROR,
                hook_type=hook_type
            )

        except Exception as e:
            logger.error(f"Hook invocation failed: {e}")
            logger.debug("Full traceback:", exc_info=True)
            return InvocationResult(
                success=False,
                error=str(e),
                exit_code=ExitCode.EXECUTION_ERROR,
                hook_type=hook_type
            )

    def list_hooks(self) -> List[str]:
        """List all registered hook types.

        Returns:
            List of registered hook type names

        Raises:
            RuntimeError: If hook registry access fails
        """
        try:
            registry = get_hook_registry()
            return sorted(registry.get_registered_hooks())
        except Exception as e:
            logger.error(f"Failed to list hooks: {e}")
            raise RuntimeError(f"Hook listing failed: {e}")

    def describe_hook(self, hook_type: str) -> Dict[str, Any]:
        """Describe a specific hook type with schema information.

        Args:
            hook_type: The hook type to describe

        Returns:
            Dictionary containing hook schema information

        Raises:
            ValueError: If hook type is not registered
            RuntimeError: If schema introspection fails
        """
        try:
            registry = get_hook_registry()

            if not registry.is_registered(hook_type):
                available_hooks = registry.get_registered_hooks()
                raise ValueError(
                    f"Hook type '{hook_type}' is not registered. "
                    f"Available hooks: {', '.join(available_hooks)}"
                )

            payload_class = registry.get_payload_type(hook_type)
            result_class = registry.get_result_type(hook_type)

            description = {
                "hook_type": hook_type,
                "payload_schema": payload_class.model_json_schema() if payload_class else None,
                "result_schema": result_class.model_json_schema() if result_class else None,
                "payload_class": payload_class.__name__ if payload_class else None,
                "result_class": result_class.__name__ if result_class else None,
            }

            return description

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to describe hook {hook_type}: {e}")
            raise RuntimeError(f"Hook description failed: {e}")

    def _determine_exit_code(self, result: PluginResult) -> ExitCode:
        """Determine appropriate exit code based on plugin result.

        Args:
            result: The plugin result from hook invocation

        Returns:
            Appropriate exit code
        """
        if not result.continue_processing:
            if result.violation:
                # Hook blocked processing due to violation
                return ExitCode.BLOCKED_BY_VIOLATION
            else:
                # Hook decided to stop processing (but not due to violation)
                return ExitCode.BLOCKED_BY_VIOLATION

        return ExitCode.SUCCESS