from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AgentMode(str, Enum):
    CHAT = "chat"
    RAG = "rag"
    AGENT = "agent"
    SUMMARIZE = "summarize"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=10000)
    mode: AgentMode = AgentMode.CHAT
    stream: bool = False
    options: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage
    sources: list[dict[str, Any]] = Field(default_factory=list)
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: int = 0


class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    message_count: int
    mode: AgentMode
    documents_loaded: int = 0


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_created: int
    status: str


class ConversationHistory(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    total_messages: int


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
