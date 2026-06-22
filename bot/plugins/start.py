from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    welcome_text = (
        f"Hello {message.from_user.mention}! 👋\n\n"
        "I am an advanced File Renamer Bot.\n"
        "Just send me any file (Video/Document) and I will intelligently rename it based on my regex rules!"
    )
    await message.reply_text(welcome_text, quote=True)
