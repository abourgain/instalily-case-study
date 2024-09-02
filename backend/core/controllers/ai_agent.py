"""Controller for the AI agent."""

from langchain.memory import ConversationBufferMemory

from backend.graph_rag.ai_agent import MemoryParallelAgent


# Initialize the agent and memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
agent_executor = MemoryParallelAgent(memory=memory)  # Pass the memory to the agent


def ask_agent(message: str) -> dict:
    """Ask the agent a question."""
    return agent_executor.invoke(message)
