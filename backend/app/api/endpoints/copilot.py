from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import CopilotChatRequest, CopilotChatResponse
from app.agent.copilot import ask_copilot

router = APIRouter()

@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def chat_with_copilot(request: CopilotChatRequest, db: Session = Depends(get_db)):
    return await ask_copilot(db, request.message, request.history)
