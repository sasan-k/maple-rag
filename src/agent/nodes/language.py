"""
Language detection node.

Detects the language of user input for bilingual support.
"""

import re

from src.agent.state import AgentState
from src.config.logging import get_logger

logger = get_logger("agent.language")

# Common French words and patterns
FRENCH_PATTERNS = [
    r"\b(je|tu|il|elle|nous|vous|ils|elles)\b",
    r"\b(le|la|les|un|une|des)\b",
    r"\b(est|sont|avoir|être|fait)\b",
    r"\b(pour|avec|dans|sur|sous)\b",
    r"\b(comment|pourquoi|quand|où|qui|quoi)\b",
    r"\b(impôt|impôts|crédit|déclaration|revenu)\b",
    r"\b(merci|bonjour|salut|s'il vous plaît)\b",
    r"\bqu[e']",
    r"[àâäéèêëïîôùûüç]",
]

# Common English words and patterns
ENGLISH_PATTERNS = [
    r"\b(i|you|he|she|we|they)\b",
    r"\b(the|a|an)\b",
    r"\b(is|are|was|were|have|has)\b",
    r"\b(for|with|in|on|at)\b",
    r"\b(how|why|when|where|who|what)\b",
    r"\b(tax|taxes|credit|return|income)\b",
    r"\b(thank|hello|please)\b",
]


def _score_language(text: str, patterns: list[str]) -> int:
    """Score text against language patterns."""
    score = 0
    text_lower = text.lower()
    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        score += len(matches)
    return score


def detect_language_from_text(text: str) -> str:
    """
    Detect if text is English or French.

    Args:
        text: Input text to analyze

    Returns:
        'en' for English, 'fr' for French
    """
    if not text or not text.strip():
        return "en"

    french_score = _score_language(text, FRENCH_PATTERNS)
    english_score = _score_language(text, ENGLISH_PATTERNS)

    # French needs higher score to overcome English default
    if french_score > english_score * 0.8:
        return "fr"

    return "en"


async def detect_language(state: AgentState) -> AgentState:
    """
    Agent node: Detect the language of the user query.

    Args:
        state: Current agent state

    Returns:
        Updated state with detected language
    """
    language = detect_language_from_text(state.query)
    logger.debug(f"Detected language: {language} for query: {state.query[:50]}...")

    state.language = language
    state.metadata["detected_language"] = language

    return state
