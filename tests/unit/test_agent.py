"""
Tests for agent components.
"""

import pytest

from src.agent.nodes.language import detect_language, detect_language_from_text
from src.agent.prompts import get_no_context_response, get_system_prompt
from src.agent.state import AgentState


class TestAgentState:
    """Test AgentState class."""

    def test_initialization(self):
        """Test state initialization."""
        state = AgentState(query="How do I file taxes?")

        assert state.query == "How do I file taxes?"
        assert state.language == "en"
        assert state.conversation_history == []
        assert state.retrieved_chunks == []

    def test_add_source(self):
        """Test adding sources."""
        state = AgentState()

        state.add_source(
            title="Tax Filing Guide",
            url="https://canada.ca/taxes/filing",
            snippet="Learn how to file...",
        )

        assert len(state.sources) == 1
        assert state.sources[0]["title"] == "Tax Filing Guide"

    def test_format_context(self):
        """Test context formatting."""
        state = AgentState()
        state.retrieved_chunks = [
            {
                "title": "Tax Guide",
                "url": "https://canada.ca/taxes",
                "content": "Tax filing information.",
            },
            {
                "title": "Deadlines",
                "url": "https://canada.ca/deadlines",
                "content": "April 30 deadline.",
            },
        ]

        context = state.format_context()

        assert "Tax Guide" in context
        assert "Tax filing information" in context
        assert "Deadlines" in context
        assert "April 30" in context

    def test_format_history(self):
        """Test conversation history formatting."""
        state = AgentState()
        state.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        history = state.format_history()

        assert "User: Hello" in history
        assert "Assistant: Hi there!" in history


class TestLanguageDetection:
    """Test language detection."""

    def test_detect_english(self):
        """Test English detection."""
        assert detect_language_from_text("How do I file my taxes?") == "en"
        assert detect_language_from_text("What are the tax deadlines?") == "en"
        assert detect_language_from_text("I need help with my return") == "en"

    def test_detect_french(self):
        """Test French detection."""
        assert detect_language_from_text("Comment puis-je déclarer mes impôts?") == "fr"
        assert detect_language_from_text("Quelles sont les dates limites?") == "fr"
        assert (
            detect_language_from_text("J'ai besoin d'aide avec ma déclaration") == "fr"
        )

    def test_detect_empty(self):
        """Test empty string defaults to English."""
        assert detect_language_from_text("") == "en"
        assert detect_language_from_text("   ") == "en"

    def test_detect_mixed(self):
        """Test mixed language defaults appropriately."""
        # Short ambiguous text defaults to English
        assert detect_language_from_text("tax") == "en"

    @pytest.mark.asyncio
    async def test_detect_language_node(self):
        """Test language detection node."""
        state = AgentState(query="Comment déclarer mes impôts?")

        result = await detect_language(state)

        assert result.language == "fr"
        assert result.metadata["detected_language"] == "fr"


class TestPrompts:
    """Test prompt templates."""

    def test_get_system_prompt_english(self):
        """Test English system prompt."""
        prompt = get_system_prompt("en")

        assert "Canada.ca" in prompt
        assert "citations" in prompt.lower() or "sources" in prompt.lower()
        assert "{context}" in prompt
        assert "{conversation_history}" in prompt

    def test_get_system_prompt_french(self):
        """Test French system prompt."""
        prompt = get_system_prompt("fr")

        assert "Canada.ca" in prompt
        assert "français" in prompt.lower() or "sources" in prompt.lower()
        assert "{context}" in prompt

    def test_no_context_response_english(self):
        """Test English no-context response."""
        response = get_no_context_response("en")

        assert "canada.ca" in response.lower()
        assert "CRA" in response or "Canada Revenue Agency" in response

    def test_no_context_response_french(self):
        """Test French no-context response."""
        response = get_no_context_response("fr")

        assert "canada.ca" in response.lower()
        assert "ARC" in response or "Agence du revenu" in response
