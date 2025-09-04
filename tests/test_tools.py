"""Tests for MCP tool functions"""

import pytest
import json
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import targetprocess_mcp


@pytest.fixture
def mock_client():
    """Create a mock TargetProcessClient"""
    client = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up required environment variables"""
    os.environ["TARGETPROCESS_URL"] = "https://test.tpondemand.com"
    os.environ["TARGETPROCESS_TOKEN"] = "test_token"
    yield
    targetprocess_mcp.tp_client = None


class TestToolFunctions:
    @pytest.mark.asyncio
    async def test_list_user_stories(self, mock_client):
        """Test listing user stories"""
        mock_client.get_entities.return_value = {
            "Items": [
                {"Id": 1, "Name": "Story 1", "EntityState": {"Name": "Open"}},
                {"Id": 2, "Name": "Story 2", "EntityState": {"Name": "Done"}},
            ]
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.list_user_stories(
                project_id=10, state="Open", limit=20
            )

            result_data = json.loads(result)
            assert len(result_data["Items"]) == 2
            assert result_data["Items"][0]["Name"] == "Story 1"

            mock_client.get_entities.assert_called_once_with(
                "UserStories",
                where="Project.Id eq 10 and EntityState.Name eq 'Open'",
                include="[Id,Name,Description,EntityState,Project[Name],Iteration[Name],AssignedUser[FirstName,LastName,Email],Effort,TimeSpent,CreateDate,ModifyDate]",
                take=20,
            )

    @pytest.mark.asyncio
    async def test_get_user_story(self, mock_client):
        """Test getting a specific user story"""
        mock_client.get_entity_by_id.return_value = {
            "Id": 123,
            "Name": "Test Story",
            "Description": "Story description",
            "EntityState": {"Name": "In Progress"},
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.get_user_story(123)

            result_data = json.loads(result)
            assert result_data["Id"] == 123
            assert result_data["Name"] == "Test Story"

            mock_client.get_entity_by_id.assert_called_once_with(
                "UserStory",
                123,
                include="[Id,Name,Description,EntityState,Project[Name],Iteration[Name],Release[Name],AssignedUser[FirstName,LastName,Email],Effort,TimeSpent,CreateDate,ModifyDate,Comments[Description,Owner[FirstName,LastName],CreateDate]]",
            )

    @pytest.mark.asyncio
    async def test_list_tasks(self, mock_client):
        """Test listing tasks"""
        mock_client.get_entities.return_value = {
            "Items": [
                {"Id": 10, "Name": "Task 1", "EntityState": {"Name": "Open"}},
                {"Id": 11, "Name": "Task 2", "EntityState": {"Name": "In Progress"}},
            ]
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.list_tasks(
                story_id=123, state="Open", limit=30
            )

            result_data = json.loads(result)
            assert len(result_data["Items"]) == 2
            assert result_data["Items"][0]["Name"] == "Task 1"

            mock_client.get_entities.assert_called_once_with(
                "Tasks",
                where="UserStory.Id eq 123 and EntityState.Name eq 'Open'",
                include="[Id,Name,Description,EntityState,UserStory[Id,Name],AssignedUser[FirstName,LastName,Email],Effort,TimeSpent,CreateDate,ModifyDate]",
                take=30,
            )

    @pytest.mark.asyncio
    async def test_list_bugs(self, mock_client):
        """Test listing bugs"""
        mock_client.get_entities.return_value = {
            "Items": [
                {"Id": 20, "Name": "Bug 1", "Severity": {"Name": "Critical"}},
                {"Id": 21, "Name": "Bug 2", "Severity": {"Name": "Minor"}},
            ]
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.list_bugs(
                project_id=10, severity="Critical", limit=25
            )

            result_data = json.loads(result)
            assert len(result_data["Items"]) == 2
            assert result_data["Items"][0]["Severity"]["Name"] == "Critical"

            mock_client.get_entities.assert_called_once_with(
                "Bugs",
                where="Project.Id eq 10 and Severity.Name eq 'Critical'",
                include="[Id,Name,Description,EntityState,Severity,Project[Name],AssignedUser[FirstName,LastName,Email],CreateDate,ModifyDate]",
                take=25,
            )

    @pytest.mark.asyncio
    async def test_create_user_story(self, mock_client):
        """Test creating a new user story"""
        mock_client.create_entity.return_value = {
            "Id": 999,
            "Name": "New User Story",
            "Project": {"Id": 100},
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.create_user_story(
                name="New User Story",
                project_id=100,
            )

            result_data = json.loads(result)
            assert result_data["Id"] == 999
            assert result_data["Name"] == "New User Story"

            mock_client.create_entity.assert_called_once()
            call_args = mock_client.create_entity.call_args
            assert call_args[0][0] == "UserStories"
            assert call_args[0][1]["Name"] == "New User Story"
            assert call_args[0][1]["Project"]["Id"] == 100

    @pytest.mark.asyncio
    async def test_create_task(self, mock_client):
        """Test creating a new task"""
        mock_client.create_entity.return_value = {
            "Id": 456,
            "Name": "New Task",
            "UserStory": {"Id": 123},
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.create_task(
                name="New Task",
                story_id=123,
                description="Task description",
                effort=3.5,
            )

            result_data = json.loads(result)
            assert result_data["Id"] == 456
            assert result_data["Name"] == "New Task"

            mock_client.create_entity.assert_called_once()
            call_args = mock_client.create_entity.call_args
            assert call_args[0][0] == "Task"
            assert call_args[0][1]["Name"] == "New Task"
            assert call_args[0][1]["UserStory"]["Id"] == 123
            assert call_args[0][1]["Description"] == "Task description"
            assert call_args[0][1]["Effort"] == 3.5

    @pytest.mark.asyncio
    async def test_update_entity_state(self, mock_client):
        """Test updating entity state"""
        mock_client.get_entities.return_value = {"Items": [{"Id": 5, "Name": "Done"}]}
        mock_client.update_entity.return_value = {
            "Id": 789,
            "EntityState": {"Id": 5, "Name": "Done"},
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.update_entity_state(
                entity_type="Task", entity_id=789, state_name="Done"
            )

            result_data = json.loads(result)
            assert result_data["Id"] == 789
            assert result_data["EntityState"]["Name"] == "Done"

            mock_client.get_entities.assert_called_once_with(
                "EntityStates", where="Name eq 'Done'", take=1
            )
            mock_client.update_entity.assert_called_once_with(
                "Task", 789, {"EntityState": {"Id": 5}}
            )

    @pytest.mark.asyncio
    async def test_update_entity_state_not_found(self, mock_client):
        """Test updating entity state when state doesn't exist"""
        mock_client.get_entities.return_value = {"Items": []}

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.update_entity_state(
                entity_type="Task", entity_id=789, state_name="InvalidState"
            )

            result_data = json.loads(result)
            assert "error" in result_data
            assert "not found" in result_data["error"]

    @pytest.mark.asyncio
    async def test_add_comment(self, mock_client):
        """Test adding a comment to an entity"""
        mock_client.add_comment.return_value = {
            "Id": 999,
            "Description": "Test comment",
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.add_comment(
                entity_type="Task", entity_id=123, comment="Test comment"
            )

            result_data = json.loads(result)
            assert result_data["Id"] == 999
            assert result_data["Description"] == "Test comment"

            mock_client.add_comment.assert_called_once_with("Task", 123, "Test comment")

    @pytest.mark.asyncio
    async def test_update_time_spent(self, mock_client):
        """Test updating time spent on an entity"""
        mock_client.get_entity_by_id.return_value = {"TimeSpent": 5}
        mock_client.update_entity.return_value = {"Id": 456, "TimeSpent": 8}

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.update_time_spent(
                entity_type="Task", entity_id=456, hours=3
            )

            result_data = json.loads(result)
            assert result_data["TimeSpent"] == 8

            mock_client.get_entity_by_id.assert_called_once_with(
                "Task", 456, include="[TimeSpent]"
            )
            mock_client.update_entity.assert_called_once_with(
                "Task", 456, {"TimeSpent": 8}
            )

    @pytest.mark.asyncio
    async def test_list_projects(self, mock_client):
        """Test listing projects"""
        mock_client.get_entities.return_value = {
            "Items": [
                {"Id": 1, "Name": "Project A", "IsActive": True},
                {"Id": 2, "Name": "Project B", "IsActive": False},
            ]
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.list_projects()

            result_data = json.loads(result)
            assert len(result_data["Items"]) == 2
            assert result_data["Items"][0]["Name"] == "Project A"

            mock_client.get_entities.assert_called_once_with(
                "Projects",
                include="[Id,Name,Description,IsActive,StartDate,EndDate]",
                take=100,
            )

    @pytest.mark.asyncio
    async def test_list_iterations(self, mock_client):
        """Test listing iterations"""
        mock_client.get_entities.return_value = {
            "Items": [
                {"Id": 1, "Name": "Sprint 1", "IsCurrent": True},
                {"Id": 2, "Name": "Sprint 2", "IsCurrent": False},
            ]
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.list_iterations(
                project_id=10, is_current=True
            )

            result_data = json.loads(result)
            assert len(result_data["Items"]) == 2
            assert result_data["Items"][0]["IsCurrent"] == True

            mock_client.get_entities.assert_called_once_with(
                "Iterations",
                where="Project.Id eq 10 and IsCurrent eq 'true'",
                include="[Id,Name,StartDate,EndDate,IsCurrent,Project[Name]]",
                take=100,
            )

    @pytest.mark.asyncio
    async def test_search_entities(self, mock_client):
        """Test searching entities"""
        mock_client.get_entities.side_effect = [
            {"Items": [{"Id": 1, "Name": "Story with query"}]},
            {"Items": [{"Id": 2, "Name": "Task with query"}]},
            {"Items": [{"Id": 3, "Name": "Bug with query"}]},
        ]

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.search_entities(query="query", limit=10)

            result_data = json.loads(result)
            assert "UserStories" in result_data
            assert "Tasks" in result_data
            assert "Bugs" in result_data
            assert len(result_data["UserStories"]) == 1
            assert len(result_data["Tasks"]) == 1
            assert len(result_data["Bugs"]) == 1

            assert mock_client.get_entities.call_count == 3
    
    @pytest.mark.asyncio
    async def test_update_user_story(self, mock_client):
        """Test updating a user story"""
        mock_client.update_entity.return_value = {
            "Id": 123,
            "Name": "Updated Story",
            "Description": "New description",
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.update_user_story(
                story_id=123,
                name="Updated Story",
                description="New description",
                effort=5.0,
            )

            result_data = json.loads(result)
            assert result_data["Id"] == 123
            assert result_data["Name"] == "Updated Story"

            mock_client.update_entity.assert_called_once()
            call_args = mock_client.update_entity.call_args
            assert call_args[0][0] == "UserStories"
            assert call_args[0][1] == 123
            assert call_args[0][2]["Name"] == "Updated Story"
            assert call_args[0][2]["Description"] == "New description"
            assert call_args[0][2]["Effort"] == 5.0
    
    @pytest.mark.asyncio
    async def test_get_entity_states(self, mock_client):
        """Test getting entity states"""
        mock_client.get_entities.return_value = {
            "Items": [
                {
                    "Id": 1,
                    "Name": "New",
                    "NumericPriority": 1.0,
                    "Process": {"Id": 1, "Name": "Scrum"},
                    "EntityType": {"Name": "UserStory"}
                },
                {
                    "Id": 2,
                    "Name": "Done",
                    "NumericPriority": 10.0,
                    "Process": {"Id": 1, "Name": "Scrum"},
                    "EntityType": {"Name": "UserStory"}
                },
            ]
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.get_entity_states(
                entity_type="UserStory",
                process_id=1,
            )

            result_data = json.loads(result)
            assert len(result_data["Items"]) == 2
            # Should be sorted by priority
            assert result_data["Items"][0]["Name"] == "New"
            assert result_data["Items"][1]["Name"] == "Done"

            mock_client.get_entities.assert_called_once_with(
                "EntityStates",
                where="EntityType.Name eq 'UserStory' and Process.Id eq 1",
                include="[Id,Name,NumericPriority,Process[Id,Name],EntityType[Name]]",
                take=100,
            )
    
    @pytest.mark.asyncio
    async def test_delete_entity(self, mock_client):
        """Test marking an entity as deleted/done"""
        # Mock getting the entity
        mock_client.get_entity_by_id.return_value = {
            "Id": 123,
            "Name": "Test Story",
            "Project": {"Process": {"Id": 1}},
        }
        
        # Mock finding the Done state
        mock_client.get_entities.return_value = {
            "Items": [{"Id": 5, "Name": "Done"}]
        }
        
        # Mock updating the entity
        mock_client.update_entity.return_value = {
            "Id": 123,
            "EntityState": {"Id": 5, "Name": "Done"}
        }

        with patch.object(targetprocess_mcp, "tp_client", mock_client):
            result = await targetprocess_mcp.delete_entity(
                entity_type="UserStory",
                entity_id=123,
            )

            result_data = json.loads(result)
            assert result_data["Id"] == 123
            assert result_data["Note"] == "Entity marked as Done"

            # Should have called get_entity_by_id, get_entities (for state), and update_entity
            mock_client.get_entity_by_id.assert_called_once()
            mock_client.get_entities.assert_called_once()
            mock_client.update_entity.assert_called_once()
