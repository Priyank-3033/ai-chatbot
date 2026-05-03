from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.dependencies import database, document_service, embedding_service, require_user, to_document_response, vector_store
from app.models import DocumentResponse, UserPublic


router = APIRouter()


def process_document_upload(document_id: str, user_id: int, filename: str, content_type: str | None, payload: bytes) -> None:
    try:
        extracted_text = document_service.extract_text(filename or "document", content_type, payload)
        if extracted_text.strip():
            chunks = document_service.chunk_text(extracted_text, chunk_size=300, overlap=60)
            if chunks:
                embeddings = embedding_service.embed_many(chunks)
                vector_store.delete_document(document_id)
                vector_store.add_document_chunks(
                    document_id=document_id,
                    user_id=user_id,
                    document_name=filename or "document",
                    source_type="pdf" if (filename or "").lower().endswith(".pdf") or (content_type or "").lower() == "application/pdf" else "document",
                    content_type=content_type or "application/octet-stream",
                    chunks=chunks,
                    embeddings=embeddings,
                )
            database.update_uploaded_document_text(document_id, extracted_text[:200000], status="ready")
            database.record_audit_log(
                event_type="document.upload_processed",
                severity="low",
                user_id=user_id,
                description=f"Document {filename or 'document'} processed successfully",
                metadata={"document_id": document_id, "content_type": content_type or "unknown"},
            )
        else:
            database.mark_uploaded_document_failed(document_id)
            database.create_security_alert(
                alert_type="empty_document_extract",
                severity="medium",
                user_id=user_id,
                message=f"Uploaded document {filename or 'document'} could not be parsed into readable text",
                metadata={"document_id": document_id},
            )
    except ValueError:
        database.mark_uploaded_document_failed(document_id)
        database.create_security_alert(
            alert_type="invalid_document_upload",
            severity="high",
            user_id=user_id,
            message=f"Document upload rejected or failed parsing for {filename or 'document'}",
            metadata={"document_id": document_id, "content_type": content_type or "unknown"},
        )


@router.get("/api/documents", response_model=list[DocumentResponse])
def list_documents(current_user: UserPublic = Depends(require_user)) -> list[DocumentResponse]:
    return [to_document_response(row) for row in database.list_uploaded_documents(current_user.id)]


@router.post("/api/documents", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(require_user),
) -> DocumentResponse:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(payload) > (embedding_service.settings.upload_max_mb * 1024 * 1024):
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded file is too large.")
    allowed_types = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "application/json",
    }
    if file.content_type not in allowed_types:
        database.create_security_alert(
            alert_type="blocked_file_upload",
            severity="high",
            user_id=current_user.id,
            message=f"Blocked unsupported upload type: {file.content_type or 'unknown'}",
            metadata={"filename": file.filename or "document"},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")
    row = database.create_uploaded_document_placeholder(
        user_id=current_user.id,
        name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size=len(payload),
    )
    database.record_audit_log(
        event_type="document.upload_started",
        severity="low",
        user_id=current_user.id,
        description=f"Document upload started for {file.filename or 'document'}",
        metadata={"document_id": row["id"], "content_type": file.content_type or "unknown", "size": str(len(payload))},
    )
    background_tasks.add_task(process_document_upload, row["id"], current_user.id, file.filename or "document", file.content_type, payload)
    return to_document_response(row)
