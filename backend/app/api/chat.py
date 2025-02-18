import uuid
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, ConversationHistory, SessionInfo, AgentMode
from app.services.chat_service import chat_service
from app.services.memory_service import memory_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        return await chat_service.process(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/new")
async def new_session():
    session_id = str(uuid.uuid4())
    meta = await memory_service.get_session_meta(session_id)
    return {"session_id": session_id, "meta": meta}


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    meta = await memory_service.get_session_meta(session_id)
    history = await memory_service.get_history(session_id)
    return SessionInfo(
        session_id=session_id,
        created_at=meta.get("created_at"),
        message_count=len(history),
        mode=AgentMode(meta.get("mode", "chat")),
        documents_loaded=int(meta.get("documents_loaded", 0))
    )


@router.get("/session/{session_id}/history", response_model=ConversationHistory)
async def get_history(session_id: str, limit: int = 50):
    messages = await memory_service.get_history(session_id, limit=limit)
    return ConversationHistory(
        session_id=session_id,
        messages=messages,
        total_messages=len(messages)
    )


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    await memory_service.clear_session(session_id)
    return {"message": f"Session {session_id} cleared"}


@router.get("/sessions")
async def list_sessions():
    sessions = await memory_service.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}
