"""
Guardrail node to specific check topics.
"""

from langchain_core.messages import HumanMessage

from src.agent.prompts import GUARDRAIL_PROMPT
from src.agent.state import AgentState
from src.config.logging import get_logger
from src.llm.factory import LLMFactory

logger = get_logger("agent.guardrail")


async def guardrail(state: AgentState) -> AgentState:
    """
    Check if the user's query is on-topic.
    """
    logger.info("Checking guardrails")
    query = state.query

    # Simple check for very short queries
    if len(query.strip()) < 2:
        return state

    # Use LLM to classify
    llm = LLMFactory.create_chat_model(temperature=0)

    messages = [HumanMessage(content=GUARDRAIL_PROMPT.format(message=query))]

    try:
        response = await llm.ainvoke(messages)
        result = response.content.strip().lower()

        logger.info(f"Guardrail check result: {result}")

        if "no" in result:
            state.metadata["is_off_topic"] = True
            # We can set a refusal message here, but the decision will be made in the graph edge
        else:
            state.metadata["is_off_topic"] = False

    except Exception as e:
        logger.error(f"Guardrail check failed: {e}")
        # Fail open
        state.metadata["is_off_topic"] = False

    return state
