from typing import Annotated, TypedDict, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
import json
import math

from app.core.config import settings
from app.services.rag_service import rag_service


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a math expression. Supports standard operators and math module functions.
    Example: calculator("sqrt(144) + 2**8")
    """
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


@tool
def web_search(query: str) -> str:
    """Search the web for current information on any topic."""
    # TODO: integrate Tavily or SerpAPI key via settings
    return (
        f"[Web Search: '{query}']\n"
        "Connect a search provider (Tavily/SerpAPI) by replacing this function body."
    )


@tool
def get_weather(location: str) -> str:
    """Get current weather for a location."""
    # TODO: integrate OpenWeatherMap API key via settings
    return (
        f"[Weather: {location}]\n"
        "72°F, Partly Cloudy. Connect an API key in settings for live data."
    )


@tool
def summarize_document(session_id: str, query: str) -> str:
    """Retrieve relevant passages from documents uploaded in this session."""
    import asyncio
    try:
        docs = asyncio.get_event_loop().run_until_complete(
            rag_service.similarity_search(session_id, query)
        )
        if not docs:
            return "No documents found for this session."

        excerpts = []
        for i, doc in enumerate(docs[:3], 1):
            src = doc.metadata.get("filename", doc.metadata.get("source", "Document"))
            excerpts.append(f"[{src}]\n{doc.page_content[:800]}")
        return "\n\n---\n\n".join(excerpts)
    except Exception as e:
        return f"Error retrieving documents: {e}"


@tool
def run_code(code: str, language: str = "python") -> str:
    """Simulate running a code snippet. Supported: python, javascript, sql."""
    # TODO: connect to sandboxed execution environment
    lines = code.strip().split("\n")
    return f"[{language}] {len(lines)} lines - looks good. Wire up a sandbox for real execution."


TOOLS = [calculator, web_search, get_weather, summarize_document, run_code]


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    iterations: int


class LangGraphAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            openai_api_key=settings.openai_api_key,
            streaming=True
        )
        self.llm_with_tools = self.llm.bind_tools(TOOLS)
        self.tool_node = ToolNode(TOOLS)
        self.graph = self._build_graph()

    def _build_graph(self):
        def call_model(state: AgentState) -> dict:
            system = SystemMessage(content=
                "You are a capable AI assistant with tools for search, math, weather, "
                "document retrieval, and code. Use them when helpful. Cite sources."
            )
            messages = [system] + list(state["messages"])
            response = self.llm_with_tools.invoke(messages)
            return {
                "messages": [response],
                "iterations": state.get("iterations", 0) + 1
            }

        def should_continue(state: AgentState) -> Literal["tools", "end"]:
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                if state.get("iterations", 0) >= settings.max_agent_iterations:
                    return "end"
                return "tools"
            return "end"

        graph = StateGraph(AgentState)
        graph.add_node("agent", call_model)
        graph.add_node("tools", self.tool_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
        graph.add_edge("tools", "agent")

        return graph.compile()

    async def invoke(self, session_id: str, messages: list[BaseMessage]) -> tuple[str, list[dict]]:
        state = AgentState(messages=messages, session_id=session_id, iterations=0)
        result = await self.graph.ainvoke(state)

        response_text = ""
        agent_steps = []

        for msg in result["messages"]:
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        agent_steps.append({
                            "type": "tool_call",
                            "tool": tc["name"],
                            "input": tc["args"]
                        })
                elif msg.content:
                    response_text = msg.content
            elif isinstance(msg, ToolMessage):
                agent_steps.append({
                    "type": "tool_result",
                    "tool": msg.name,
                    "output": str(msg.content)[:500]
                })

        return response_text, agent_steps

    async def stream(self, session_id: str, messages: list[BaseMessage]):
        state = AgentState(messages=messages, session_id=session_id, iterations=0)
        async for chunk in self.graph.astream(state, stream_mode="values"):
            last = chunk["messages"][-1]
            if isinstance(last, AIMessage) and last.content:
                yield last.content


agent = LangGraphAgent()
