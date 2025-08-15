import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.health import router as health_router
from .routes.mcp import router as mcp_router
from .routes.realtime import router as realtime_router
from .mcp_bootstrap import initialize_mcp, cleanup_mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load .env if present
    load_dotenv()
    # Initialize MCP/Gmail agent once on startup
    await initialize_mcp()
    try:
        yield
    finally:
        await cleanup_mcp()


app = FastAPI(title="Email Voice Agent MCP Backend", lifespan=lifespan)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(health_router)
app.include_router(mcp_router)
app.include_router(realtime_router)


# Optional: local dev entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("UVICORN_RELOAD", "0") == "1"),
    )


