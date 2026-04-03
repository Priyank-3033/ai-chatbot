import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import auth_service, chatbot, database


router = APIRouter()


def trim_history(history: list[dict[str, str]], max_messages: int = 10) -> list[dict[str, str]]:
    return history[-max_messages:]


def build_effective_history(existing_messages: list[dict[str, str]], request_history: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    if len(existing_messages) > 1:
        return trim_history(existing_messages, max_messages=10)
    request_history = request_history or []
    normalized_request_history = [
        {
            "role": str(item.get("role", "user")),
            "content": str(item.get("content", "")).strip(),
        }
        for item in request_history
        if str(item.get("content", "")).strip()
    ]
    return trim_history(existing_messages + normalized_request_history, max_messages=10)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    try:
        user_id = auth_service.parse_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    user_row = database.get_user_by_id(user_id)
    if not user_row:
        await websocket.close(code=4401)
        return

    await websocket.accept()

    try:
        while True:
            payload = await websocket.receive_json()
            question = str(payload.get("question", "")).strip()
            mode = str(payload.get("mode", "general"))
            model = payload.get("model")
            custom_prompt = payload.get("custom_prompt")
            session_id = payload.get("session_id")
            request_history = payload.get("history") or []

            if not question:
                await websocket.send_json({"type": "error", "message": "Question is required."})
                continue

            if session_id:
                session_row = database.get_chat_session(session_id, user_id)
                if not session_row:
                    await websocket.send_json({"type": "error", "message": "Chat session not found."})
                    continue
            else:
                session_row = database.create_chat_session(
                    user_id=user_id,
                    mode=mode,
                    title=chatbot.default_session_title(mode),
                    welcome_message=chatbot.welcome_message(mode),
                )
                session_id = session_row["id"]

            existing_messages = database.get_chat_messages(session_id)
            history = build_effective_history(
                [{"role": item["role"], "content": item["content"]} for item in existing_messages],
                request_history,
            )
            uploaded_documents = [
                {"name": row["name"], "text": row["extracted_text"]}
                for row in database.get_uploaded_documents_for_retrieval(user_id)
            ]
            database.append_chat_message(session_id, "user", question)

            response = chatbot.answer(
                question,
                history,
                mode,
                model=model,
                custom_prompt=custom_prompt,
                user_id=user_id,
                uploaded_documents=uploaded_documents,
            )
            database.append_chat_message(session_id, "assistant", response.answer)

            await websocket.send_json({"type": "start", "session_id": session_id, "mode": response.mode})
            built = ""
            for char in response.answer:
                built += char
                await websocket.send_json({"type": "chunk", "content": char})
                await asyncio.sleep(0.005)
            await websocket.send_json({"type": "done", "content": built, "session_id": session_id, "sources": [source.model_dump() for source in response.sources]})
    except WebSocketDisconnect:
        return
