from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from takehome.db.models import Message
from takehome.db.session import get_session
from takehome.services.citations import analyze_response
from takehome.services.conversation import get_conversation, update_conversation
from takehome.services.document import get_documents_for_conversation
from takehome.services.llm import CITATION_MARKER, chat_with_document, generate_title

logger = structlog.get_logger()

router = APIRouter(tags=["messages"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class CitationOut(BaseModel):
    document_id: str | None = None
    document_name: str
    quote: str
    label: str | None = None
    page: int | None = None
    verified: bool


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources_cited: int
    grounded: bool | None = None
    confidence: str | None = None
    citations: list[CitationOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


def message_to_out(m: Message) -> MessageOut:
    """Build the API representation of a message, decoding stored citations."""
    citations: list[CitationOut] = []
    if m.citations:
        try:
            citations = [CitationOut(**c) for c in json.loads(m.citations)]
        except (json.JSONDecodeError, TypeError, ValueError):
            citations = []
    return MessageOut(
        id=m.id,
        conversation_id=m.conversation_id,
        role=m.role,
        content=m.content,
        sources_cited=m.sources_cited,
        grounded=m.grounded,
        confidence=m.confidence,
        citations=citations,
        created_at=m.created_at,
    )


class MessageCreate(BaseModel):
    content: str


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.get(
    "/api/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
async def list_messages(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[MessageOut]:
    """List all messages in a conversation, ordered by creation time."""
    # Verify the conversation exists
    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await session.execute(stmt)
    messages = list(result.scalars().all())

    return [message_to_out(m) for m in messages]


@router.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Send a user message and stream back the AI response via SSE."""
    # Verify the conversation exists
    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save the user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=body.content,
    )
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    logger.info("User message saved", conversation_id=conversation_id, message_id=user_message.id)

    # Load every document in the conversation so answers can span all of them
    documents = await get_documents_for_conversation(session, conversation_id)
    document_payload = [
        {"id": d.id, "filename": d.filename, "text": d.extracted_text or ""}
        for d in documents
        if d.extracted_text
    ]

    # Load conversation history (exclude the message we just saved, it will be the user_message param)
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .where(Message.id != user_message.id)
        .order_by(Message.created_at.asc())
    )
    result = await session.execute(stmt)
    history_messages = list(result.scalars().all())

    conversation_history: list[dict[str, str]] = [
        {"role": m.role, "content": m.content} for m in history_messages
    ]

    # Determine if this is the first user message (for title generation)
    user_msg_count = sum(1 for m in history_messages if m.role == "user")
    is_first_message = user_msg_count == 0

    async def event_stream() -> AsyncIterator[str]:
        """Generate SSE events with the streamed LLM response."""
        full_response = ""
        emitted = 0  # length of prose already streamed to the client

        try:
            async for chunk in chat_with_document(
                user_message=body.content,
                documents=document_payload,
                conversation_history=conversation_history,
            ):
                full_response += chunk
                # Stream only the prose answer; withhold the citation JSON block
                # so the user never sees the raw machine-readable trailer.
                prose = full_response.split(CITATION_MARKER, 1)[0]
                if CITATION_MARKER in full_response:
                    safe = prose
                else:
                    # Hold back a marker-length tail in case the marker is mid-arrival.
                    safe = prose[: max(0, len(prose) - len(CITATION_MARKER))]
                if len(safe) > emitted:
                    delta = safe[emitted:]
                    emitted = len(safe)
                    event_data = json.dumps({"type": "content", "content": delta})
                    yield f"data: {event_data}\n\n"

        except Exception:
            logger.exception(
                "Error during LLM streaming",
                conversation_id=conversation_id,
            )
            error_msg = "I'm sorry, an error occurred while generating a response. Please try again."
            full_response = error_msg
            emitted = len(error_msg)
            event_data = json.dumps({"type": "content", "content": error_msg})
            yield f"data: {event_data}\n\n"

        # Flush any prose still held back (when no citation marker ever arrived).
        prose_final = full_response.split(CITATION_MARKER, 1)[0]
        if len(prose_final) > emitted:
            event_data = json.dumps({"type": "content", "content": prose_final[emitted:]})
            yield f"data: {event_data}\n\n"

        # Parse the trailer and verify every cited quote against the source text.
        analysis = analyze_response(full_response, document_payload)
        answer = analysis["answer"] or prose_final.strip()
        citations = analysis["citations"]
        verified_count = sum(1 for c in citations if c["verified"])
        citations_json = json.dumps(citations)

        # Save the assistant message to the database.
        # We need a fresh session since the outer one may have been closed.
        from takehome.db.session import async_session as session_factory

        async with session_factory() as save_session:
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                sources_cited=verified_count,
                grounded=analysis["grounded"],
                confidence=analysis["confidence"],
                citations=citations_json,
            )
            save_session.add(assistant_message)
            await save_session.commit()
            await save_session.refresh(assistant_message)

            # Auto-generate title from first user message
            if is_first_message:
                try:
                    title = await generate_title(body.content)
                    await update_conversation(save_session, conversation_id, title)
                    logger.info(
                        "Auto-generated conversation title",
                        conversation_id=conversation_id,
                        title=title,
                    )
                except Exception:
                    logger.exception(
                        "Failed to generate title",
                        conversation_id=conversation_id,
                    )

            # Send the final message event with the complete assistant message
            message_data = json.dumps(
                {
                    "type": "message",
                    "message": message_to_out(assistant_message).model_dump(mode="json"),
                }
            )
            yield f"data: {message_data}\n\n"

            # Send the done signal
            done_data = json.dumps(
                {
                    "type": "done",
                    "sources_cited": verified_count,
                    "message_id": assistant_message.id,
                }
            )
            yield f"data: {done_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
