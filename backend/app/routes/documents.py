from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.dependencies import database, document_service, require_user, to_document_response
from app.models import DocumentResponse, UserPublic


router = APIRouter()


def process_document_upload(document_id: str, filename: str, content_type: str | None, payload: bytes) -> None:
    try:
        extracted_text = document_service.extract_text(filename or "document", content_type, payload)
        if extracted_text.strip():
            database.update_uploaded_document_text(document_id, extracted_text[:200000], status="ready")
        else:
            database.mark_uploaded_document_failed(document_id)
    except ValueError:
        database.mark_uploaded_document_failed(document_id)


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
    row = database.create_uploaded_document_placeholder(
        user_id=current_user.id,
        name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size=len(payload),
    )
    background_tasks.add_task(process_document_upload, row["id"], file.filename or "document", file.content_type, payload)
    return to_document_response(row)
