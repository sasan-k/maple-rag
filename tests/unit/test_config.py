"""
Tests for configuration settings.
"""

import os
from unittest.mock import patch

from src.config.settings import Settings, get_settings


class TestSettings:
    """Test Settings class."""

    def test_default_values(self):
        """Test default setting values."""
        settings = Settings()

        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.llm_provider == "azure_openai"
        assert settings.chunk_size == 1000
        assert settings.chunk_overlap == 200

    def test_environment_detection(self):
        """Test environment detection properties."""
        settings = Settings(environment="development")
        assert settings.is_development is True
        assert settings.is_production is False

        settings = Settings(environment="production")
        assert settings.is_development is False
        assert settings.is_production is True

    def test_database_url_validation(self):
        """Test database URL asyncpg validation."""
        # Should add asyncpg if missing
        settings = Settings(database_url="postgresql://user:pass@localhost/db")
        assert "asyncpg" in settings.database_url

        # Should keep asyncpg if present
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db"
        )
        assert "asyncpg" in settings.database_url
        assert settings.database_url.count("asyncpg") == 1

    def test_from_environment(self):
        """Test loading settings from environment."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "staging",
                "DEBUG": "true",
                "API_PORT": "9000",
                "LLM_PROVIDER": "openai",
            },
        ):
            # Clear cache
            get_settings.cache_clear()
            settings = Settings()

            assert settings.environment == "staging"
            assert settings.debug is True
            assert settings.api_port == 9000
            assert settings.llm_provider == "openai"

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
