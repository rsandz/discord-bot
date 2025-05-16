import logging
from sqlalchemy.orm import Session

from .models.user_context import UserContext
from discordbot.models.message import TimeStampedMessage
from .orm.user_context import UserContextORM

logger = logging.getLogger(__name__)

class UserContextService:
    """Resolves information about the user."""

    CHAT_HISTORY_LIMIT = 16
    """Max number of messages to keep in user context."""

    def create_user_context(self, session: Session, user_id: str, user_name: str) -> UserContext:
        """Creates a new user context in the DB"""
        user_context = UserContext(user_id=user_id, user_name=user_name, user_chat_history=[])
        user_context_orm = UserContextORM.from_user_context(user_context)
        session.add(user_context_orm)
        logger.info(f"Created user context for user {user_id}")
        return user_context

    def resolve_user_context(self, session: Session, user_id: str) -> UserContext | None:
        """Resolves the user context from the DB"""
        user_context_orm = session.get(UserContextORM, user_id)
        if user_context_orm is None:
            return None
        logger.info(f"Resolved user context for user {user_id}")
        return user_context_orm.to_user_context()

        
    def append_message_to_user_context(self, session: Session, user_id: str, message: TimeStampedMessage):
        """Appends a message to the user context DB"""

        session.flush() # In case user context was just created

        user_context_orm = session.get(UserContextORM, user_id)
        if user_context_orm is None:
            raise ValueError(f"User context not found for user {user_id}")

        user_context_orm.user_chat_history = [*user_context_orm.user_chat_history, message][-self.CHAT_HISTORY_LIMIT:]
        session.add(user_context_orm)

        logger.info(f"Appended message with ID {message.id} to user context for user {user_id}")


        

        