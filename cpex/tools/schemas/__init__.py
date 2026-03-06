# -*- coding: utf-8 -*-
"""Location: ./cpex/tools/schemas/__init__.py
Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Claude Code

Schema Mapping Package ─ transform external tool payloads to CPEX hook formats
This package provides schema mappers for integrating external tools with CPEX hooks.

Modules
───────
* base: Abstract base classes for schema mappers
* claude_code: Schema mapping for Claude Code hook events

Classes
───────
* SchemaMapper: Abstract base class for all schema mappers
"""

from cpex.tools.schemas.base import SchemaMapper, get_schema_mapper

__all__ = ["SchemaMapper", "get_schema_mapper"]