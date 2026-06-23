import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    STRING_SESSION = os.environ.get("STRING_SESSION", "")
    MONGO_URI = os.environ.get("MONGO_URI", "")
    OWNER_ID = int(os.environ.get("OWNER_ID", 0))
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

    # Proxy Configuration
    PROXY_IP = os.environ.get("PROXY_IP", "")
    PROXY_PORT = int(os.environ.get("PROXY_PORT", 1080)) if os.environ.get("PROXY_PORT") else None
    PROXY_USERNAME = os.environ.get("PROXY_USERNAME", "")
    PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD", "")

    # Bot internal constants
    WORKERS = 100
    DB_NAME = "RenamerBot"
