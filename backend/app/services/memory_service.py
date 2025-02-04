import json
import redis.asyncio as aioredis
from datetime import datetime
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.core.config import settings
from app.models.schemas import ChatMessage, MessageRole


class ConversationMemoryService:

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def get_client(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    def _session_key(self, session_id: str) -> str:
        return f"chat:history:{session_id}"

    def _meta_key(self, session_id: str) -> str:
        return f"chat:meta:{session_id}"

    async def add_message(self, session_id: str, role: MessageRole, content: str, metadata: dict = None) -> ChatMessage:
        client = await self.get_client()
        key = self._session_key(session_id)

        msg = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )

        await client.rpush(key, msg.model_dump_json())
        await client.expire(key, settings.conversation_ttl_seconds)

        # keep history bounded
        length = await client.llen(key)
        if length > settings.max_conversation_history * 2:
            await client.ltrim(key, -settings.max_conversation_history * 2, -1)

        return msg

    async def get_history(self, session_id: str, limit: int = None) -> list[ChatMessage]:
        client = await self.get_client()
        key = self._session_key(session_id)

        raw = await client.lrange(key, 0, -1)
        messages = [ChatMessage(**json.loads(r)) for r in raw]

        if limit:
            messages = messages[-limit:]
        return messages

    async def get_langchain_messages(self, session_id: str) -> list[BaseMessage]:
        history = await self.get_history(session_id, limit=settings.max_conversation_history)
        lc_messages = []
        for msg in history:
            if msg.role == MessageRole.USER:
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                lc_messages.append(AIMessage(content=msg.content))
        return lc_messages

    async def clear_session(self, session_id: str):
        client = await self.get_client()
        await client.delete(self._session_key(session_id))
        await client.delete(self._meta_key(session_id))

    async def get_session_meta(self, session_id: str) -> dict:
        client = await self.get_client()
        key = self._meta_key(session_id)
        meta = await client.hgetall(key)
        if not meta:
            meta = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "mode": "chat",
                "documents_loaded": "0"
            }
            await client.hset(key, mapping=meta)
            await client.expire(key, settings.conversation_ttl_seconds)
        return meta

    async def update_session_meta(self, session_id: str, **kwargs):
        client = await self.get_client()
        key = self._meta_key(session_id)
        await client.hset(key, mapping={k: str(v) for k, v in kwargs.items()})
        await client.expire(key, settings.conversation_ttl_seconds)

    async def list_sessions(self) -> list[str]:
        client = await self.get_client()
        keys = await client.keys("chat:history:*")
        return [k.replace("chat:history:", "") for k in keys]

    async def health_check(self) -> bool:
        try:
            client = await self.get_client()
            await client.ping()
            return True
        except Exception:
            return False


memory_service = ConversationMemoryService()
