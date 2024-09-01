"""Controller for the AI agent."""

from backend.graph_rag.ai_agent import Agent


agent_executor = Agent()


def ask_agent(message: str) -> dict:
    """Ask the agent a question."""
    return agent_executor.invoke(message)
