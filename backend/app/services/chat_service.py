import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.core.config import settings
from app.models.schemas import ChatRequest, ChatResponse, ChatMessage, MessageRole, AgentMode
from app.services.memory_service import memory_service
from app.services.rag_service import rag_service
from app.services.agent_service import agent


SYSTEM_PROMPTS = {
    AgentMode.CHAT: (
        "You are a helpful, knowledgeable AI assistant. "
        "Answer clearly and concisely. If unsure, say so."
    ),
    AgentMode.RAG: (
        "Answer using ONLY the provided context. "
        "Cite source and page when available. "
        "If the answer isn't in the context, say so — do not guess."
    ),
    AgentMode.SUMMARIZE: (
        "Create clear, structured summaries capturing key points and main arguments. "
        "Use bullet points where it helps readability."
    ),
}


class ChatService:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            openai_api_key=settings.openai_api_key
        )

    async def process(self, request: ChatRequest) -> ChatResponse:
        start = time.time()

        await memory_service.add_message(request.session_id, MessageRole.USER, request.message)

        if request.mode == AgentMode.CHAT:
            response_text, sources, steps = await self._handle_chat(request)
        elif request.mode == AgentMode.RAG:
            response_text, sources, steps = await self._handle_rag(request)
        elif request.mode == AgentMode.AGENT:
            response_text, sources, steps = await self._handle_agent(request)
        elif request.mode == AgentMode.SUMMARIZE:
            response_text, sources, steps = await self._handle_summarize(request)
        else:
            response_text, sources, steps = "Unknown mode.", [], []

        ai_msg = await memory_service.add_message(
            request.session_id, MessageRole.ASSISTANT, response_text
        )

        return ChatResponse(
            session_id=request.session_id,
            message=ai_msg,
            sources=sources,
            agent_steps=steps,
            latency_ms=int((time.time() - start) * 1000)
        )

    async def _handle_chat(self, request: ChatRequest) -> tuple[str, list, list]:
        history = await memory_service.get_langchain_messages(request.session_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPTS[AgentMode.CHAT]),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        response = await (prompt | self.llm).ainvoke({
            "history": history,
            "input": request.message
        })
        return response.content, [], []

    async def _handle_rag(self, request: ChatRequest) -> tuple[str, list, list]:
        docs = await rag_service.similarity_search(request.session_id, request.message)

        if not docs:
            return (
                "No documents uploaded for this session. "
                "Upload a file first using the paperclip icon.",
                [], []
            )

        context = "\n\n---\n\n".join([
            f"[Source: {doc.metadata.get('filename', 'Document')}, "
            f"Page: {doc.metadata.get('page', 'N/A')}]\n{doc.page_content}"
            for doc in docs
        ])

        history = await memory_service.get_langchain_messages(request.session_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPTS[AgentMode.RAG] + "\n\nContext:\n{context}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}")
        ])

        response = await (prompt | self.llm).ainvoke({
            "context": context,
            "history": history,
            "question": request.message
        })

        sources = [
            {
                "filename": doc.metadata.get("filename", "Document"),
                "page": doc.metadata.get("page", "N/A"),
                "excerpt": doc.page_content[:300] + "..."
            }
            for doc in docs
        ]

        return response.content, sources, []

    async def _handle_agent(self, request: ChatRequest) -> tuple[str, list, list]:
        history = await memory_service.get_langchain_messages(request.session_id)
        messages = history + [HumanMessage(content=request.message)]

        response_text, steps = await agent.invoke(request.session_id, messages)

        if not response_text:
            response_text = "Done. Let me know if you need anything else."

        return response_text, [], steps

    async def _handle_summarize(self, request: ChatRequest) -> tuple[str, list, list]:
        if any(kw in request.message.lower() for kw in ["conversation", "chat", "history"]):
            history = await memory_service.get_history(request.session_id)
            if not history:
                return "No conversation to summarize yet.", [], []

            conv_text = "\n".join([f"{m.role.value}: {m.content}" for m in history[-20:]])
            prompt = f"Summarize this conversation:\n\n{conv_text}"
        else:
            docs = await rag_service.similarity_search(request.session_id, request.message, k=8)
            if not docs:
                return "No documents to summarize. Upload a file first.", [], []
            conv_text = "\n\n".join([doc.page_content for doc in docs])
            prompt = f"Summarize the following. Focus on: {request.message}\n\n{conv_text}"

        response = await self.llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPTS[AgentMode.SUMMARIZE]),
            HumanMessage(content=prompt)
        ])
        return response.content, [], []


chat_service = ChatService()
