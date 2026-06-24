from pyrogram import Client
from config import Config
import logging

logger = logging.getLogger(__name__)

# Configure Proxy
proxy_dict = None
if Config.PROXY_IP and Config.PROXY_PORT:
    proxy_dict = {
        "scheme": "socks5",
        "hostname": Config.PROXY_IP,
        "port": Config.PROXY_PORT
    }
    if Config.PROXY_USERNAME:
        proxy_dict["username"] = Config.PROXY_USERNAME
        proxy_dict["password"] = Config.PROXY_PASSWORD
    logger.info(f"Using SOCKS5 Proxy: {Config.PROXY_IP}:{Config.PROXY_PORT}")

# Primary Bot Client (2GB limit)
bot = Client(
    "renamer_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot.plugins"),
    workers=Config.WORKERS,
    proxy=proxy_dict,
    max_concurrent_transmissions=3,
    sleep_threshold=60
)

# Optional Premium Userbot Client (4GB limit)
userbot = None
if Config.STRING_SESSION:
    userbot = Client(
        "renamer_userbot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        session_string=Config.STRING_SESSION,
        workers=Config.WORKERS,
        proxy=proxy_dict,
        max_concurrent_transmissions=3,
        sleep_threshold=60
    )
    logger.info("Premium String Session detected. 4GB Userbot upgrade is ENABLED.")
else:
    logger.info("No String Session provided. Operating in standard 2GB limit mode.")

async def start_clients():
    logger.info("Starting Bot...")
    await bot.start()
    
    if userbot:
        logger.info("Starting Userbot...")
        await userbot.start()
        
    logger.info("All clients started successfully!")

async def stop_clients():
    logger.info("Stopping Bot...")
    await bot.stop()
    
    if userbot:
        logger.info("Stopping Userbot...")
        await userbot.stop()
