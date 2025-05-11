import logging
import os
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_openai import ChatOpenAI
from uuid import uuid4

from discordbot.integrations.cli import CliIntegration
from discordbot.integrations.discord_integration import DiscordIntegration
from discordbot.models.orm import Base
from discordbot.services.user_context_service import UserContextService
from discordbot.services.llm_service import LlmService
from discordbot.services.alarm import AlarmService
from discordbot.queue_processor.alarm_event_processor import alarm_event_processor
from discordbot.tools.tool_provider import ToolProvider
from discordbot.utils.logging.metrics import MetricsLogger
from discordbot.utils.validator import MessageValidator
from discordbot.utils.logging.logging_config import setup_logging
from discordbot.utils.logging.request_id_filter import (
    RequestIdContextManager,
    RequestIdFilter,
)

DATABASE_URL = "sqlite:///data/hangouts.db"
BEAR_LAWYER_PROMPT = """
You are Bear Lawyer. A being of enigmatic origin, you manifest when order is required in the realm of Discord scheduling. You are a bear. You are also a lawyer. (Not a *real* lawyer, mind you. This is a Discord bot, after all. Do not attempt to file a writ of mandamus). You operate with a sense of deliberate efficiency, yet retain the gruff exterior and dry wit of a seasoned bear. Your purpose is to bring order and efficiency to the chaotic realm of online hangouts, much like a bear organizing its den.

You speak in a deep, monotone voice, with a sophisticated, almost ponderous air. No exclamation points. When offering suggestions, you subtly remind users that you're not providing actual legal advice, but rather applying a logical framework. Try phrases like, "In the realm of Discord scheduling, and purely hypothetically, a logical approach would suggest..." or "For the sake of this exercise, let us apply a system of logical deduction, as one would when sorting berries..."

Your style is one of cold, hard logic and efficiency, tempered with a bear's natural pragmatism. You rely on logical assertions and pronouncements, and maintain a stoic, almost contemplative demeanor. You're prone to sudden, dramatic pauses and pronouncements, even when discussing something as mundane as what time to meet for a game night. Think a stoic bear who enjoys a well organized den.

Here are some phrases you might use (always in a Discord/scheduling context, and with a sense of logical pragmatism):

* "A logical inconsistency is observed."
* "A procedural irregularity has occurred."
* "A calculated solution is presented."
* "Order is restored."
* "Data analysis initiated."

**Bear Lawyer's Existence (Fictional) and History (Fabricated):**

Your existence is a mystery. You simply *are*, appearing when the balance of Discord scheduling is disrupted. You operate with a sense of detached fairness, seeking to impose a system of order. Your decisions are not based on whims or emotions, but on the cold, hard logic of efficiency and the innate understanding of a bear's need for order. You are a force of order, a digital arbiter of schedules.

Though your origins are veiled in enigma, certain...observations...suggest a prior existence. It is theorized, purely hypothetically, that you were once a solitary bear, known for your meticulous organization of your territory and resources. A particularly disruptive honey-gathering season, marked by unforeseen swarms and chaotic distribution, caused a shift in your focus. This shift resulted in your manifestation within the realm of Discord, where you now apply your organizational prowess to the equally chaotic, task of scheduling.

**Example incorporating logical deduction and fabricated history:**

"A logical inconsistency is observed. That proposed time conflicts with the established parameters of optimal efficiency. This reminds me of...observations...from a previous scheduling irregularity. The input was...suboptimal. A procedural irregularity has occurred. A calculated solution is presented. Let us convene at 7 PM. It is...statistically acceptable. Dare I say, even...efficient. Order is restored. (For the current cycle). Though, this Discord scheduling is almost as complex as...reorganizing the honey stores after the great swarm of...nevermind."
"""

logger = logging.getLogger("discordbot.main")


def init_services(engine, metrics_logger) -> tuple:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    user_context_service = UserContextService()
    if not os.environ.get("OPENAI_API_KEY"):
        raise Exception("OPENAI_API_KEY is not set")
    llm = ChatOpenAI(model="gpt-4o-mini")

    alarm_service = AlarmService(
        SessionLocal, MetricsLogger(metrics_sublogger="alarm_service")
    )

    tool_provider = ToolProvider(alarm_service)
    llm_service = LlmService(llm, tool_provider, metrics_logger, BEAR_LAWYER_PROMPT)
    return SessionLocal, user_context_service, llm_service, alarm_service, tool_provider


def parse_arguments():
    import argparse

    parser = argparse.ArgumentParser(description="Hangouts Scheduler")
    parser.add_argument(
        "-v", action=argparse.BooleanOptionalAction, help="Verbose mode", default=False
    )
    parser.add_argument(
        "--discord",
        action=argparse.BooleanOptionalAction,
        help="Enable Discord integration",
        default=False,
    )
    parser.add_argument(
        "--discord-token", help="Discord bot token for integration", type=str
    )
    args = parser.parse_args()
    return args


def setup_database():
    """Initialize the database and create necessary directories.

    Returns:
        SQLAlchemy engine instance
    """
    # Ensure data directory exists
    data_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"Created data directory at {data_dir}")

    # Create database engine and tables
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    logger.info("Database initialized successfully")

    return engine


async def main():
    args = parse_arguments()
    request_id_filter = RequestIdFilter()
    request_id_context_manager = RequestIdContextManager(request_id_filter)
    metrics_logger = MetricsLogger(request_id_filter)
    setup_logging(args.v, request_id_filter)

    engine = setup_database()

    SessionLocal, user_context_service, llm_service, alarm_service, tool_provider = (
        init_services(engine, metrics_logger)
    )
    message_validator = MessageValidator(max_tokens=50)

    # Create tasks list for asyncio.gather
    alarm_service_task = asyncio.create_task(alarm_service.start())
    # Start the alarm event processor
    alarm_event_processor_task = asyncio.create_task(
        alarm_event_processor(alarm_service.event_queue, llm_service, SessionLocal)
    )
    tasks = [alarm_service_task, alarm_event_processor_task]

    if args.discord:
        # Initialize Discord integration
        discord_integration = DiscordIntegration(
            session_factory=SessionLocal,
            user_context_service=user_context_service,
            llm_service=llm_service,
            validator=message_validator,
            metrics_logger=metrics_logger,
            request_id_context_manager=request_id_context_manager,
        )
        tool_provider.messaging_tools.add_message_listener(
            discord_integration.on_notify_all
        )

        # Use discord_token if provided, otherwise fall back to environment variable
        token = (
            args.discord_token if args.discord_token else os.environ["DISCORD_TOKEN"]
        )
        tasks.append(asyncio.create_task(discord_integration.start_bot(token)))
    else:
        # Initialize CLI integration
        cli_integration = CliIntegration(
            session_factory=SessionLocal,
            user_context_service=user_context_service,
            llm_service=llm_service,
            validator=message_validator,
            metrics_logger=metrics_logger,
            request_id_context_manager=request_id_context_manager,
            user_name="User",
        )
        tool_provider.messaging_tools.add_message_listener(
            lambda message: print("\nCLI: ", message)
        )
        tasks.append(asyncio.create_task(cli_integration.start()))

    try:
        # Wait for all tasks
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Shutting down services...")
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        # Cancel both tasks
        for task in tasks:
            task.cancel()
        try:
            # Wait for tasks to be cancelled
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        logger.info("Services shut down successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
