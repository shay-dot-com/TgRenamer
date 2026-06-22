from pyrogram import Client, filters
from pyrogram.types import Message
from database.db import db
import logging

logger = logging.getLogger(__name__)

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def receiver(client: Client, message: Message):
    if not db:
        await message.reply_text("Database is not connected. Cannot process files.", quote=True)
        return

    # Determine file type and get file ID
    file = getattr(message, message.media.value)
    
    if file.file_size > 2000000000:
        # Check if we have 4GB support enabled
        from bot.client import userbot
        if not userbot:
            await message.reply_text("This file is larger than 2GB, but Premium 4GB support is not configured.", quote=True)
            return

    processing_msg = await message.reply_text("Added to Queue ⏳", quote=True)
    
    # Insert into MongoDB
    try:
        await db.add_to_queue(
            user_id=message.from_user.id,
            message_id=message.id,
            file_id=file.file_id,
            file_type=message.media.value
        )
    except Exception as e:
        logger.error(f"Error adding to queue: {e}")
        await processing_msg.edit_text("Failed to add to queue due to a database error.")
