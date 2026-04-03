from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import database, document_service, require_user, to_document_response
from app.models import DocumentResponse, UserPublic


router = APIRouter()


@router.get("/api/documents", response_model=list[DocumentResponse])
def list_documents(current_user: UserPublic = Depends(require_user)) -> list[DocumentResponse]:
    return [to_document_response(row) for row in database.list_uploaded_documents(current_user.id)]


@router.post("/api/documents", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(require_user),
) -> DocumentResponse:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    try:
        extracted_text = document_service.extract_text(file.filename or "document", file.content_type, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not extracted_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not extract readable text from the file.")

    row = database.save_uploaded_document(
        user_id=current_user.id,
        name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size=len(payload),
        extracted_text=extracted_text[:200000],
    )
    return to_document_response(row)
