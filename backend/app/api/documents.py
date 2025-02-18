import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from app.models.schemas import DocumentUploadResponse
from app.services.rag_service import rag_service
from app.services.memory_service import memory_service

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_FILE_SIZE_MB = 20


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {list(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit")

    tmp_path = f"/tmp/{uuid.uuid4()}{ext}"
    async with aiofiles.open(tmp_path, "wb") as f:
        await f.write(content)

    try:
        result = await rag_service.ingest_file(session_id, tmp_path, file.filename)

        current_docs = int((await memory_service.get_session_meta(session_id)).get("documents_loaded", 0))
        await memory_service.update_session_meta(session_id, documents_loaded=current_docs + 1)

        return DocumentUploadResponse(
            document_id=result["doc_id"],
            filename=file.filename,
            chunks_created=result["chunks_created"],
            status="indexed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.delete("/{session_id}")
async def clear_documents(session_id: str):
    rag_service.clear_session(session_id)
    await memory_service.update_session_meta(session_id, documents_loaded=0)
    return {"message": "Documents cleared"}


@router.get("/{session_id}/status")
async def documents_status(session_id: str):
    has_docs = rag_service.has_documents(session_id)
    meta = await memory_service.get_session_meta(session_id)
    return {
        "session_id": session_id,
        "has_documents": has_docs,
        "documents_loaded": int(meta.get("documents_loaded", 0))
    }
