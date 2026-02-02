"""
Generator node.

Generates responses using the LLM based on retrieved context.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.prompts import get_no_context_response, get_system_prompt
from src.agent.state import AgentState
from src.config.logging import get_logger
from src.llm.factory import LLMFactory

logger = get_logger("agent.generator")


async def generate(state: AgentState) -> AgentState:
    """
    Agent node: Generate a response using the LLM.

    Args:
        state: Current agent state with query and context

    Returns:
        Updated state with generated response
    """
    query = state.query
    context = state.context
    language = state.language

    logger.info(f"Generating response in {language} for: {query[:50]}...")

    # If no context retrieved, provide helpful fallback
    if not context or not state.retrieved_chunks:
        logger.warning("No context available, using fallback response")
        state.response = get_no_context_response(language)
        state.sources = []
        return state

    try:
        # Build the system prompt with context
        system_prompt = get_system_prompt(language).format(
            conversation_history=state.format_history(),
            context=context,
        )

        # Create LLM and generate response
        llm = LLMFactory.create_chat_model()

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ]

        response = await llm.ainvoke(messages)
        state.response = response.content

        logger.info(f"Generated response ({len(state.response)} chars)")
        state.metadata["response_length"] = len(state.response)

    except Exception as e:
        logger.error(f"Generation error: {e}")
        state.error = f"Failed to generate response: {e}"

        # Provide error fallback
        if language == "fr":
            state.response = (
                "Je suis désolé, j'ai rencontré une erreur en traitant votre demande. "
                "Veuillez réessayer ou visiter canada.ca directement."
            )
        else:
            state.response = (
                "I'm sorry, I encountered an error processing your request. "
                "Please try again or visit canada.ca directly."
            )

    return state
