import time
import math
import asyncio
import logging
from pyrogram.types import Message, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified, FloodWait
from utils.caption import get_readable_size, get_readable_time
from utils.state import CANCEL_TASKS

logger = logging.getLogger(__name__)

LAST_UPDATE = {}
SPEED_TRACKER = {}

async def progress_for_pyrogram(current, total, ud_type, message: Message, start, doc_id: str, reply_markup: InlineKeyboardMarkup = None):
    # Check for cancellation
    if CANCEL_TASKS.get(doc_id):
        raise asyncio.CancelledError("User cancelled the process.")

    now = time.time()
    diff = now - start
    
    # Proper timing: strictly update every 5 seconds
    if doc_id not in LAST_UPDATE:
        LAST_UPDATE[doc_id] = start
        SPEED_TRACKER[doc_id] = {"time": start, "bytes": 0}

    if (now - LAST_UPDATE[doc_id] < 5) and (current != total):
        return
        
    # Calculate instantaneous speed over the last interval (5 seconds)
    last_time = SPEED_TRACKER[doc_id]["time"]
    last_bytes = SPEED_TRACKER[doc_id]["bytes"]
    
    window_diff = now - last_time
    bytes_diff = current - last_bytes
    
    speed = bytes_diff / window_diff if window_diff > 0 else 0
    
    # Update trackers
    LAST_UPDATE[doc_id] = now
    SPEED_TRACKER[doc_id] = {"time": now, "bytes": current}
    
    percentage = current * 100 / total
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
    except FloodWait as e:
        logger.warning(f"Progress bar FloodWait! Telegram wants us to wait {e.value}s.")
    except Exception as e:
        logger.error(f"Progress callback error: {e}")

    # Cleanup LAST_UPDATE if done
    if current == total:
        if doc_id in LAST_UPDATE: del LAST_UPDATE[doc_id]
        if doc_id in SPEED_TRACKER: del SPEED_TRACKER[doc_id]
