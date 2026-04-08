"""Chat routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.dependencies import get_chat_service
from app.api.schemas.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationListItem,
    MessageListItem,
)
from app.core.logging import get_logger
from app.db.connection import get_db
from app.db.models import User
from app.services.chat_service import ChatService

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """
    Send a chat message and get a response.

    The system will:
    1. Check input for safety violations
    2. Retrieve relevant information from knowledge base
    3. Generate a response with citations
    4. Check output for safety
    5. Return final response
    """
    logger.info("Chat request", user_id=current_user.id)

    try:
        response = await chat_service.send_message(
            db=db,
            user=current_user,
            conversation_id=request.conversation_id,
            content=request.message,
        )

        return ChatResponse(
            conversation_id=response["conversation_id"],
            message=ChatMessage(
                id=response["message"]["id"],
                content=response["message"]["content"],
                citations=[Citation(**citation) for citation in response["message"]["citations"]],
                safety_outcome=response["message"]["safety_outcome"],
            ),
        )

    except Exception as e:
        logger.error("Chat request failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/conversations", response_model=list[ConversationListItem])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> list[ConversationListItem]:
    """List user's conversations."""
    conversations = chat_service.list_conversations(db, current_user)
    return [ConversationListItem(**conv) for conv in conversations]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageListItem])
def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> list[MessageListItem]:
    """Get conversation history."""
    messages = chat_service.get_conversation_history(db, current_user, conversation_id)
    return [MessageListItem(**msg) for msg in messages]
