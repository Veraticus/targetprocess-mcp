"""Tests for configuration loading"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.targetprocess_mcp import (
    init_client,
    load_config_from_file,
    TargetProcessClient,
)


class TestConfigLoading:
    @patch.dict(os.environ, {}, clear=True)
    @patch("src.targetprocess_mcp.load_config_from_file")
    def test_init_client_from_config_file(self, mock_load_config):
        """Test client initialization from config file when env vars are missing"""
        mock_load_config.return_value = {
            "TARGETPROCESS_URL": "https://test.tpondemand.com",
            "TARGETPROCESS_TOKEN": "test_token_from_file",
        }

        with patch("src.targetprocess_mcp.tp_client", None):
            init_client()

            # Verify load_config_from_file was called
            mock_load_config.assert_called_once()

            # Verify client was initialized
            from src import targetprocess_mcp

            assert targetprocess_mcp.tp_client is not None
            assert targetprocess_mcp.tp_client.base_url == "https://test.tpondemand.com"

    @patch.dict(
        os.environ,
        {
            "TARGETPROCESS_URL": "https://env.tpondemand.com",
            "TARGETPROCESS_TOKEN": "env_token",
        },
    )
    @patch("src.targetprocess_mcp.load_config_from_file")
    def test_env_vars_take_precedence(self, mock_load_config):
        """Test that environment variables take precedence over config file"""
        mock_load_config.return_value = {
            "TARGETPROCESS_URL": "https://file.tpondemand.com",
            "TARGETPROCESS_TOKEN": "file_token",
        }

        with patch("src.targetprocess_mcp.tp_client", None):
            init_client()

            # load_config_from_file should not be called if env vars are complete
            mock_load_config.assert_not_called()

            # Verify client uses env var values
            from src import targetprocess_mcp

            assert targetprocess_mcp.tp_client.base_url == "https://env.tpondemand.com"

    @patch.dict(
        os.environ, {"TARGETPROCESS_URL": "https://env.tpondemand.com"}, clear=True
    )
    @patch("src.targetprocess_mcp.load_config_from_file")
    def test_partial_env_vars_with_config_fallback(self, mock_load_config):
        """Test mixing env vars with config file values"""
        mock_load_config.return_value = {"TARGETPROCESS_TOKEN": "file_token"}

        with patch("src.targetprocess_mcp.tp_client", None):
            init_client()

            # Verify load_config_from_file was called for missing values
            mock_load_config.assert_called_once()

            # Verify client uses mixed values
            from src import targetprocess_mcp

            assert targetprocess_mcp.tp_client.base_url == "https://env.tpondemand.com"

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.targetprocess_mcp.load_config_from_file")
    def test_missing_url_raises_error(self, mock_load_config):
        """Test that missing URL raises appropriate error"""
        mock_load_config.return_value = {"TARGETPROCESS_TOKEN": "test_token"}

        with patch("src.targetprocess_mcp.tp_client", None):
            with pytest.raises(ValueError) as exc_info:
                init_client()

            assert "TARGETPROCESS_URL not found" in str(exc_info.value)

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.targetprocess_mcp.load_config_from_file")
    def test_missing_auth_raises_error(self, mock_load_config):
        """Test that missing authentication raises appropriate error"""
        mock_load_config.return_value = {
            "TARGETPROCESS_URL": "https://test.tpondemand.com"
        }

        with patch("src.targetprocess_mcp.tp_client", None):
            with pytest.raises(ValueError) as exc_info:
                init_client()

            assert (
                "TARGETPROCESS_TOKEN or TARGETPROCESS_USERNAME/PASSWORD is required"
                in str(exc_info.value)
            )

    @patch("pathlib.Path.home")
    def test_load_config_from_file_exists(self, mock_home):
        """Test loading configuration from existing file"""
        config_data = {
            "TARGETPROCESS_URL": "https://file.tpondemand.com",
            "TARGETPROCESS_TOKEN": "file_token",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            config_dir = Path(tmpdir) / ".config" / "targetprocess"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.json"

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            result = load_config_from_file()
            assert result == config_data

    @patch("pathlib.Path.home")
    def test_load_config_from_file_not_exists(self, mock_home):
        """Test loading configuration when file doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)

            result = load_config_from_file()
            assert result == {}

    @patch("pathlib.Path.home")
    def test_load_config_from_file_invalid_json(self, mock_home):
        """Test loading configuration with invalid JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            config_dir = Path(tmpdir) / ".config" / "targetprocess"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.json"

            with open(config_file, "w") as f:
                f.write("invalid json content")

            result = load_config_from_file()
            assert result == {}

    @patch.dict(
        os.environ,
        {
            "TARGETPROCESS_URL": "https://env.tpondemand.com",
            "TARGETPROCESS_USERNAME": "user",
            "TARGETPROCESS_PASSWORD": "pass",
        },
    )
    def test_init_client_with_username_password(self):
        """Test client initialization with username/password from env vars"""
        with patch("src.targetprocess_mcp.tp_client", None):
            init_client()

            from src import targetprocess_mcp

            assert targetprocess_mcp.tp_client is not None
            assert targetprocess_mcp.tp_client.base_url == "https://env.tpondemand.com"
            assert "Authorization" in targetprocess_mcp.tp_client.headers
