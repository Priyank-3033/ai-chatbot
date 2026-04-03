import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dependencies import chatbot, database, require_user, to_session_summary
from app.models import ChatRequest, ChatResponse, ChatSessionCreateRequest, ChatSessionDetail, ChatSessionSummary, UserPublic


router = APIRouter()


def build_effective_history(existing_messages: list[dict[str, str]], request_history: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(existing_messages) > 1:
        return existing_messages

    normalized_request_history = [
        {
            "role": str(item.get("role", "user")),
            "content": str(item.get("content", "")).strip(),
        }
        for item in request_history
        if str(item.get("content", "")).strip()
    ]
    return (existing_messages + normalized_request_history)[-12:]


def generate_chat_response(request: ChatRequest, current_user: UserPublic) -> ChatResponse:
    session_id = request.session_id
    if session_id:
        session_row = database.get_chat_session(session_id, current_user.id)
        if not session_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    else:
        session_row = database.create_chat_session(
            user_id=current_user.id,
            mode=request.mode,
            title=chatbot.default_session_title(request.mode),
            welcome_message=chatbot.welcome_message(request.mode),
        )
        session_id = session_row["id"]

    existing_messages = database.get_chat_messages(session_id)
    history = build_effective_history(
        [{"role": item["role"], "content": item["content"]} for item in existing_messages],
        request.history,
    )
    uploaded_documents = [
        {
            "name": row["name"],
            "text": row["extracted_text"],
        }
        for row in database.get_uploaded_documents_for_retrieval(current_user.id)
    ]
    database.append_chat_message(session_id, "user", request.question)

    if session_row["title"] == chatbot.default_session_title(request.mode):
        database.rename_chat_session(session_id, chatbot.suggested_session_title(request.question, request.mode))

    response = chatbot.answer(
        request.question,
        history,
        request.mode,
        model=request.model,
        custom_prompt=request.custom_prompt,
        user_id=current_user.id,
        uploaded_documents=uploaded_documents,
    )
    database.append_chat_message(session_id, "assistant", response.answer)
    response.session_id = session_id
    return response


@router.get("/api/chat-sessions", response_model=list[ChatSessionSummary])
def list_chat_sessions(current_user: UserPublic = Depends(require_user)) -> list[ChatSessionSummary]:
    rows = database.list_chat_sessions(current_user.id)
    return [to_session_summary(row) for row in rows]


@router.post("/api/chat-sessions", response_model=ChatSessionDetail)
def create_chat_session(request: ChatSessionCreateRequest, current_user: UserPublic = Depends(require_user)) -> ChatSessionDetail:
    title = request.title.strip() if request.title else chatbot.default_session_title(request.mode)
    row = database.create_chat_session(
        user_id=current_user.id,
        mode=request.mode,
        title=title,
        welcome_message=chatbot.welcome_message(request.mode),
    )
    messages = database.get_chat_messages(row["id"])
    return ChatSessionDetail(
        id=row["id"],
        title=row["title"],
        mode=row["mode"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        messages=[{"role": item["role"], "content": item["content"], "created_at": item["created_at"]} for item in messages],
    )


@router.get("/api/chat-sessions/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(session_id: str, current_user: UserPublic = Depends(require_user)) -> ChatSessionDetail:
    row = database.get_chat_session(session_id, current_user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    messages = database.get_chat_messages(session_id)
    return ChatSessionDetail(
        id=row["id"],
        title=row["title"],
        mode=row["mode"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        messages=[{"role": item["role"], "content": item["content"], "created_at": item["created_at"]} for item in messages],
    )


@router.delete("/api/chat-sessions/{session_id}")
def delete_chat_session(session_id: str, current_user: UserPublic = Depends(require_user)) -> dict[str, str]:
    deleted = database.delete_chat_session(session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    return {"status": "deleted"}


@router.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: UserPublic = Depends(require_user)) -> ChatResponse:
    return generate_chat_response(request, current_user)


@router.post("/api/chat/stream")
def chat_stream(request: ChatRequest, current_user: UserPublic = Depends(require_user)) -> StreamingResponse:
    session_id = request.session_id
    if session_id:
        session_row = database.get_chat_session(session_id, current_user.id)
        if not session_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    else:
        session_row = database.create_chat_session(
            user_id=current_user.id,
            mode=request.mode,
            title=chatbot.default_session_title(request.mode),
            welcome_message=chatbot.welcome_message(request.mode),
        )
        session_id = session_row["id"]

    existing_messages = database.get_chat_messages(session_id)
    history = build_effective_history(
        [{"role": item["role"], "content": item["content"]} for item in existing_messages],
        request.history,
    )
    uploaded_documents = [
        {"name": row["name"], "text": row["extracted_text"]}
        for row in database.get_uploaded_documents_for_retrieval(current_user.id)
    ]
    database.append_chat_message(session_id, "user", request.question)

    if session_row["title"] == chatbot.default_session_title(request.mode):
        database.rename_chat_session(session_id, chatbot.suggested_session_title(request.question, request.mode))

    stream, sources, result_mode = chatbot.stream_answer(
        request.question,
        history,
        request.mode,
        model=request.model,
        custom_prompt=request.custom_prompt,
        user_id=current_user.id,
        uploaded_documents=uploaded_documents,
    )

    def event_stream() -> Iterator[str]:
        built = ""
        yield json.dumps({"type": "start", "session_id": session_id, "mode": result_mode}) + "\n"
        try:
            for chunk in stream:
                built += chunk
                yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
        except Exception:
            yield json.dumps({"type": "error", "message": "Streaming failed."}) + "\n"
            return

        database.append_chat_message(session_id, "assistant", built)
        yield json.dumps(
            {
                "type": "done",
                "content": built,
                "session_id": session_id,
                "sources": [source.model_dump() for source in sources],
            }
        ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
