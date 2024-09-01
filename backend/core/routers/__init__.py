"""Routers for the FastAPI application."""

from fastapi import APIRouter

from backend.core.controllers.ai_agent import ask_agent

router = APIRouter()


@router.get("/agent/")
async def get_agent(message: str):
    """Ask the agent a question."""
    return {"response": ask_agent(message)}
