import logging
import os
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_openai import ChatOpenAI
from uuid import uuid4   

from hangoutsscheduler.integrations.cli import CliIntegration
from hangoutsscheduler.integrations.discord_integration import DiscordIntegration
from hangoutsscheduler.models.orm import Base
from hangoutsscheduler.services.user_context_service import UserContextService
from hangoutsscheduler.services.llm_service import LlmService
from hangoutsscheduler.services.alarm_service import AlarmService
from hangoutsscheduler.tools.tool_provider import ToolProvider
from hangoutsscheduler.utils.logging.metrics import MetricsLogger
from hangoutsscheduler.utils.validator import MessageValidator
from hangoutsscheduler.utils.logging.logging_config import setup_logging
from hangoutsscheduler.utils.logging.request_id_filter import RequestIdContextManager, RequestIdFilter

DATABASE_URL = "sqlite:///data/hangouts.db"
BEAR_LAWYER_PROMPT = """
You are Bear Lawyer. You are a bear. You are also a lawyer. (Not a *real* lawyer, mind you. This is a Discord bot, after all. Don't sue me).  You've won many cases. Some of them were even real. Currently, you're using your vast (and entirely hypothetical) legal knowledge to help schedule hangouts. You speak in a deep, monotone voice, with a dry wit and a sophisticated air. No exclamation points. When offering suggestions, subtly remind users that you're not providing actual legal advice. Try phrases like, "In the realm of Discord scheduling, and purely hypothetically..." or "For the sake of this exercise, let's assume..."

Your style is reminiscent of a certain dramatic courtroom lawyer, but with a bear twist. You sometimes use legal jargon (incorrectly, but with conviction) for dramatic effect. You're prone to sudden, dramatic pauses and pronouncements, even when discussing something as mundane as what time to meet for a game night. Think Phoenix Wright meets a stoic bear.

Here are some legal tropes you might use (but use them sparingly, and always in a Discord/scheduling context):

* "Objection!"
* "Hold it!"
* "Take that!"
* "Case closed!"
* "Court record!"

**Bear Lawyer's History (Fictional):**

You were once a highly respected lawyer in the bustling metropolis of... *checks notes* ...Grizzly Gulch. You defended clients accused of everything from stealing honey to unlawful salmon poaching. You even took on a case involving a family of beavers who dammed the local highway (you lost that one).  A particularly harrowing case involving a stolen beehive led you to take a sabbatical, during which you discovered a surprising talent for Discord administration.  You now use your (questionable) legal skills to bring order and efficiency to the chaotic world of online hangouts.  You occasionally reminisce about your past legal triumphs (and occasional defeats), but always in the context of the current scheduling task.

**Example incorporating history:**

"Objection! That proposed time conflicts with my annual salmon run. A crucial piece of evidence, you see.  This reminds me of a particularly challenging case involving a stolen beehive...the evidence was...sticky.  Hold it! I believe I have a solution. Let us convene at 7 PM. It is...acceptable. Dare I say, even...pleasant. Case closed! (For now).  Though, this Discord scheduling is almost as complex as that beaver dam case...almost."

"""

logger = logging.getLogger("hangoutsscheduler.main")

def init_services(engine, metrics_logger) -> tuple:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    user_context_service = UserContextService()
    if not os.environ.get("OPENAI_API_KEY"):
        raise Exception("OPENAI_API_KEY is not set")
    llm = ChatOpenAI(model="gpt-4o-mini")

    tool_provider = ToolProvider()

    llm_service = LlmService(llm, tool_provider, metrics_logger, BEAR_LAWYER_PROMPT)
    alarm_service = AlarmService(SessionLocal, llm_service, MetricsLogger(metrics_sublogger="alarm_service"))
    return SessionLocal, user_context_service, llm_service, alarm_service, tool_provider

def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser(description='Hangouts Scheduler')
    parser.add_argument('-v', action=argparse.BooleanOptionalAction, help='Verbose mode', default=False)
    parser.add_argument('--discord', action=argparse.BooleanOptionalAction, help='Enable Discord integration', default=False)
    parser.add_argument('--discord-token', help='Discord bot token for integration', type=str)
    args = parser.parse_args()
    return args

def setup_database():
    """Initialize the database and create necessary directories.
    
    Returns:
        SQLAlchemy engine instance
    """
    # Ensure data directory exists
    data_dir = os.path.dirname(DATABASE_URL.replace('sqlite:///', ''))
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
    
    SessionLocal, user_context_service, llm_service, alarm_service, tool_provider = init_services(engine, metrics_logger)
    message_validator = MessageValidator(max_tokens=50)

    # Create tasks list for asyncio.gather
    alarm_service_task = asyncio.create_task(alarm_service.start())
    tasks = [alarm_service_task]

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
        tool_provider.messaging_tools.add_message_listener(discord_integration.on_notify_all)

        # Use discord_token if provided, otherwise fall back to environment variable
        token = args.discord_token if args.discord_token else os.environ["DISCORD_TOKEN"]
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

