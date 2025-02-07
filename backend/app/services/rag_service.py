import os
import uuid
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, Docx2txtLoader, UnstructuredMarkdownLoader
)
from langchain_core.documents import Document

from app.core.config import settings


LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".docx": Docx2txtLoader,
}


class RAGService:

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self._vectorstores: dict[str, FAISS] = {}
        self._store_path = Path(settings.vector_store_path)
        self._store_path.mkdir(parents=True, exist_ok=True)

    def _session_store_path(self, session_id: str) -> Path:
        return self._store_path / session_id

    async def ingest_file(self, session_id: str, file_path: str, filename: str) -> dict:
        ext = Path(filename).suffix.lower()
        loader_cls = LOADER_MAP.get(ext)

        if loader_cls is None:
            raise ValueError(f"Unsupported file type: {ext}")

        loader = loader_cls(file_path)
        raw_docs = loader.load()

        doc_id = str(uuid.uuid4())
        for doc in raw_docs:
            doc.metadata.update({
                "doc_id": doc_id,
                "filename": filename,
                "session_id": session_id
            })

        chunks = self.splitter.split_documents(raw_docs)

        store_path = self._session_store_path(session_id)
        if session_id in self._vectorstores:
            self._vectorstores[session_id].add_documents(chunks)
        else:
            self._vectorstores[session_id] = FAISS.from_documents(chunks, self.embeddings)

        self._vectorstores[session_id].save_local(str(store_path))

        return {
            "doc_id": doc_id,
            "filename": filename,
            "chunks_created": len(chunks),
            "pages": len(raw_docs)
        }

    async def ingest_text(self, session_id: str, text: str, source: str = "manual") -> dict:
        doc_id = str(uuid.uuid4())
        docs = [Document(
            page_content=text,
            metadata={"doc_id": doc_id, "source": source, "session_id": session_id}
        )]
        chunks = self.splitter.split_documents(docs)

        if session_id in self._vectorstores:
            self._vectorstores[session_id].add_documents(chunks)
        else:
            self._vectorstores[session_id] = FAISS.from_documents(chunks, self.embeddings)

        self._vectorstores[session_id].save_local(str(self._session_store_path(session_id)))
        return {"doc_id": doc_id, "chunks_created": len(chunks)}

    def get_retriever(self, session_id: str, k: int = None):
        if session_id not in self._vectorstores:
            store_path = self._session_store_path(session_id)
            if store_path.exists():
                self._vectorstores[session_id] = FAISS.load_local(
                    str(store_path), self.embeddings, allow_dangerous_deserialization=True
                )
            else:
                return None

        # MMR gives more diverse results than plain similarity search
        return self._vectorstores[session_id].as_retriever(
            search_type="mmr",
            search_kwargs={"k": k or settings.top_k_retrieval, "fetch_k": 20}
        )

    async def similarity_search(self, session_id: str, query: str, k: int = None) -> list[Document]:
        retriever = self.get_retriever(session_id, k)
        if retriever is None:
            return []
        return await retriever.ainvoke(query)

    def has_documents(self, session_id: str) -> bool:
        return session_id in self._vectorstores or self._session_store_path(session_id).exists()

    def clear_session(self, session_id: str):
        self._vectorstores.pop(session_id, None)
        store_path = self._session_store_path(session_id)
        if store_path.exists():
            import shutil
            shutil.rmtree(store_path)


rag_service = RAGService()
