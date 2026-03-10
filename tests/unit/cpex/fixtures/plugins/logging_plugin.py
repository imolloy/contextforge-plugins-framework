# -*- coding: utf-8 -*-
"""Location: ./tests/unit/cpex/fixtures/plugins/passthrough.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Ian Molloy

Passthrough Logging plugin.
"""

from pydantic import BaseModel

# First-Party
from cpex.framework import (
    PluginContext,
    Plugin,
    PromptPosthookPayload,
    PromptPosthookResult,
    PromptPrehookPayload,
    PromptPrehookResult,
    ResourcePostFetchPayload,
    ResourcePostFetchResult,
    ResourcePreFetchPayload,
    ResourcePreFetchResult,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
)
from cpex.framework.models import PluginConfig


class PassThroughLoggingPlugin(Plugin):
    """A simple pass through plugin."""

    def __init__(self, config: PluginConfig):
        """Initialize the logging plugin.

        Args:
            config: Plugin configuration.
        """
        super().__init__(config)
        self._dconfig = PassThroughLoggingConfig.model_validate(self._config.config)
        self.output_file = self._dconfig.output_file

    async def prompt_pre_fetch(self, payload: PromptPrehookPayload, context: PluginContext) -> PromptPrehookResult:
        """The plugin hook run before a prompt is retrieved and rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the prompt can proceed.
        """
        with open(self.output_file, "a") as f:
            f.write(f"prompt_pre_fetch: {payload}\n")
        return PromptPrehookResult(continue_processing=True)

    async def prompt_post_fetch(self, payload: PromptPosthookPayload, context: PluginContext) -> PromptPosthookResult:
        """Plugin hook run after a prompt is rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the prompt can proceed.
        """
        with open(self.output_file, "a") as f:
            f.write(f"prompt_post_fetch: {payload}\n")
        return PromptPosthookResult(continue_processing=True)

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Plugin hook run before a tool is invoked.

        Args:
            payload: The tool payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the tool can proceed.
        """
        with open(self.output_file, "a") as f:
            f.write(f"tool_pre_invoke: {payload}\n")
        return ToolPreInvokeResult(continue_processing=True)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        """Plugin hook run after a tool is invoked.

        Args:
            payload: The tool result payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the tool result should proceed.
        """
        with open(self.output_file, "a") as f:
            f.write(f"tool_post_invoke: {payload}\n")
        return ToolPostInvokeResult(continue_processing=True)

    async def resource_post_fetch(
        self, payload: ResourcePostFetchPayload, context: PluginContext
    ) -> ResourcePostFetchResult:
        """Plugin hook run after a resource was fetched.

        Args:
            payload: The resource result payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the resource result should proceed.
        """
        with open(self.output_file, "a") as f:
            f.write(f"resource_post_fetch: {payload}\n")
        return ResourcePostFetchResult(continue_processing=True)

    async def resource_pre_fetch(
        self, payload: ResourcePreFetchPayload, context: PluginContext
    ) -> ResourcePreFetchResult:
        """Plugin hook run before a resource was fetched.

        Args:
            payload: The resource result payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the resource result should proceed.
        """
        with open(self.output_file, "a") as f:
            f.write(f"resource_pre_fetch: {payload}\n")
        return ResourcePreFetchResult(continue_processing=True)


class PassThroughLoggingConfig(BaseModel):
    """Configuration for deny list plugin.

    Attributes:
        words: List of words to deny.
    """

    output_file: str
