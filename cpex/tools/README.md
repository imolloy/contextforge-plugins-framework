# CPEX CLI Tools

This module provides command-line interfaces for the CPEX (ContextForge Plugin Extensibility Framework) system, enabling both plugin users and developers to interact with the framework effectively.

## Overview

The CLI tools consist of two main components:

1. **`cpex` CLI**: Hook invocation and introspection for plugin users
2. **`mcpplugins` CLI**: Plugin development and bootstrapping tools

## Architecture

```mermaid
graph TB
    %% CLI Layer
    subgraph "CLI Layer"
        A[cpex CLI<br/>cpex_cli.py] --> B[Hook Invocation]
        A --> C[Hook Introspection]
        D[mcpplugins CLI<br/>cli.py] --> E[Project Bootstrap]
        D --> F[Plugin Install]
        D --> G[Plugin Package]
    end

    %% Core Engine
    subgraph "Core Engine"
        H[HookInvoker<br/>hook_invoker.py] --> I[Plugin Manager]
        H --> J[Hook Registry]
        H --> K[Schema Mappers]
    end

    %% Schema Mapping System
    subgraph "Schema Mapping System"
        L[SchemaMapper<br/>Base Class] --> M[ClaudeCodeSchemaMapper]
        L --> N[Custom Mappers...]
        O[Schema Registry] --> L
    end

    %% Output System
    subgraph "Output System"
        P[InvocationResult<br/>output.py] --> Q[JSON Formatting]
        R[ExitCode] --> S[Unix Exit Codes]
        T[format_output] --> P
        T --> R
    end

    %% Framework Integration
    subgraph "CPEX Framework"
        U[PluginManager] --> V[Plugin Execution]
        W[HookRegistry] --> X[Hook Types]
        Y[GlobalContext] --> Z[Request Context]
        AA[PluginResult] --> BB[Hook Results]
    end

    %% Connections
    A --> H
    D --> CC[Template System]
    H --> U
    H --> W
    K --> O
    H --> P
    B --> T
    C --> W
    I --> U
    J --> W
    H --> Y
    V --> AA
```

## Class Hierarchy

```mermaid
classDiagram
    %% Abstract Base Classes
    class SchemaMapper {
        <<abstract>>
        +map_to_hook_payload(payload, hook_type) Dict*
        +map_from_hook_result(result, hook_type) Dict*
        +get_supported_hooks() List[str]
        +validate_external_payload(payload, hook_type) bool
    }

    %% Core Classes
    class HookInvoker {
        -config_path: Path
        -_plugin_manager: PluginManager
        +__init__(config_path)
        +invoke_hook_sync(hook_type, payload, context, schema) InvocationResult
        +list_hooks() List[str]
        +describe_hook(hook_type) Dict
        -_get_plugin_manager() PluginManager
        -_determine_exit_code(result) ExitCode
    }

    class InvocationResult {
        +success: bool
        +exit_code: ExitCode
        +hook_type: str
        +data: Dict
        +error: str
        +metadata: Dict
        +to_dict() Dict
    }

    class ExitCode {
        <<enumeration>>
        SUCCESS = 0
        EXECUTION_ERROR = 1
        BLOCKED_BY_VIOLATION = 2
        CONFIGURATION_ERROR = 3
    }

    %% Concrete Implementations
    class ClaudeCodeSchemaMapper {
        +map_to_hook_payload(payload, hook_type) Dict
        +map_from_hook_result(result, hook_type) Dict
        +get_supported_hooks() List[str]
        +validate_external_payload(payload, hook_type) bool
        -_map_pre_tool_use(payload) Dict
        -_map_post_tool_use(payload) Dict
        -_map_tool_result(result, hook_type) Dict
    }

    %% Framework Models
    class PluginResult {
        +continue_processing: bool
        +modified_payload: BaseModel
        +violation: PluginViolation
        +metadata: Dict
        +model_dump() Dict
    }

    class GlobalContext {
        +request_id: str
        +user: str
        +tenant_id: str
        +server_id: str
        +metadata: Dict
        +state: Dict
    }

    %% Registry Functions
    class SchemaRegistry {
        <<static>>
        +register_schema_mapper(name, mapper_class)
        +get_schema_mapper(name) SchemaMapper
        +list_schema_mappers() List[str]
    }

    %% Relationships
    SchemaMapper <|-- ClaudeCodeSchemaMapper
    HookInvoker --> InvocationResult
    HookInvoker --> ExitCode
    HookInvoker --> GlobalContext
    HookInvoker --> PluginResult
    InvocationResult --> ExitCode
    SchemaRegistry --> SchemaMapper
    HookInvoker --> SchemaRegistry
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User (Claude Code)
    participant CLI as cpex CLI
    participant HI as HookInvoker
    participant SM as SchemaMapper
    participant PM as PluginManager
    participant P as Plugins

    U->>CLI: cpex invoke --hook tool_pre_invoke --payload {...}
    CLI->>HI: invoke_hook_sync()

    alt Schema Mapping Required
        HI->>SM: map_to_hook_payload()
        SM-->>HI: Transformed payload
    end

    HI->>PM: invoke_hook()
    PM->>P: Execute plugins in phases
    P-->>PM: PluginResult
    PM-->>HI: PluginResult, ContextTable

    alt Schema Mapping Required
        HI->>SM: map_from_hook_result()
        SM-->>HI: Transformed result
    end

    HI->>HI: _determine_exit_code()
    HI-->>CLI: InvocationResult
    CLI->>CLI: format_output()
    CLI-->>U: JSON response + exit code
```

## Features

### 🔧 **Hook Invocation (`cpex invoke`)**
- Execute any registered hook with JSON payloads
- Support for file-based or inline JSON input
- Global context injection for request metadata
- Schema mapping for external tool integration
- Verbose logging and error reporting

### 🔍 **Hook Introspection (`cpex hooks`)**
- **`cpex hooks list`**: List all registered hook types
- **`cpex hooks describe <hook>`**: Show detailed schema information

### 🏗️ **Plugin Development (`mcpplugins`)**
- **`mcpplugins bootstrap`**: Create new plugin projects from templates
- Support for native Python and external plugin templates
- Git-based template system with version control

### 🔄 **Schema Mapping**
- Transform external tool payloads to CPEX format
- Extensible registry for custom schema mappers
- Built-in Claude Code integration
- Bidirectional payload transformation

## Usage Examples

### Basic Hook Invocation
```bash
# Simple tool invocation
cpex invoke --hook tool_pre_invoke --payload '{"name": "search", "args": {"query": "test"}}'

# With custom context
cpex invoke --hook tool_pre_invoke \
  --payload '{"name": "search", "args": {"query": "test"}}' \
  --context '{"request_id": "req-123", "user": "alice"}'

# From files
cpex invoke --hook tool_pre_invoke \
  --payload ./payload.json \
  --context ./context.json
```

### Claude Code Integration
```bash
# Transform Claude Code payload format
cpex invoke --hook tool_pre_invoke \
  --payload '{"tool_name": "search", "arguments": {"query": "test"}}' \
  --schema claude-code
```

### Hook Introspection
```bash
# List all available hooks
cpex hooks list

# Get detailed schema for a hook
cpex hooks describe tool_pre_invoke

# Verbose listing with metadata
cpex hooks list --verbose
```

### Plugin Development
```bash
# Create new native plugin project
mcpplugins bootstrap --destination ./my-plugin --template_type native

# Create external plugin project
mcpplugins bootstrap --destination ./my-external-plugin --template_type external

# Use specific template version
mcpplugins bootstrap --destination ./my-plugin --vcs_ref v1.2.0
```

## Configuration

### Environment Variables
- `PLUGINS_CLI_COMPLETION`: Enable auto-completion (default: false)
- `PLUGINS_CLI_MARKUP_MODE`: Set markup mode (rich/markdown/disabled)

### Configuration Files
- Plugin configuration via YAML files with `--config` option
- Template customization through cookiecutter variables
- Schema mapper registration through Python imports

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | SUCCESS | Hook executed successfully, continue processing |
| 1 | EXECUTION_ERROR | Hook execution failed due to error |
| 2 | BLOCKED_BY_VIOLATION | Hook executed but blocked processing due to violation |
| 3 | CONFIGURATION_ERROR | Configuration, validation, or CLI usage error |

## Extension Points

### Custom Schema Mappers
```python
from cpex.tools.schemas.base import SchemaMapper, register_schema_mapper

class MyToolSchemaMapper(SchemaMapper):
    def map_to_hook_payload(self, external_payload, hook_type):
        # Transform external payload to CPEX format
        return {"name": external_payload["tool_name"], "args": external_payload.get("params", {})}

    def map_from_hook_result(self, hook_result, hook_type):
        # Transform CPEX result to external format
        return {"success": hook_result.continue_processing, "data": hook_result.model_dump()}

# Register the mapper
register_schema_mapper("my-tool", MyToolSchemaMapper)
```

### Plugin Templates
- Add custom templates to the template repository
- Support for both native Python and external plugin types
- Cookiecutter-based templating with variable substitution

## Dependencies

- **Core**: FastAPI, Pydantic, PyYAML, httpx
- **CLI**: typer (rich formatting, auto-completion)
- **Templates**: cookiecutter (optional, for `mcpplugins bootstrap`)
- **Framework**: All CPEX framework components

## Installation

The CLI tools are automatically available when installing CPEX with the `cli` extra:

```bash
pip install cpex[cli]

# Or for development
pip install cpex[cli,dev]
```

Console scripts are registered as:
- `cpex` → `cpex.tools.cpex_cli:main`
- `mcpplugins` → `cpex.tools.cli:main`