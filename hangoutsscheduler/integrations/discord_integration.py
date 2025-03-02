import logging
import discord
from discord import Intents
from langchain_core.messages import SystemMessage
from sqlalchemy.orm import Session
from typing import Callable, List, Optional

from hangoutsscheduler.constants import AI_MESSAGE_TYPE, USER_MESSAGE_TYPE
from hangoutsscheduler.models.message_context import (
    ChatMessage,
    MessageContextChatHistory,
)
from hangoutsscheduler.services.llm_service import LlmService, UserPromptTransformer
from hangoutsscheduler.services.user_context_service import UserContextService
from hangoutsscheduler.utils.logging.metrics import MetricsLogger
from hangoutsscheduler.utils.logging.request_id_filter import RequestIdContextManager
from hangoutsscheduler.utils.validator import MessageValidator

logger = logging.getLogger(__name__)


class DiscordIntegration(discord.Client):
    """Discord bot integration that responds to mentions and interacts with the LLM."""

    MAX_LLM_CHANNEL_MESSAGE_CONTEXT = 10
    CHANNEL_CHAT_HISTORY_NAME = "Discord Channel"
    CHANNEL_CHAT_HISTORY_DESCRIPTION = "Chat history of the Discord channel"

    def __init__(
        self,
        session_factory: Callable[[], Session],
        user_context_service: UserContextService,
        llm_service: LlmService,
        validator: MessageValidator,
        metrics_logger: MetricsLogger,
        request_id_context_manager: RequestIdContextManager,
        *args,
        **kwargs,
    ):
        # Set up required intents
        intents = Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)

        self.session_factory = session_factory
        self.user_context_service = user_context_service
        self.llm_service = llm_service
        self.validator = validator
        self.metrics_logger = metrics_logger
        self.request_id_context_manager = request_id_context_manager

    async def setup_hook(self):
        """Called when the client is done preparing data"""
        logger.info("Discord bot is setting up")

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        logger.info(f"Discord bot {self.user} is ready and connected to Discord!")

    async def on_notify_all(self, message: str):
        logger.info(f"Discord bot notifying all users: {message}")
        for channel in self.get_all_channels():
            if channel.type == discord.ChannelType.text:
                await channel.send(message)

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        if not self.user:
            raise Exception("Discord user ID is not set")

        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        is_mention = message.mentions and self.user in message.mentions

        # For non-mentions, check if it's a question and if there was a recent interaction
        is_question = message.content.strip().endswith("?")
        has_recent_interaction = False

        if not is_mention and is_question:
            has_recent_interaction = await self._check_recent_interaction(message)

        # Only respond to mentions or questions with recent interactions
        if not (is_mention or (is_question and has_recent_interaction)):
            return

        if isinstance(message.channel, (discord.DMChannel, discord.PartialMessageable)):
            return

        channel_name = str(message.channel.name)
        trigger_type = "mention" if is_mention else "follow-up question"
        logger.info(
            f"Discord bot responding to {trigger_type} in channel {channel_name}: {message.content}"
        )
        channel_history = message.channel.history(
            limit=self.MAX_LLM_CHANNEL_MESSAGE_CONTEXT
        )
        transformed_channel_history = MessageContextChatHistory(
            name=self.CHANNEL_CHAT_HISTORY_NAME,
            description=self.CHANNEL_CHAT_HISTORY_DESCRIPTION,
            messages=self.transform_channel_history(
                [message async for message in channel_history]
            ),
        )

        server_name = message.guild.name if message.guild else None
        user_name = message.author.display_name

        server_channel_context_prompt_transformer = (
            self._create_server_channel_context_transformer(channel_name, server_name)
        )

        user_name_context_prompt_transformer = (
            self._create_user_name_context_transformer(
                user_name, user_id=str(message.author.id)
            )
        )

        content = message.content.replace(f"<@{self.user.id}>", "").strip()
        if not content:
            return

        try:
            async with message.channel.typing():
                with (
                    self.session_factory() as session,
                    self.metrics_logger,
                    self.request_id_context_manager,
                ):
                    user_id = str(message.author.id)
                    validated_message = self.validator.validate_message(content)
                    new_chat_message = ChatMessage(
                        type=USER_MESSAGE_TYPE,
                        content=validated_message,
                        datetime=message.created_at,
                        id=str(message.id),
                    )
                    message_context = self.user_context_service.resolve_chat_history(
                        session, user_id, new_chat_message
                    )
                    message_context.histories.append(transformed_channel_history)

                    response = await self.llm_service.respond_to_user_message(
                        message_context,
                        session,
                        additional_transformers=[
                            server_channel_context_prompt_transformer,
                            user_name_context_prompt_transformer,
                        ],
                    )
                    response_content = str(response.content)
                    new_ai_response = ChatMessage(
                        type=AI_MESSAGE_TYPE,
                        content=response_content,
                        datetime=message.created_at,
                        id=str(message.id),
                    )

                    self.user_context_service.update_with_llm_response(
                        session, user_id, new_ai_response
                    )

                    # Send response, splitting if too long
                    if len(response_content) > 2000:
                        # Split into chunks of 2000 chars (Discord's limit)
                        chunks = [
                            response_content[i : i + 2000]
                            for i in range(0, len(response_content), 2000)
                        ]
                        for chunk in chunks:
                            await message.reply(chunk)
                    else:
                        await message.reply(response_content)

        except Exception as e:
            logger.exception(f"Error processing Discord message: {e}")
            await message.reply(
                "I encountered an error while processing your message. Please try again later."
            )

    async def start_bot(self, token: str):
        """Start the Discord bot with the given token"""
        logger.info("Starting Discord integration")
        try:
            await self.start(token)
        except Exception as e:
            logger.exception(f"Failed to start Discord bot: {e}")
            raise

    def transform_channel_history(
        self, history: list[discord.Message]
    ) -> list[ChatMessage]:
        return [
            ChatMessage(
                type=(
                    AI_MESSAGE_TYPE
                    if message.author == self.user
                    else USER_MESSAGE_TYPE
                ),
                content=message.content,
                datetime=message.created_at,
                id=str(message.id),
            )
            for message in history
        ]

    def _create_server_channel_context_transformer(
        self, channel_name: str, server_name: Optional[str] = None
    ) -> UserPromptTransformer:
        """Create a prompt transformer that adds Discord server and channel context.

        Args:
            channel_name: The name of the channel
            server_name: The name of the server (optional)

        Returns:
            A transformer function that adds server and channel context to the prompt
        """
        if server_name:
            return lambda prompt: [
                SystemMessage(
                    f"You are responding to a message in Discord Server: {server_name}, Channel: {channel_name}"
                ),
                *prompt,
            ]
        else:
            return lambda prompt: [
                SystemMessage(
                    f"You are responding to a message in Discord Channel: {channel_name}"
                ),
                *prompt,
            ]

    async def _check_recent_interaction(self, message: discord.Message) -> bool:
        """Check if the user had a recent interaction with the bot.

        This method determines if the bot should respond to a question without being mentioned
        by checking if the bot responded to the same user within the last 60 seconds.

        Args:
            message: The current message to check

        Returns:
            True if there was a recent interaction, False otherwise
        """
        async for prev_msg in message.channel.history(limit=10, before=message):
            if (
                prev_msg.author == self.user
                and (message.created_at - prev_msg.created_at).total_seconds() < 60
            ):
                async for user_msg in message.channel.history(limit=5, before=prev_msg):
                    if user_msg.author == message.author:
                        return True

        return False

    def _create_user_name_context_transformer(
        self, user_name: str, user_id: str
    ) -> UserPromptTransformer:
        """Create a prompt transformer that adds the user's name to the context.

        Args:
            user_name: The display name of the user
            user_id: The ID of the user

        Returns:
            A transformer function that adds user name context to the prompt
        """
        return lambda prompt: [
            SystemMessage(
                f"You are talking to Discord user: {user_name} (ID: {user_id})"
            ),
            *prompt,
        ]
