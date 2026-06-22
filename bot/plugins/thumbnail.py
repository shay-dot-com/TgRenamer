from pyrogram import Client, filters
from pyrogram.types import Message
from database.db import db
import logging

logger = logging.getLogger(__name__)

@Client.on_message(filters.private & filters.photo)
async def save_thumbnail(client: Client, message: Message):
    if not db:
        await message.reply_text("Database not connected.", quote=True)
        return
        
    file_id = message.photo.file_id
    await db.set_thumbnail(message.from_user.id, file_id)
    await message.reply_text("✅ Custom thumbnail saved successfully!\nThis will be applied to all your future files.", quote=True)

@Client.on_message(filters.command("viewthumb") & filters.private)
async def view_thumbnail(client: Client, message: Message):
    if not db:
        return
        
    file_id = await db.get_thumbnail(message.from_user.id)
    if file_id:
        await message.reply_photo(file_id, caption="🖼 This is your current custom thumbnail.")
    else:
        await message.reply_text("You don't have any custom thumbnail saved.\nSend me a photo to set one!", quote=True)

@Client.on_message(filters.command("delthumb") & filters.private)
async def delete_thumbnail(client: Client, message: Message):
    if not db:
        return
        
    await db.delete_thumbnail(message.from_user.id)
    await message.reply_text("🗑 Custom thumbnail deleted.\nI will now extract automatic thumbnails from the videos.", quote=True)
