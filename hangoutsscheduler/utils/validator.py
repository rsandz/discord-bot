import logging

logger = logging.getLogger(__name__)

class MessageValidator:
    """Validator for messages."""

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens

    def validate_message(self, message: str) -> str:
        return self.validate_token_count(message)

    def validate_token_count(self, message: str) -> str:
        tokens = message.split()
        if len(tokens) > self.max_tokens:
            logger.info(f"Message exceeds the maximum allowed tokens ({self.max_tokens}). Truncating message.")
            return ' '.join(tokens[:self.max_tokens])
        return message
