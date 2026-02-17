"""Chat service for managing conversations."""

from typing import Any

from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.core.logging import get_logger
from app.core.security import redact_pii
from app.db.models import Conversation, Message, SafetyCheck, User

logger = get_logger(__name__)


class ChatService:
    """Service for managing chat conversations."""

    def __init__(self, orchestrator: AgentOrchestrator):
        """
        Initialize chat service.

        Args:
            orchestrator: Agent orchestrator
        """
        self.orchestrator = orchestrator

    async def send_message(
        self,
        db: Session,
        user: User,
        conversation_id: str | None,
        content: str,
    ) -> dict[str, Any]:
        """
        Send a message and get a response.

        Args:
            db: Database session
            user: User sending the message
            conversation_id: Optional conversation ID
            content: Message content

        Returns:
            Response with message and conversation info
        """
        logger.info(
            "Processing chat message",
            user_id=user.id,
            conversation_id=conversation_id,
        )

        # Get or create conversation
        if conversation_id:
            conversation = (
                db.query(Conversation)
                .filter(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user.id,
                )
                .first()
            )
            if not conversation:
                logger.warning("Conversation not found", conversation_id=conversation_id)
                conversation = Conversation(user_id=user.id)
                db.add(conversation)
        else:
            conversation = Conversation(user_id=user.id)
            db.add(conversation)

        db.flush()

        # Store user message with PII redaction
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=redact_pii(content) if redact_pii else content,
            message_metadata={"original_length": len(content)},
        )
        db.add(user_message)
        db.flush()

        # Process message through agent pipeline
        response = await self.orchestrator.process_message(db, content)

        # Store assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response["content"],
            message_metadata={
                "citations": response.get("citations", []),
                "usage": response.get("usage", {}),
            },
        )
        db.add(assistant_message)
        db.flush()

        # Store safety check result
        safety_check = SafetyCheck(
            message_id=assistant_message.id,
            outcome=response.get("safety_outcome", "ok"),
            reason=response.get("safety_reason"),
        )
        db.add(safety_check)

        db.commit()

        logger.info(
            "Chat message processed",
            conversation_id=conversation.id,
            safety_outcome=safety_check.outcome,
        )

        return {
            "conversation_id": conversation.id,
            "message": {
                "id": assistant_message.id,
                "content": response["content"],
                "citations": response.get("citations", []),
                "safety_outcome": response.get("safety_outcome", "ok"),
            },
        }

    def get_conversation_history(
        self,
        db: Session,
        user: User,
        conversation_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get conversation history.

        Args:
            db: Database session
            user: User requesting history
            conversation_id: Conversation ID
            limit: Maximum number of messages

        Returns:
            List of messages
        """
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
            .first()
        )

        if not conversation:
            return []

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.message_metadata,
            }
            for msg in messages
        ]

    def list_conversations(
        self,
        db: Session,
        user: User,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        List user's conversations.

        Args:
            db: Database session
            user: User
            limit: Maximum number of conversations

        Returns:
            List of conversations
        """
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
            for conv in conversations
        ]
