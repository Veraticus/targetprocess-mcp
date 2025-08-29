"""Tests for TargetProcessClient"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.targetprocess_mcp import TargetProcessClient, TargetProcessConfig


@pytest.fixture
def client():
    """Create a TargetProcessClient instance for testing"""
    config = TargetProcessConfig(
        base_url="https://test.tpondemand.com", token="test_token"
    )
    return TargetProcessClient(config)


@pytest.fixture
def client_with_creds():
    """Create a TargetProcessClient with username/password"""
    config = TargetProcessConfig(
        base_url="https://test.tpondemand.com", username="testuser", password="testpass"
    )
    return TargetProcessClient(config)


class TestTargetProcessClient:
    def test_init_with_token(self, client):
        """Test client initialization with API token"""
        assert client.base_url == "https://test.tpondemand.com"
        assert client.api_v1_url == "https://test.tpondemand.com/api/v1"
        assert client.api_v2_url == "https://test.tpondemand.com/api/v2"
        assert "Authorization" in client.headers
        assert client.headers["Accept"] == "application/json"

    def test_init_with_credentials(self, client_with_creds):
        """Test client initialization with username/password"""
        assert client_with_creds.base_url == "https://test.tpondemand.com"
        assert "Authorization" in client_with_creds.headers

    @pytest.mark.asyncio
    async def test_get_entities(self, client):
        """Test getting entities from Target Process"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Items": [{"Id": 1, "Name": "Test"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await client.get_entities("UserStories", where="Id eq 1", take=10)

            assert result == {"Items": [{"Id": 1, "Name": "Test"}]}
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "UserStories" in call_args[0][0]
            assert call_args[1]["params"]["take"] == "10"
            assert call_args[1]["params"]["where"] == "Id eq 1"

    @pytest.mark.asyncio
    async def test_get_entity_by_id(self, client):
        """Test getting a specific entity by ID"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Id": 123, "Name": "Test Story"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await client.get_entity_by_id("UserStory", 123)

            assert result == {"Id": 123, "Name": "Test Story"}
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "UserStory/123" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_entity(self, client):
        """Test creating a new entity"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Id": 456, "Name": "New Task"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            data = {"Name": "New Task", "UserStory": {"Id": 123}}
            result = await client.create_entity("Task", data)

            assert result == {"Id": 456, "Name": "New Task"}
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "Task" in call_args[0][0]
            assert call_args[1]["json"] == data

    @pytest.mark.asyncio
    async def test_update_entity(self, client):
        """Test updating an existing entity"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Id": 789, "EntityState": {"Name": "Done"}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            data = {"EntityState": {"Id": 2}}
            result = await client.update_entity("Task", 789, data)

            assert result == {"Id": 789, "EntityState": {"Name": "Done"}}
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "Task/789" in call_args[0][0]
            assert call_args[1]["json"] == data

    @pytest.mark.asyncio
    async def test_add_comment(self, client):
        """Test adding a comment to an entity"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Id": 999, "Description": "Test comment"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = await client.add_comment("Task", 123, "Test comment")

            assert result == {"Id": 999, "Description": "Test comment"}
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "Comment" in call_args[0][0]
            assert call_args[1]["json"]["Description"] == "Test comment"
            assert call_args[1]["json"]["General"]["Id"] == 123
