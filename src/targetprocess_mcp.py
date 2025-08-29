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

        # Setup authentication headers
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if config.token:
            self.headers["Authorization"] = (
                f"Basic {base64.b64encode(f':{config.token}'.encode()).decode()}"
            )
        elif config.username and config.password:
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
    username = os.getenv("TARGETPROCESS_USERNAME")
    password = os.getenv("TARGETPROCESS_PASSWORD")

    # If environment variables are not complete, try config file
    if not base_url or (not token and not (username and password)):
        config_data = load_config_from_file()

        # Use config file values if env vars are missing
        base_url = base_url or config_data.get("TARGETPROCESS_URL")
        token = token or config_data.get("TARGETPROCESS_TOKEN")
        username = username or config_data.get("TARGETPROCESS_USERNAME")
        password = password or config_data.get("TARGETPROCESS_PASSWORD")

    if not base_url:
        raise ValueError(
            "TARGETPROCESS_URL not found in environment variables or ~/.config/targetprocess/config.json"
        )

    if not token and not (username and password):
        raise ValueError(
            "Either TARGETPROCESS_TOKEN or TARGETPROCESS_USERNAME/PASSWORD is required "
            "(check environment variables or ~/.config/targetprocess/config.json)"
        )

    config = TargetProcessConfig(
        base_url=base_url, token=token, username=username, password=password
    )

    tp_client = TargetProcessClient(config)
    logger.info(f"Initialized Target Process client for {base_url}")


# Tool definitions


@server.tool()
async def list_user_stories(
    project_id: Optional[int] = None,
    iteration_id: Optional[int] = None,
    state: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    List user stories from Target Process

    Args:
        project_id: Filter by project ID
        iteration_id: Filter by iteration ID
        state: Filter by state (e.g., "Open", "In Progress", "Done")
        assigned_to: Filter by assigned user email or name
        limit: Maximum number of results to return
    """
    if not tp_client:
        init_client()

    where_clauses = []
    if project_id:
        where_clauses.append(f"Project.Id eq {project_id}")
    if iteration_id:
        where_clauses.append(f"Iteration.Id eq {iteration_id}")
    if state:
        where_clauses.append(f"EntityState.Name eq '{state}'")
    if assigned_to:
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
    limit: int = 50,
) -> str:
    """
    List tasks from Target Process

    Args:
        story_id: Filter by user story ID
        assigned_to: Filter by assigned user email or name
        state: Filter by state (e.g., "Open", "In Progress", "Done")
        limit: Maximum number of results to return
    """
    if not tp_client:
        init_client()

    where_clauses = []
    if story_id:
        where_clauses.append(f"UserStory.Id eq {story_id}")
    if assigned_to:
        where_clauses.append(
            f"(AssignedUser.Email eq '{assigned_to}' or AssignedUser.FirstName eq '{assigned_to}')"
        )
    if state:
        where_clauses.append(f"EntityState.Name eq '{state}'")

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
    limit: int = 50,
) -> str:
    """
    List bugs from Target Process

    Args:
        project_id: Filter by project ID
        state: Filter by state (e.g., "Open", "In Progress", "Done")
        severity: Filter by severity (e.g., "Critical", "Major", "Minor")
        assigned_to: Filter by assigned user email or name
        limit: Maximum number of results to return
    """
    if not tp_client:
        init_client()

    where_clauses = []
    if project_id:
        where_clauses.append(f"Project.Id eq {project_id}")
    if state:
        where_clauses.append(f"EntityState.Name eq '{state}'")
    if severity:
        where_clauses.append(f"Severity.Name eq '{severity}'")
    if assigned_to:
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
