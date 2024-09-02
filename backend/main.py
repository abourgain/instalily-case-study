"""Main module of the application."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.core.routers import router

app = FastAPI(
    title="quote",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")


@app.get("/")
async def read_root():
    """
    Root route
    """
    return {"Hello": "World"}


# Inclure les routes définies dans le dossier routers de core
app.include_router(
    router,
    prefix="",
)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", reload=True, port=8000)
