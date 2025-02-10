import asyncio
import logging
import discord
from discord import Intents
from sqlalchemy.orm import Session
from typing import Callable

from hangoutsscheduler.services.llm_service import LlmService
from hangoutsscheduler.services.user_context_service import UserContextService
from hangoutsscheduler.utils.logging.metrics import MetricsLogger
from hangoutsscheduler.utils.logging.request_id_filter import RequestIdContextManager
from hangoutsscheduler.utils.validator import MessageValidator

logger = logging.getLogger(__name__)

class DiscordIntegration(discord.Client):
    """Discord bot integration that responds to mentions and interacts with the LLM."""
    
    def __init__(
        self,
        session_factory: Callable[[], Session],
        user_context_service: UserContextService,
        llm_service: LlmService,
        validator: MessageValidator,
        metrics_logger: MetricsLogger,
        request_id_context_manager: RequestIdContextManager,
        *args,
        **kwargs
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
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        # Only respond to mentions
        if not message.mentions or self.user not in message.mentions:
            return
            
        # Remove the mention from the message
        content = message.content.replace(f'<@{self.user.id}>', '').strip()
        if not content:
            return
            
        try:
            # Show typing indicator while processing
            async with message.channel.typing():
                with self.session_factory() as session, self.metrics_logger, self.request_id_context_manager:
                    # Get user-specific context
                    user_id = str(message.author.id)
                    validated_message = self.validator.validate_message(content)
                    message_context = self.user_context_service.resolve_chat_history(
                        session, 
                        user_id,
                        validated_message
                    )
                    
                    # Get LLM response
                    response = await self.llm_service.respond_to_user_message(message_context, session)
                    
                    # Update context with response
                    self.user_context_service.update_with_llm_response(
                        session,
                        user_id,
                        response.content
                    )
                    
                    # Send response, splitting if too long
                    if len(response.content) > 2000:
                        # Split into chunks of 2000 chars (Discord's limit)
                        chunks = [response.content[i:i+2000] for i in range(0, len(response.content), 2000)]
                        for chunk in chunks:
                            await message.reply(chunk)
                    else:
                        await message.reply(response.content)
                        
        except Exception as e:
            logger.exception(f"Error processing Discord message: {e}")
            await message.reply("I encountered an error while processing your message. Please try again later.")
    
    async def start_bot(self, token: str):
        """Start the Discord bot with the given token"""
        logger.info("Starting Discord integration")
        try:
            await self.start(token)
        except Exception as e:
            logger.exception(f"Failed to start Discord bot: {e}")
            raise
