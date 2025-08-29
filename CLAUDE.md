# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server for interacting with Target Process/Apptio Targetprocess project management system. The server provides tools for managing user stories, tasks, bugs, projects, iterations, comments, and time tracking through the Target Process REST API.

## Development Commands

### Setup and Installation
```bash
# Create virtual environment
uv venv --python $(which python3) .venv

# Install dependencies
uv pip install --python .venv -e .
```

### Running the Server
```bash
# Direct execution
.venv/bin/python targetprocess_mcp.py

# Or via installed script
.venv/bin/targetprocess-mcp
```

### Code Formatting and Quality
```bash
# Format code with black
black src/targetprocess_mcp.py

# Run tests (when available)
pytest
```

## Architecture

### Core Components

1. **MCP Server** (`targetprocess_mcp.py`)
   - Single-file implementation containing all server logic
   - Uses the `mcp` library for MCP protocol implementation
   - Async/await pattern throughout for API calls

2. **TargetProcessClient Class** 
   - Handles all HTTP communication with Target Process API
   - Manages authentication (API token or basic auth)
   - Base methods: `get_entities()`, `get_entity_by_id()`, `create_entity()`, `update_entity()`, `add_comment()`

3. **Tool Functions**
   - Each decorated with `@server.tool()` 
   - Async functions that use the TargetProcessClient
   - Return JSON-formatted strings for MCP protocol

### Authentication Flow
- Credentials loaded from environment variables: `TARGETPROCESS_URL`, `TARGETPROCESS_TOKEN` or `TARGETPROCESS_USERNAME/PASSWORD`
- Client initialized on first tool call via `init_client()`
- Basic auth header constructed with base64 encoding

### API Patterns
- Target Process REST API v1 endpoint: `/api/v1/`
- Query parameters: `format=json`, `take`, `where`, `include`
- Entity types: UserStories, Tasks, Bugs, Projects, Iterations, Comments, EntityStates
- Include syntax for related data: `[field1,field2,relation[subfield1,subfield2]]`

## Key Implementation Details

### Adding New Tools
1. Define async function with `@server.tool()` decorator
2. Add typed parameters with clear descriptions
3. Call `init_client()` if `tp_client` is None
4. Use `tp_client` methods for API calls
5. Return JSON-formatted string

### Error Handling
- HTTP errors propagate via `response.raise_for_status()`
- Missing credentials checked in `init_client()`
- Entity not found returns error in JSON response

### Where Clause Construction
- Build list of conditions and join with " and "
- Use `eq` for equality, `contains` for text search
- Quote string values, don't quote numbers
- Example: `"Project.Id eq 123 and EntityState.Name eq 'Open'"`

## Environment Configuration

Configuration can be provided via environment variables or a config file at `~/.config/targetprocess/config.json`.

Priority order (highest to lowest):
1. Environment variables
2. Config file (`~/.config/targetprocess/config.json`)
3. Mix of both (e.g., URL from env, token from config file)

Required configuration:
- `TARGETPROCESS_URL`: Base URL of Target Process instance
- Authentication (one of):
  - `TARGETPROCESS_TOKEN`: API token (preferred)
  - `TARGETPROCESS_USERNAME` and `TARGETPROCESS_PASSWORD`: Basic auth credentials

Config file example:
```json
{
  "TARGETPROCESS_URL": "https://company.tpondemand.com",
  "TARGETPROCESS_TOKEN": "your-api-token"
}
```

## Dependencies

- `mcp>=1.5.0`: MCP protocol implementation
- `httpx>=0.27.0`: Async HTTP client
- `python-dotenv>=1.0.0`: Environment variable loading
- Python 3.10+ required

## Testing Approach

When adding new features:
1. Test API calls manually first using curl or httpx
2. Verify response structure matches expectations
3. Handle edge cases (missing data, null values)
4. Test filter combinations in where clauses