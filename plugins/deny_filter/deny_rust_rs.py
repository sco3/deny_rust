# -*- coding: utf-8 -*-
"""Location: ./plugins/deny_filter/deny.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Fred Araujo, Dmitry Zakharov

Simple example plugin for searching and replacing text.
This module loads configurations for plugins.
"""

# Third-Party
from typing import Any

# First-Party
from deny_filter import DenyListRs
from mcpgateway.plugins.framework import (
    PluginConfig,
    PluginContext,
    PluginViolation,
    PromptPrehookPayload,
    PromptPrehookResult,
)
from mcpgateway.services.logging_service import LoggingService
from plugins.deny_filter.deny import DenyListConfig, DenyListPlugin

# Initialize logging service first
logging_service = LoggingService()
logger = logging_service.get_logger(__name__)


class DenyListPluginRustRs(DenyListPlugin):
    """Example deny list plugin."""

    def __init__(self, config: PluginConfig):
        """Initialize the deny list plugin.

        Args:
            config: Plugin configuration.
        """
        super().__init__(config)
        self._dconfig = DenyListConfig.model_validate(self._config.config)
        self._deny_list: Any = DenyListRs(self._dconfig.words)

    async def prompt_pre_fetch(
        self, payload: PromptPrehookPayload, context: PluginContext
    ) -> PromptPrehookResult:
        """The plugin hook run before a prompt is retrieved and rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the prompt can proceed.
        """
        if payload.args:
            if self._deny_list.scan_any(payload.args):
                violation = PluginViolation(
                    reason="Prompt not allowed",
                    description="A deny word was found in the prompt",
                    code="deny",
                    details={},
                )
                logger.warning("Deny word detected in prompt")
                return PromptPrehookResult(
                    modified_payload=payload,
                    violation=violation,
                    continue_processing=False,
                )
        return PromptPrehookResult(modified_payload=payload)
