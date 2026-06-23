from pyrogram import Client, filters
from pyrogram.types import Message
import psutil
import time
from database.db import db

# Record start time for uptime calculation
START_TIME = time.time()

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "
    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    # Fetch system stats
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram_info = psutil.virtual_memory()
    ram_percent = ram_info.percent
    
    # Calculate Uptime
    uptime_sec = int(time.time() - START_TIME)
    uptime_str = get_readable_time(uptime_sec)
    
    # Get Queue Stats
    pending_count, processing_count = await db.get_queue_count()
    total_queue = pending_count + processing_count
    
    stats_text = (
        "**📊 System Performance**\n\n"
        f"**CPU Usage:** `{cpu_percent}%`\n"
        f"**RAM Usage:** `{ram_percent}%`\n"
        f"**Uptime:** `{uptime_str}`\n\n"
        "**📥 Active Queue Status**\n"
        f"**Processing Now:** `{processing_count} files`\n"
        f"**Waiting in Queue:** `{pending_count} files`\n"
        f"**Total Backlog:** `{total_queue} files`"
    )
    
    await message.reply_text(stats_text, quote=True)
