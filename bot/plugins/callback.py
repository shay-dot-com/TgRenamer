from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from database.db import db
from utils.state import CANCEL_TASKS
import logging

logger = logging.getLogger(__name__)

@Client.on_callback_query(filters.regex(r"^cancel_(.*)"))
async def cancel_callback(client: Client, query: CallbackQuery):
    doc_id = query.matches[0].group(1)
    
    # Mark in memory to trigger Exception in progress bar
    CANCEL_TASKS[doc_id] = True
    
    # Update DB
    from bson.objectid import ObjectId
    try:
        await db.update_status(ObjectId(doc_id), "CANCELLED")
    except Exception as e:
        logger.error(f"Error marking as cancelled in DB: {e}")
        
    await query.answer("Cancelling process... Please wait a few seconds for cleanup.", show_alert=True)
    
    # Update the message button to show it's cancelling
    await query.message.edit_reply_markup(None)
