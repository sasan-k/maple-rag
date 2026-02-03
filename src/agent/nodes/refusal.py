"""
Refusal node for off-topic queries.
"""

from src.agent.prompts import GUARDRAIL_REFUSAL_EN, GUARDRAIL_REFUSAL_FR
from src.agent.state import AgentState
from src.config.logging import get_logger

logger = get_logger("agent.refusal")


async def generate_refusal(state: AgentState) -> AgentState:
    """
    Generate a refusal message for off-topic queries.
    """
    logger.info("Generating refusal message")

    # Check language
    if state.language == "fr":
        state.response = GUARDRAIL_REFUSAL_FR
    else:
        state.response = GUARDRAIL_REFUSAL_EN

    # Remove sources since we aren't answering
    state.sources = []

    return state
