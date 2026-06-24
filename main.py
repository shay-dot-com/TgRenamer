import asyncio
import logging
from pyrogram import idle
from bot.client import start_clients, stop_clients
from bot.worker import queue_worker

# Setup standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing Bot Services...")
    
    try:
        await start_clients()
        
        # Start 2 parallel background workers to prevent bandwidth starvation
        for _ in range(2):
            asyncio.create_task(queue_worker())
        
        logger.info("Bot is running with 2 parallel workers! Press Ctrl+C to stop.")
        await idle()
        
    except KeyboardInterrupt:
        logger.warning("Keyboard interrupt received.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await stop_clients()
        logger.info("Bot shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
