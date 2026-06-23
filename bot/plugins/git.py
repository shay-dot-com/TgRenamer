from pyrogram import filters, Client
from pyrogram.types import Message
from config import Config
import asyncio
import os
import sys

@Client.on_message(filters.command("gitpull") & filters.user(Config.OWNER_ID))
async def git_pull_command(client: Client, message: Message):
    if len(message.command) > 1:
        branch = message.command[1]
    else:
        branch = "main"

    m = await message.reply_text(f"🔄 **Pulling from branch:** `{branch}`...")

    try:
        # Run git pull command
        process = await asyncio.create_subprocess_shell(
            f"git pull origin {branch}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode('utf-8').strip()
        error = stderr.decode('utf-8').strip()
        
        result_text = f"**Git Pull Executed!**\n\n**Output:**\n`{output}`"
        if error and "From https://github.com" not in error:
            result_text += f"\n\n**Warnings/Errors:**\n`{error}`"
            
        result_text += "\n\n♻️ **Restarting bot automatically...**"
        
        await m.edit_text(result_text)
        
        # Give Telegram a second to deliver the message before killing the process
        await asyncio.sleep(1)
        os.system("pm2 restart renamer")
        sys.exit(0)
        
    except Exception as e:
        await m.edit_text(f"❌ **Error executing git pull:**\n`{str(e)}`")
