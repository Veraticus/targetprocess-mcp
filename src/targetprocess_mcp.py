#!/usr/bin/env python3
"""
Target Process MCP Server

Provides MCP tools for interacting with Target Process/Apptio Targetprocess.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, quote
import base64

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TargetProcessConfig(BaseModel):
    """Configuration for Target Process connection"""

    base_url: str = Field(
        description="Target Process instance URL (e.g., https://company.tpondemand.com)"
    )
    token: Optional[str] = Field(None, description="API token for authentication")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")


class TargetProcessClient:
    """Client for interacting with Target Process REST API"""

    def __init__(self, config: TargetProcessConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_v1_url = f"{self.base_url}/api/v1"
        self.api_v2_url = f"{self.base_url}/api/v2"
        
        # Store token for URL parameter or prepare headers for basic auth
        self.access_token = config.token
        
        # Setup headers
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Only use Authorization header for username/password auth
        if not self.access_token and config.username and config.password:
            credentials = base64.b64encode(
                f"{config.username}:{config.password}".encode()
            ).decode()
            self.headers["Authorization"] = f"Basic {credentials}"

    async def get_entities(
        self,
        entity_type: str,
        where: Optional[str] = None,
        include: Optional[str] = None,
        take: int = 100,
    ) -> Dict[str, Any]:
        """Get entities from Target Process"""
        params = {"format": "json", "take": str(take)}
        if where:
            params["where"] = where
        if include:
            params["include"] = include
        
        # Add access_token to params if using token auth
        if self.access_token:
            params["access_token"] = self.access_token

        url = f"{self.api_v1_url}/{entity_type}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_entity_by_id(
        self, entity_type: str, entity_id: int, include: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a specific entity by ID"""
        params = {"format": "json"}
        if include:
            params["include"] = include
        
        # Add access_token to params if using token auth
        if self.access_token:
            params["access_token"] = self.access_token

        url = f"{self.api_v1_url}/{entity_type}/{entity_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def create_entity(
        self, entity_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new entity"""
        url = f"{self.api_v1_url}/{entity_type}"
        params = {"format": "json"}
        
        # Add access_token to params if using token auth
        if self.access_token:
            params["access_token"] = self.access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=self.headers, params=params, json=data
            )
            response.raise_for_status()
            return response.json()

    async def update_entity(
        self, entity_type: str, entity_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing entity"""
        url = f"{self.api_v1_url}/{entity_type}/{entity_id}"
        params = {"format": "json"}
        
        # Add access_token to params if using token auth
        if self.access_token:
            params["access_token"] = self.access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=self.headers, params=params, json=data
            )
            response.raise_for_status()
            return response.json()

    async def add_comment(
        self, entity_type: str, entity_id: int, comment: str
    ) -> Dict[str, Any]:
        """Add a comment to an entity"""
        url = f"{self.api_v1_url}/Comment"
        params = {"format": "json"}
        
        # Add access_token to params if using token auth
        if self.access_token:
            params["access_token"] = self.access_token

        data = {"Description": comment, "General": {"Id": entity_id}}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=self.headers, params=params, json=data
            )
            response.raise_for_status()
            return response.json()


# Initialize MCP server
server = FastMCP("targetprocess-mcp")
tp_client: Optional[TargetProcessClient] = None


def load_config_from_file():
    """Load configuration from ~/.config/targetprocess/config.json"""
    import pathlib

    config_path = pathlib.Path.home() / ".config" / "targetprocess" / "config.json"

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                return config_data
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return {}

    return {}


def init_client():
    """Initialize Target Process client from environment variables or config file"""
    global tp_client

    # First try environment variables
    base_url = os.getenv("TARGETPROCESS_URL")
    token = os.getenv("TARGETPROCESS_TOKEN")

    # If environment variables are not complete, try config file
    if not base_url or not token:
        config_data = load_config_from_file()

        # Use config file values if env vars are missing
        base_url = base_url or config_data.get("TARGETPROCESS_URL")
        token = token or config_data.get("TARGETPROCESS_TOKEN")

    if not base_url:
        raise ValueError(
            "TARGETPROCESS_URL not found in environment variables or ~/.config/targetprocess/config.json"
        )

    if not token:
        raise ValueError(
            "TARGETPROCESS_TOKEN is required "
            "(check environment variables or ~/.config/targetprocess/config.json)"
        )

    config = TargetProcessConfig(base_url=base_url, token=token)

    tp_client = TargetProcessClient(config)
    logger.info(f"Initialized Target Process client for {base_url}")


# Tool definitions


@server.tool()
async def list_user_stories(
    project_id: Optional[int] = None,
    iteration_id: Optional[int] = None,
    state: Optional[str] = None,
    assigned_to: Optional[str] = None,
    where_clause: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    List user stories from Target Process

    Args:
        project_id: Filter by project ID
        iteration_id: Filter by iteration ID
        state: Filter by state name (e.g., "Open", "In Progress", "Done")
        assigned_to: [Note: Complex field - use where_clause for filtering by assignments]
        where_clause: Custom Target Process filter (e.g., "EntityState.Name eq 'Open' and Project.Id eq 123")
                     Examples:
                     - "EntityState.Name eq 'In Progress'"
                     - "Project.Name contains 'Mobile'"
                     - "CreateDate gt '2024-01-01'"
                     - "Tags contains 'urgent'"
        limit: Maximum number of results to return (max 1000)
    
    Note: User assignments in Target Process are complex. To filter by assigned user,
    consider using the Assignments endpoint or search_entities instead.
    """
    if not tp_client:
        init_client()

    where_clauses = []
    if where_clause:
        where_clauses.append(where_clause)
    if project_id:
        where_clauses.append(f"Project.Id eq {project_id}")
    if iteration_id:
        where_clauses.append(f"Iteration.Id eq {iteration_id}")
    if state:
        where_clauses.append(f"EntityState.Name eq '{state}'")
    # Note: assigned_to is kept for backward compatibility but may not work as expected
    if assigned_to:
        logger.warning("assigned_to filter may not work as expected. Consider using search_entities or custom where_clause.")
        where_clauses.append(
            f"(AssignedUser.Email eq '{assigned_to}' or AssignedUser.FirstName eq '{assigned_to}')"
        )

    where = " and ".join(where_clauses) if where_clauses else None
    include = "[Id,Name,Description,EntityState,Project[Name],Iteration[Name],AssignedUser[FirstName,LastName,Email],Effort,TimeSpent,CreateDate,ModifyDate]"

    result = await tp_client.get_entities(
        "UserStories", where=where, include=include, take=limit
    )

    return json.dumps(result, indent=2)


@server.tool()
async def get_user_story(story_id: int) -> str:
    """
    Get details of a specific user story

    Args:
        story_id: The ID of the user story
    """
    if not tp_client:
        init_client()

    include = "[Id,Name,Description,EntityState,Project[Name],Iteration[Name],Release[Name],AssignedUser[FirstName,LastName,Email],Effort,TimeSpent,CreateDate,ModifyDate,Comments[Description,Owner[FirstName,LastName],CreateDate]]"

    result = await tp_client.get_entity_by_id("UserStory", story_id, include=include)

    return json.dumps(result, indent=2)


@server.tool()
async def list_tasks(
    story_id: Optional[int] = None,
    assigned_to: Optional[str] = None,
    state: Optional[str] = None,
    where_clause: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    List tasks from Target Process

    Args:
        story_id: Filter by user story ID
        assigned_to: [Note: Complex field - use where_clause for filtering by assignments]
        state: Filter by state name (e.g., "New", "In Progress", "Done")
        where_clause: Custom Target Process filter (e.g., "UserStory.Id eq 123 and EntityState.Name eq 'Open'")
                     See list_user_stories for more examples
        limit: Maximum number of results to return (max 1000)
    """
    if not tp_client:
        init_client()

    where_clauses = []
    if where_clause:
        where_clauses.append(where_clause)
    if story_id:
        where_clauses.append(f"UserStory.Id eq {story_id}")
    if state:
        where_clauses.append(f"EntityState.Name eq '{state}'")
    # Note: assigned_to is kept for backward compatibility but may not work as expected
    if assigned_to:
        logger.warning("assigned_to filter may not work as expected. Consider using search_entities or custom where_clause.")
        where_clauses.append(
            f"(AssignedUser.Email eq '{assigned_to}' or AssignedUser.FirstName eq '{assigned_to}')"
        )

    where = " and ".join(where_clauses) if where_clauses else None
    include = "[Id,Name,Description,EntityState,UserStory[Id,Name],AssignedUser[FirstName,LastName,Email],Effort,TimeSpent,CreateDate,ModifyDate]"

    result = await tp_client.get_entities(
        "Tasks", where=where, include=include, take=limit
    )

    return json.dumps(result, indent=2)


@server.tool()
async def list_bugs(
    project_id: Optional[int] = None,
    state: Optional[str] = None,
    severity: Optional[str] = None,
    assigned_to: Optional[str] = None,
    where_clause: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    List bugs from Target Process

    Args:
        project_id: Filter by project ID
        state: Filter by state name (e.g., "Open", "In Progress", "Done")
        severity: Filter by severity (e.g., "Critical", "Major", "Minor")
        assigned_to: [Note: Complex field - use where_clause for filtering by assignments]
        where_clause: Custom Target Process filter - see list_user_stories for examples
        limit: Maximum number of results to return (max 1000)
    """
    if not tp_client:
        init_client()

    where_clauses = []
    if where_clause:
        where_clauses.append(where_clause)
    if project_id:
        where_clauses.append(f"Project.Id eq {project_id}")
    if state:
        where_clauses.append(f"EntityState.Name eq '{state}'")
    if severity:
        where_clauses.append(f"Severity.Name eq '{severity}'")
    # Note: assigned_to is kept for backward compatibility but may not work as expected
    if assigned_to:
        logger.warning("assigned_to filter may not work as expected. Consider using search_entities or custom where_clause.")
        where_clauses.append(
            f"(AssignedUser.Email eq '{assigned_to}' or AssignedUser.FirstName eq '{assigned_to}')"
        )

    where = " and ".join(where_clauses) if where_clauses else None
    include = "[Id,Name,Description,EntityState,Severity,Project[Name],AssignedUser[FirstName,LastName,Email],CreateDate,ModifyDate]"

    result = await tp_client.get_entities(
        "Bugs", where=where, include=include, take=limit
    )

    return json.dumps(result, indent=2)


@server.tool()
async def create_user_story(
    name: str,
    project_id: int,
) -> str:
    """
    Create a new user story in Target Process

    Args:
        name: User story name
        project_id: ID of the project
    
    Note: To add description, assignments, or effort, update the story after creation
    """
    if not tp_client:
        init_client()

    data = {"Name": name, "Project": {"Id": project_id}}

    result = await tp_client.create_entity("UserStories", data)

    return json.dumps(result, indent=2)


@server.tool()
async def create_task(
    name: str,
    story_id: int,
    description: Optional[str] = None,
    assigned_user_id: Optional[int] = None,
    effort: Optional[float] = None,
) -> str:
    """
    Create a new task in Target Process

    Args:
        name: Task name
        story_id: ID of the parent user story
        description: Task description
        assigned_user_id: ID of user to assign the task to
        effort: Estimated effort in hours
    """
    if not tp_client:
        init_client()

    data = {"Name": name, "UserStory": {"Id": story_id}}

    if description:
        data["Description"] = description
    if assigned_user_id:
        data["AssignedUser"] = {"Id": assigned_user_id}
    if effort:
        data["Effort"] = effort

    result = await tp_client.create_entity("Task", data)

    return json.dumps(result, indent=2)


@server.tool()
async def update_entity_state(entity_type: str, entity_id: int, state_name: str) -> str:
    """
    Update the state of an entity (UserStory, Task, Bug)

    Args:
        entity_type: Type of entity (UserStory, Task, or Bug)
        entity_id: ID of the entity
        state_name: New state name (e.g., "In Progress", "Done")
    """
    if not tp_client:
        init_client()

    # First get the state ID
    states = await tp_client.get_entities(
        "EntityStates", where=f"Name eq '{state_name}'", take=1
    )

    if not states.get("Items"):
        return json.dumps({"error": f"State '{state_name}' not found"})

    state_id = states["Items"][0]["Id"]

    data = {"EntityState": {"Id": state_id}}

    result = await tp_client.update_entity(entity_type, entity_id, data)

    return json.dumps(result, indent=2)


@server.tool()
async def add_comment(entity_type: str, entity_id: int, comment: str) -> str:
    """
    Add a comment to an entity

    Args:
        entity_type: Type of entity (UserStory, Task, Bug, etc.)
        entity_id: ID of the entity
        comment: Comment text to add
    """
    if not tp_client:
        init_client()

    result = await tp_client.add_comment(entity_type, entity_id, comment)

    return json.dumps(result, indent=2)


@server.tool()
async def update_time_spent(entity_type: str, entity_id: int, hours: float) -> str:
    """
    Update time spent on an entity

    Args:
        entity_type: Type of entity (UserStory, Task, Bug)
        entity_id: ID of the entity
        hours: Hours spent
    """
    if not tp_client:
        init_client()

    # Get current time spent
    entity = await tp_client.get_entity_by_id(
        entity_type, entity_id, include="[TimeSpent]"
    )
    current_time = entity.get("TimeSpent", 0) or 0

    data = {"TimeSpent": current_time + hours}

    result = await tp_client.update_entity(entity_type, entity_id, data)

    return json.dumps(result, indent=2)


@server.tool()
async def list_projects() -> str:
    """List all projects in Target Process"""
    if not tp_client:
        init_client()

    include = "[Id,Name,Description,IsActive,StartDate,EndDate]"
    result = await tp_client.get_entities("Projects", include=include, take=100)

    return json.dumps(result, indent=2)


@server.tool()
async def list_iterations(
    project_id: Optional[int] = None, is_current: bool = False
) -> str:
    """
    List iterations/sprints

    Args:
        project_id: Filter by project ID
        is_current: If True, only show current iteration
    """
    if not tp_client:
        init_client()

    where_clauses = []
    if project_id:
        where_clauses.append(f"Project.Id eq {project_id}")
    if is_current:
        where_clauses.append("IsCurrent eq 'true'")

    where = " and ".join(where_clauses) if where_clauses else None
    include = "[Id,Name,StartDate,EndDate,IsCurrent,Project[Name]]"

    result = await tp_client.get_entities(
        "Iterations", where=where, include=include, take=100
    )

    return json.dumps(result, indent=2)


@server.tool()
async def list_assignments(
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    entity_type: Optional[str] = None,
    state: Optional[str] = None,
    project_id: Optional[int] = None,
    limit: int = 50,
) -> str:
    """
    List assignments for a specific user - THIS IS THE PROPER WAY TO FIND ASSIGNED WORK
    
    Args:
        user_id: The ID of the user to get assignments for
        user_email: The email of the user (alternative to user_id)
        entity_type: Filter by entity type (e.g., "UserStory", "Task", "Bug")
        state: Filter by state name (e.g., "Open", "In Progress", "Done")
        project_id: Filter by project ID
        limit: Maximum number of results to return
        
    Note: This queries the Assignments endpoint which properly handles the many-to-many
    relationship between users and assignable entities in Target Process.
    """
    if not tp_client:
        init_client()
    
    where_clauses = []
    
    # Filter by user
    if user_id:
        where_clauses.append(f"GeneralUser.Id eq {user_id}")
    elif user_email:
        where_clauses.append(f"GeneralUser.Email eq '{user_email}'")
    
    # Filter by entity type
    if entity_type:
        where_clauses.append(f"Assignable.EntityType.Name eq '{entity_type}'")
    
    # Filter by state
    if state:
        where_clauses.append(f"Assignable.EntityState.Name eq '{state}'")
        
    # Filter by project
    if project_id:
        where_clauses.append(f"Assignable.Project.Id eq {project_id}")
    
    where = " and ".join(where_clauses) if where_clauses else None
    include = "[GeneralUser[Id,FirstName,LastName,Email],Assignable[Id,Name,EntityType,EntityState,Project[Name],CreateDate,ModifyDate]]"
    
    result = await tp_client.get_entities(
        "Assignments", where=where, include=include, take=limit
    )
    
    return json.dumps(result, indent=2)


@server.tool()
async def get_logged_user() -> str:
    """
    Get information about the currently authenticated user
    
    Returns details about the user associated with the current access token.
    This is useful for finding your own user ID to use with other queries.
    """
    if not tp_client:
        init_client()
    
    result = await tp_client.get_entity_by_id(
        "Users", 
        "LoggedUser",
        include="[Id,FirstName,LastName,Email,Login,IsActive,IsAdministrator]"
    )
    
    return json.dumps(result, indent=2)


@server.tool()
async def search_entities(
    query: str, entity_types: Optional[List[str]] = None, limit: int = 20
) -> str:
    """
    Search for entities by text

    Args:
        query: Search query
        entity_types: List of entity types to search (default: UserStory, Task, Bug)
        limit: Maximum results per entity type
    """
    if not tp_client:
        init_client()

    if not entity_types:
        entity_types = ["UserStories", "Tasks", "Bugs"]

    results = {}

    for entity_type in entity_types:
        where = f"Name contains '{query}' or Description contains '{query}'"
        include = "[Id,Name,EntityState,Project[Name]]"

        try:
            result = await tp_client.get_entities(
                entity_type, where=where, include=include, take=limit
            )
            results[entity_type] = result.get("Items", [])
        except Exception as e:
            results[entity_type] = {"error": str(e)}

    return json.dumps(results, indent=2)


@server.tool()
async def update_user_story(
    story_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    state_id: Optional[int] = None,
    effort: Optional[float] = None,
    iteration_id: Optional[int] = None,
) -> str:
    """
    Update an existing user story
    
    Args:
        story_id: ID of the user story to update
        name: New name for the story
        description: New description (markdown format)
        state_id: ID of the new entity state (use get_entity_states to find valid IDs)
        effort: New effort estimate
        iteration_id: ID of iteration to assign to
    """
    if not tp_client:
        init_client()
    
    data = {}
    if name:
        data["Name"] = name
    if description:
        data["Description"] = description
    if state_id:
        data["EntityState"] = {"Id": state_id}
    if effort is not None:
        data["Effort"] = effort
    if iteration_id:
        data["Iteration"] = {"Id": iteration_id}
    
    if not data:
        return json.dumps({"error": "No fields to update"})
    
    result = await tp_client.update_entity("UserStories", story_id, data)
    return json.dumps(result, indent=2)


@server.tool()
async def get_entity_states(
    entity_type: str = "UserStory",
    process_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> str:
    """
    Get available entity states for a specific entity type and process
    
    Args:
        entity_type: Type of entity (UserStory, Task, Bug)
        process_id: Filter by process ID
        project_id: Get states for the process of a specific project
        
    Returns states with their IDs that can be used in updates
    """
    if not tp_client:
        init_client()
    
    where_clauses = [f"EntityType.Name eq '{entity_type}'"]
    
    if process_id:
        where_clauses.append(f"Process.Id eq {process_id}")
    elif project_id:
        # First get the project's process
        project = await tp_client.get_entity_by_id(
            "Projects", project_id, include="[Process]"
        )
        if project and project.get("Process"):
            process_id = project["Process"]["Id"]
            where_clauses.append(f"Process.Id eq {process_id}")
    
    where = " and ".join(where_clauses)
    include = "[Id,Name,NumericPriority,Process[Id,Name],EntityType[Name]]"
    
    result = await tp_client.get_entities(
        "EntityStates", where=where, include=include, take=100
    )
    
    # Format the output for easy reading
    if result.get("Items"):
        formatted_states = []
        for state in result["Items"]:
            formatted_states.append({
                "Id": state["Id"],
                "Name": state["Name"],
                "Priority": state.get("NumericPriority", 0),
                "Process": state.get("Process", {}).get("Name", "Unknown")
            })
        result["Items"] = sorted(formatted_states, key=lambda x: x["Priority"])
    
    return json.dumps(result, indent=2)


@server.tool()
async def delete_entity(
    entity_type: str,
    entity_id: int,
    use_done_state: bool = True,
) -> str:
    """
    Mark an entity as deleted/done (Target Process doesn't support hard delete via API)
    
    Args:
        entity_type: Type of entity (UserStory, Task, Bug)
        entity_id: ID of the entity to delete
        use_done_state: If True, sets to Done state; if False, tries to find Deleted/Cancelled state
        
    Note: This doesn't actually delete the entity but marks it as Done/Completed
    """
    if not tp_client:
        init_client()
    
    # Get the entity to find its process
    entity_plural = entity_type if entity_type.endswith("ies") else f"{entity_type}s"
    entity = await tp_client.get_entity_by_id(
        entity_plural, entity_id, include="[Project[Process]]"
    )
    
    if not entity:
        return json.dumps({"error": f"{entity_type} {entity_id} not found"})
    
    process_id = entity.get("Project", {}).get("Process", {}).get("Id")
    if not process_id:
        return json.dumps({"error": "Could not determine process for entity"})
    
    # Find appropriate state
    state_names = ["Done", "Completed", "Closed"] if use_done_state else ["Deleted", "Cancelled", "Rejected"]
    
    for state_name in state_names:
        states = await tp_client.get_entities(
            "EntityStates",
            where=f"EntityType.Name eq '{entity_type}' and Process.Id eq {process_id} and Name eq '{state_name}'",
            take=1
        )
        
        if states.get("Items"):
            state_id = states["Items"][0]["Id"]
            data = {"EntityState": {"Id": state_id}}
            result = await tp_client.update_entity(entity_plural, entity_id, data)
            result["Note"] = f"Entity marked as {state_name}"
            return json.dumps(result, indent=2)
    
    # If no suitable state found, list available states
    available_states = await get_entity_states(entity_type, process_id=process_id)
    return json.dumps({
        "error": f"No suitable deletion state found for {entity_type} in this process",
        "available_states": json.loads(available_states).get("Items", [])
    })


def main():
    """Main entry point for the MCP server"""
    import sys

    # Initialize client on startup
    try:
        init_client()
    except ValueError as e:
        logger.error(f"Failed to initialize Target Process client: {e}")
        logger.info(
            "Please set TARGETPROCESS_URL and either TARGETPROCESS_TOKEN or TARGETPROCESS_USERNAME/PASSWORD"
        )
        sys.exit(1)

    # Start the server
    server.run()


if __name__ == "__main__":
    main()
