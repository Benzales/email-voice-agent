import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    has_key = bool(os.getenv("GEMINI_API_KEY"))
    return {"status": "ok", "geminiKey": has_key}


