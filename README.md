# GenAI Chat App

Conversational AI application with RAG, a LangGraph agent, and Redis-backed memory. Built with FastAPI, LangChain, and React.

---

## Modes

| Mode | What it does |
|------|-------------|
| Chat | Standard conversation with persistent session memory |
| RAG | Upload a PDF/doc and ask questions against it |
| Agent | ReAct agent with tools — calculator, search, weather, code |
| Summarize | Summarize uploaded docs or conversation history |

---

## Stack

- **Backend** — Python 3.12, FastAPI, LangChain 0.3, LangGraph 0.2
- **Embeddings / Vector store** — OpenAI text-embedding-3-small, FAISS
- **Memory** — Redis (async, per-session, 24h TTL)
- **Frontend** — React 18, ReactMarkdown, syntax highlighting
- **Infra** — Docker, Kubernetes

---

## Setup

Needs an OpenAI API key.

```bash
cd backend
cp .env.example .env
# set OPENAI_API_KEY in .env
```

**With Docker:**
```bash
docker compose up --build
```

**Without Docker — need Python 3.12, Node 20, Redis:**

Terminal 1:
```bash
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Terminal 2:
```bash
cd frontend && npm install && npm start
```

App at http://localhost:3000, API docs at http://localhost:8000/docs.

---

## Config

Key env vars (all have defaults except the API key):

```
OPENAI_API_KEY=        # required
OPENAI_MODEL=gpt-4o
CHUNK_SIZE=1000
TOP_K_RETRIEVAL=5
MAX_CONVERSATION_HISTORY=20
REDIS_URL=redis://localhost:6379
```

---

## Agent tools

`calculator`, `web_search`, `get_weather`, `summarize_document`, `run_code`

Search and weather have placeholder implementations — swap in a Tavily/OpenWeatherMap key in `agent_service.py`.

---

## Adding a tool

```python
from langchain_core.tools import tool

@tool
def my_tool(input: str) -> str:
    """One-line description the agent uses to decide when to call this."""
    return "result"

TOOLS = [..., my_tool]
```

---

## TODO

- Streaming responses to frontend
- Auth / multi-user support
- Swap FAISS for a hosted vector DB (Pinecone/Weaviate) for persistence across restarts
- Add unit tests for RAG pipeline

## License
MIT
