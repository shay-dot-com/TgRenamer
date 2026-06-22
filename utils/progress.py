import time
import math
import asyncio
from pyrogram.types import Message, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified
from utils.caption import get_readable_size, get_readable_time
from utils.state import CANCEL_TASKS

async def progress_for_pyrogram(current, total, ud_type, message: Message, start, doc_id: str, reply_markup: InlineKeyboardMarkup = None):
    # Check for cancellation
    if CANCEL_TASKS.get(doc_id):
        raise asyncio.CancelledError("User cancelled the process.")

    now = time.time()
    diff = now - start
    
    # Update progress every 3 seconds to avoid FloodWait
    if round(diff % 3.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff)
        time_to_completion = round((total - current) / speed) if speed > 0 else 0
        
        estimated_total_time = elapsed_time + time_to_completion
        
        elapsed_time_str = get_readable_time(elapsed_time)
        eta_str = get_readable_time(time_to_completion)
        
        progress_str = "[{0}{1}] {2}%\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 5))]),
            ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2)
        )
        
        tmp = progress_str + \
            "{0} of {1}\nSpeed: {2}/s\nETA: {3}\n".format(
                get_readable_size(current),
                get_readable_size(total),
                get_readable_size(speed),
                eta_str if eta_str != "00:00:00" else "00:00:00"
            )
            
        try:
            await message.edit_text(
                text=f"{ud_type}\n\n{tmp}",
                reply_markup=reply_markup
            )
        except MessageNotModified:
            pass
        except Exception as e:
            # Ignore other edit errors like FloodWait
            pass
