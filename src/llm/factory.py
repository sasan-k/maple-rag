"""
LLM Provider Factory.

Provides a factory pattern for creating LLM and embedding instances
based on configuration. Supports Azure OpenAI, OpenAI, Anthropic, and AWS Bedrock.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.config.settings import Settings, get_settings


class LLMProviderError(Exception):
    """Raised when LLM provider configuration is invalid."""

    pass


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def create_chat_model(self, **kwargs: Any) -> BaseChatModel:
        """Create a chat model instance."""
        pass

    @abstractmethod
    def create_embeddings(self, **kwargs: Any) -> Embeddings:
        """Create an embeddings instance."""
        pass

    @abstractmethod
    def validate_config(self, settings: Settings) -> bool:
        """Validate that required configuration is present."""
        pass


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI provider implementation."""

    def validate_config(self, settings: Settings) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return bool(
            settings.azure_openai_endpoint and settings.azure_openai_api_key
        )

    def create_chat_model(self, **kwargs: Any) -> BaseChatModel:
        """Create Azure OpenAI chat model."""
        from langchain_openai import AzureChatOpenAI

        settings = get_settings()

        if not self.validate_config(settings):
            raise LLMProviderError(
                "Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY"
            )

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment_name=kwargs.get(
                "deployment_name", settings.azure_openai_deployment_name
            ),
            api_version=settings.azure_openai_api_version,
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2048),
        )

    def create_embeddings(self, **kwargs: Any) -> Embeddings:
        """Create Azure OpenAI embeddings."""
        from langchain_openai import AzureOpenAIEmbeddings

        settings = get_settings()

        if not self.validate_config(settings):
            raise LLMProviderError(
                "Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY"
            )

        return AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=kwargs.get(
                "deployment", settings.azure_openai_embedding_deployment
            ),
            api_version=settings.azure_openai_api_version,
        )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI direct provider implementation."""

    def validate_config(self, settings: Settings) -> bool:
        """Check if OpenAI is properly configured."""
        return bool(settings.openai_api_key)

    def create_chat_model(self, **kwargs: Any) -> BaseChatModel:
        """Create OpenAI chat model."""
        from langchain_openai import ChatOpenAI

        settings = get_settings()

        if not self.validate_config(settings):
            raise LLMProviderError("OpenAI not configured. Set OPENAI_API_KEY")

        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model=kwargs.get("model", settings.openai_model),
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2048),
        )

    def create_embeddings(self, **kwargs: Any) -> Embeddings:
        """Create OpenAI embeddings."""
        from langchain_openai import OpenAIEmbeddings

        settings = get_settings()

        if not self.validate_config(settings):
            raise LLMProviderError("OpenAI not configured. Set OPENAI_API_KEY")

        return OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=kwargs.get("model", settings.openai_embedding_model),
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation."""

    def validate_config(self, settings: Settings) -> bool:
        """Check if Anthropic is properly configured."""
        return bool(settings.anthropic_api_key)

    def create_chat_model(self, **kwargs: Any) -> BaseChatModel:
        """Create Anthropic chat model."""
        from langchain_anthropic import ChatAnthropic

        settings = get_settings()

        if not self.validate_config(settings):
            raise LLMProviderError(
                "Anthropic not configured. Set ANTHROPIC_API_KEY"
            )

        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=kwargs.get("model", settings.anthropic_model),
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2048),
        )

    def create_embeddings(self, **kwargs: Any) -> Embeddings:
        """
        Create embeddings - Anthropic doesn't have embeddings API.
        Falls back to OpenAI embeddings.
        """
        settings = get_settings()

        # Anthropic doesn't provide embeddings, fall back to OpenAI
        if settings.openai_api_key:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                api_key=settings.openai_api_key,
                model=settings.openai_embedding_model,
            )

        raise LLMProviderError(
            "Anthropic doesn't provide embeddings. Set OPENAI_API_KEY for embeddings."
        )


class AWSBedrockProvider(BaseLLMProvider):
    """
    AWS Bedrock provider implementation.
    
    Supports various models including:
    - Anthropic Claude (claude-3-5-sonnet, claude-3-opus, etc.)
    - Amazon Titan
    - Meta Llama
    - Mistral
    - Cohere Command
    """

    def validate_config(self, settings: Settings) -> bool:
        """
        Check if AWS Bedrock is properly configured.
        Can use explicit credentials or rely on boto3 credential chain
        (environment variables, AWS config file, IAM role, etc.)
        """
        # If explicit credentials are provided, validate them
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            return True

        # Otherwise, try to use boto3's default credential chain
        try:
            import boto3
            session = boto3.Session(region_name=settings.aws_region)
            credentials = session.get_credentials()
            return credentials is not None
        except Exception:
            return False

    def create_chat_model(self, **kwargs: Any) -> BaseChatModel:
        """Create AWS Bedrock chat model."""
        from langchain_aws import ChatBedrock

        settings = get_settings()

        # Build credentials dict if explicitly provided
        credentials_kwargs = {}
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            credentials_kwargs = {
                "aws_access_key_id": settings.aws_access_key_id,
                "aws_secret_access_key": settings.aws_secret_access_key,
            }

        model_id = kwargs.get("model_id", settings.aws_bedrock_model_id)

        return ChatBedrock(
            model_id=model_id,
            region_name=kwargs.get("region_name", settings.aws_region),
            model_kwargs={
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 2048),
            },
            **credentials_kwargs,
        )

    def create_embeddings(self, **kwargs: Any) -> Embeddings:
        """Create AWS Bedrock embeddings using Amazon Titan or other models."""
        from langchain_aws import BedrockEmbeddings

        settings = get_settings()

        # Build credentials dict if explicitly provided
        credentials_kwargs = {}
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            credentials_kwargs = {
                "aws_access_key_id": settings.aws_access_key_id,
                "aws_secret_access_key": settings.aws_secret_access_key,
            }

        model_id = kwargs.get("model_id", settings.aws_bedrock_embedding_model_id)

        return BedrockEmbeddings(
            model_id=model_id,
            region_name=kwargs.get("region_name", settings.aws_region),
            **credentials_kwargs,
        )


class LLMFactory:
    """
    Factory for creating LLM instances based on configuration.

    Usage:
        llm = LLMFactory.create_chat_model()
        llm = LLMFactory.create_chat_model(provider="openai", temperature=0.5)
    """

    _providers: dict[str, type[BaseLLMProvider]] = {
        "azure_openai": AzureOpenAIProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "aws_bedrock": AWSBedrockProvider,
    }

    @classmethod
    def register_provider(
        cls, name: str, provider_class: type[BaseLLMProvider]
    ) -> None:
        """Register a new LLM provider."""
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, provider_name: str | None = None) -> BaseLLMProvider:
        """Get a provider instance by name."""
        settings = get_settings()
        name = provider_name or settings.llm_provider

        if name not in cls._providers:
            raise LLMProviderError(
                f"Unknown provider: {name}. Available: {list(cls._providers.keys())}"
            )

        return cls._providers[name]()

    @classmethod
    def create_chat_model(
        cls, provider: str | None = None, **kwargs: Any
    ) -> BaseChatModel:
        """
        Create a chat model instance.

        Args:
            provider: Optional provider name override
            **kwargs: Additional arguments passed to the provider

        Returns:
            BaseChatModel instance
        """
        provider_instance = cls.get_provider(provider)
        return provider_instance.create_chat_model(**kwargs)


class EmbeddingFactory:
    """
    Factory for creating embedding instances.

    Usage:
        embeddings = EmbeddingFactory.create_embeddings()
    """

    @classmethod
    def create_embeddings(
        cls, provider: str | None = None, **kwargs: Any
    ) -> Embeddings:
        """
        Create an embeddings instance.

        Args:
            provider: Optional provider name override
            **kwargs: Additional arguments passed to the provider

        Returns:
            Embeddings instance
        """
        provider_instance = LLMFactory.get_provider(provider)
        return provider_instance.create_embeddings(**kwargs)
