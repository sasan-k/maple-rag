"""
Tests for LLM factory.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.config.settings import Settings
from src.llm.factory import (
    LLMFactory,
    EmbeddingFactory,
    LLMProviderError,
    AzureOpenAIProvider,
    OpenAIProvider,
    AnthropicProvider,
)


class TestLLMFactory:
    """Test LLM Factory."""

    def test_get_provider_azure(self):
        """Test getting Azure OpenAI provider."""
        provider = LLMFactory.get_provider("azure_openai")
        assert isinstance(provider, AzureOpenAIProvider)

    def test_get_provider_openai(self):
        """Test getting OpenAI provider."""
        provider = LLMFactory.get_provider("openai")
        assert isinstance(provider, OpenAIProvider)

    def test_get_provider_anthropic(self):
        """Test getting Anthropic provider."""
        provider = LLMFactory.get_provider("anthropic")
        assert isinstance(provider, AnthropicProvider)

    def test_get_provider_unknown(self):
        """Test error for unknown provider."""
        with pytest.raises(LLMProviderError) as exc:
            LLMFactory.get_provider("unknown_provider")
        assert "Unknown provider" in str(exc.value)

    def test_register_custom_provider(self):
        """Test registering a custom provider."""

        class CustomProvider(AzureOpenAIProvider):
            pass

        LLMFactory.register_provider("custom", CustomProvider)
        provider = LLMFactory.get_provider("custom")
        assert isinstance(provider, CustomProvider)


class TestAzureOpenAIProvider:
    """Test Azure OpenAI Provider."""

    def test_validate_config_missing(self):
        """Test validation fails when config is missing."""
        provider = AzureOpenAIProvider()
        settings = Settings(
            azure_openai_endpoint=None,
            azure_openai_api_key=None,
        )
        assert provider.validate_config(settings) is False

    def test_validate_config_present(self):
        """Test validation passes when config is present."""
        provider = AzureOpenAIProvider()
        settings = Settings(
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_api_key="test-key",
        )
        assert provider.validate_config(settings) is True

    def test_create_chat_model_no_config(self):
        """Test error when creating model without config."""
        provider = AzureOpenAIProvider()

        with patch(
            "src.llm.factory.get_settings",
            return_value=Settings(
                azure_openai_endpoint=None,
                azure_openai_api_key=None,
            ),
        ):
            with pytest.raises(LLMProviderError):
                provider.create_chat_model()

    @patch("src.llm.factory.get_settings")
    @patch("langchain_openai.AzureChatOpenAI")
    def test_create_chat_model_success(
        self, mock_chat_class: MagicMock, mock_settings: MagicMock
    ):
        """Test successful model creation."""
        mock_settings.return_value = Settings(
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_api_key="test-key",
            azure_openai_deployment_name="gpt-4o",
        )

        provider = AzureOpenAIProvider()
        provider.create_chat_model()

        mock_chat_class.assert_called_once()


class TestOpenAIProvider:
    """Test OpenAI Provider."""

    def test_validate_config_missing(self):
        """Test validation fails when config is missing."""
        provider = OpenAIProvider()
        settings = Settings(openai_api_key=None)
        assert provider.validate_config(settings) is False

    def test_validate_config_present(self):
        """Test validation passes when config is present."""
        provider = OpenAIProvider()
        settings = Settings(openai_api_key="sk-test")
        assert provider.validate_config(settings) is True

    @patch("src.llm.factory.get_settings")
    @patch("langchain_openai.ChatOpenAI")
    def test_create_chat_model_success(
        self, mock_chat_class: MagicMock, mock_settings: MagicMock
    ):
        """Test successful model creation."""
        mock_settings.return_value = Settings(openai_api_key="sk-test")

        provider = OpenAIProvider()
        provider.create_chat_model()

        mock_chat_class.assert_called_once()


class TestAnthropicProvider:
    """Test Anthropic Provider."""

    def test_validate_config_missing(self):
        """Test validation fails when config is missing."""
        provider = AnthropicProvider()
        settings = Settings(anthropic_api_key=None)
        assert provider.validate_config(settings) is False

    def test_validate_config_present(self):
        """Test validation passes when config is present."""
        provider = AnthropicProvider()
        settings = Settings(anthropic_api_key="test-key")
        assert provider.validate_config(settings) is True

    def test_create_embeddings_requires_openai(self):
        """Test that embeddings fall back to OpenAI."""
        provider = AnthropicProvider()

        with patch(
            "src.llm.factory.get_settings",
            return_value=Settings(
                anthropic_api_key="test",
                openai_api_key=None,
            ),
        ):
            with pytest.raises(LLMProviderError) as exc:
                provider.create_embeddings()
            assert "doesn't provide embeddings" in str(exc.value)
