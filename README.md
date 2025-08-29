# Target Process MCP Server

An MCP (Model Context Protocol) server for interacting with Target Process/Apptio Targetprocess project management system.

## Features

This MCP server provides tools for:

- **User Stories**: List, view, and search user stories
- **Tasks**: List tasks, create new tasks, update status
- **Bugs**: List and filter bugs by severity and state
- **Projects**: List all projects
- **Iterations**: View sprints/iterations including current sprint
- **Comments**: Add comments to any entity
- **Time Tracking**: Update time spent on tasks/stories
- **Search**: Search across entities by text

## Setup

### 1. Get Your Target Process Credentials

You'll need:
- Your Target Process URL (e.g., `https://yourcompany.tpondemand.com`)
- Either:
  - An API token (recommended)
  - Username and password

To get an API token:
1. Log into Target Process
2. Go to your profile settings
3. Look for "Access Tokens" or "API Tokens"
4. Generate a new token

### 2. Install the MCP Server

```bash
cd ~/Personal/targetprocess-mcp
uv venv --python $(which python3) .venv
uv pip install --python .venv -e .
```

### 3. Configure Claude Code

The server can be configured in two ways:
1. **Environment variables** (takes precedence)
2. **Config file** at `~/.config/targetprocess/config.json` (fallback)

#### Option 1: Using Environment Variables

```bash
# Using global scope (available in all projects)
claude mcp add targetprocess --scope user \
  --env TARGETPROCESS_URL=https://yourcompany.tpondemand.com \
  --env TARGETPROCESS_TOKEN=your-api-token \
  -- /home/joshsymonds/Personal/targetprocess-mcp/.venv/bin/python \
     /home/joshsymonds/Personal/targetprocess-mcp/targetprocess_mcp.py
```

Or with username/password:

```bash
claude mcp add targetprocess --scope user \
  --env TARGETPROCESS_URL=https://yourcompany.tpondemand.com \
  --env TARGETPROCESS_USERNAME=your-email@example.com \
  --env TARGETPROCESS_PASSWORD=your-password \
  -- /home/joshsymonds/Personal/targetprocess-mcp/.venv/bin/python \
     /home/joshsymonds/Personal/targetprocess-mcp/targetprocess_mcp.py
```

#### Option 2: Using Config File

Create a configuration file at `~/.config/targetprocess/config.json`:

```json
{
  "TARGETPROCESS_URL": "https://yourcompany.tpondemand.com",
  "TARGETPROCESS_TOKEN": "your-api-token"
}
```

Or with username/password:

```json
{
  "TARGETPROCESS_URL": "https://yourcompany.tpondemand.com",
  "TARGETPROCESS_USERNAME": "your-email@example.com",
  "TARGETPROCESS_PASSWORD": "your-password"
}
```

Then add the server without environment variables:

```bash
claude mcp add targetprocess --scope user \
  -- /home/joshsymonds/Personal/targetprocess-mcp/.venv/bin/python \
     /home/joshsymonds/Personal/targetprocess-mcp/targetprocess_mcp.py
```

#### Configuration Priority

The server checks for configuration in this order:
1. Environment variables (highest priority)
2. `~/.config/targetprocess/config.json` file (fallback)
3. Mix of both (e.g., URL from env var, token from config file)

## Usage Examples

Once connected, you can ask Claude Code to:

### View Work Items
- "Show me all open user stories"
- "List my tasks for the current sprint"
- "Show me critical bugs in Project X"
- "Get details for story #12345"

### Update Status
- "Move task #456 to In Progress"
- "Mark story #789 as Done"
- "Add a comment to bug #321 saying we need more info"

### Time Tracking
- "Log 2 hours on task #456"
- "Update time spent on story #789 to 5 hours"

### Search and Filter
- "Find all stories mentioning 'authentication'"
- "Show me tasks assigned to Josh"
- "List stories in the current iteration"
- "Show me all bugs with severity Critical"

### Create New Items
- "Create a new task for story #123 called 'Update documentation'"
- "Add a task to story #456 with 3 hours estimated effort"

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_user_stories` | List user stories with filters | project_id, iteration_id, state, where_clause, limit |
| `get_user_story` | Get detailed story information | story_id |
| `list_tasks` | List tasks with filters | story_id, state, where_clause, limit |
| `list_bugs` | List bugs with filters | project_id, state, severity, where_clause, limit |
| `list_assignments` | **Find work assigned to users** | user_id, user_email, entity_type, state, project_id, limit |
| `get_logged_user` | Get current user info | - |
| `create_task` | Create a new task | name, story_id, description, assigned_user_id, effort |
| `update_entity_state` | Change status of any entity | entity_type, entity_id, state_name |
| `add_comment` | Add comment to any entity | entity_type, entity_id, comment |
| `update_time_spent` | Log time on entity | entity_type, entity_id, hours |
| `list_projects` | List all projects | - |
| `list_iterations` | List iterations/sprints | project_id, is_current |
| `search_entities` | Search by text | query, entity_types, limit |

## Important: Finding Assigned Work

To find work assigned to a specific user, use the `list_assignments` tool, NOT the `assigned_to` parameter on other tools. Target Process uses a complex many-to-many relationship for assignments.

**Correct approach:**
1. First, get your user info: `get_logged_user`
2. Then use: `list_assignments` with your user_id or user_email

**Example:**
```
# First get your user ID
get_logged_user()
# Returns: {"Id": 166, "Email": "jsymonds@liveworld.com", ...}

# Then get your assignments
list_assignments(user_email="jsymonds@liveworld.com", state="In Progress")
```

## Advanced Filtering with where_clause

The `where_clause` parameter on list tools allows you to use Target Process's query syntax directly:

### Filter Operators
- `eq` - equals: `EntityState.Name eq 'Open'`
- `ne` - not equals: `Priority.Name ne 'Low'`
- `gt` - greater than: `CreateDate gt '2024-01-01'`
- `lt` - less than: `Effort lt 10`
- `gte` - greater or equal: `TimeSpent gte 5`
- `lte` - less or equal: `Id lte 1000`
- `contains` - text contains: `Name contains 'API'`
- `in` - in list: `Id in (123, 456, 789)`
- `is null` / `is not null` - null checks: `Description is not null`

### Common Filter Examples

**By date range:**
```
where_clause="(CreateDate gt '2024-01-01') and (CreateDate lt '2024-12-31')"
```

**By tags:**
```
where_clause="Tags contains 'urgent'"
where_clause="Tags contains '*backend*'"  # Wildcards supported
```

**By custom fields:**
```
where_clause="CustomFields.Browser eq 'Firefox'"
where_clause="'CustomFields.Release Notes' is not null"  # Note quotes for fields with spaces
```

**Complex combinations:**
```
where_clause="(Project.Name contains 'Mobile') and (EntityState.Name eq 'In Progress') and (Priority.Importance lte 3)"
```

## API Details

This server uses Target Process REST API v1:
- Authentication: Basic auth with token or username/password
- Format: JSON
- Base endpoint: `/api/v1/`

Supported entity types:
- UserStories
- Tasks
- Bugs
- Projects
- Iterations
- Comments
- EntityStates

## Troubleshooting

### Connection Issues
1. Verify your Target Process URL is correct (including https://)
2. Check your API token is valid and has appropriate permissions
3. Test connection: `claude mcp list`

### Authentication Errors
- API tokens should be used with empty username (just `:token` in basic auth)
- Passwords may need to be URL-encoded if they contain special characters
- Some Target Process instances may require specific permissions for API access

### Missing Data
- The API respects Target Process permissions - you'll only see items you have access to
- Some fields may be null if not set in Target Process
- Use the `include` parameter in API calls to fetch related data

## Development

To modify the server:

1. Edit `~/Personal/targetprocess-mcp/targetprocess_mcp.py`
2. The server will reload automatically when Claude Code restarts
3. Test changes with `claude mcp list`

To add new entity types or operations:
1. Add new tool functions with `@server.tool()` decorator
2. Use the `TargetProcessClient` class for API calls
3. Follow the existing pattern for filters and includes

## Security Notes

- Never commit credentials to version control
- API tokens are preferred over passwords
- The `.venv/` directory is gitignored
- Store credentials in `~/.config/targetprocess/config.json`
- Consider using read-only API tokens where possible