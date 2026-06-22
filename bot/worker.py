import asyncio
import os
import logging
from bot.client import bot, userbot
from database.db import db
from utils.renamer import generate_new_name
from utils.metadata import get_video_info
from utils.ffmpeg import process_video, generate_thumbnail
from utils.caption import generate_caption
from utils.progress import progress_for_pyrogram
import time

logger = logging.getLogger(__name__)

# Config
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def process_item(item):
    """Processes a single item from the queue."""
    doc_id = item["_id"]
    chat_id = item["user_id"]
    message_id = item["message_id"]
    
    try:
        # Mark as processing
        await db.update_status(doc_id, "PROCESSING")
        
        # Get message
        client = userbot if userbot else bot
        try:
            message = await client.get_messages(chat_id, message_id)
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            await db.update_status(doc_id, "FAILED")
            return
            
        if not message or not message.media:
            await db.update_status(doc_id, "FAILED")
            return
            
        file = getattr(message, message.media.value)
        original_name = getattr(file, "file_name", "Unknown_File.mp4")
        original_size = getattr(file, "file_size", 0)
        
        # 1. Generate new name
        new_name = generate_new_name(original_name)
        
        # 2. Download
        logger.info(f"Downloading: {original_name}")
        status_msg = await bot.send_message(chat_id, f"📥 Downloading: `{original_name}`")
        
        input_path = os.path.join(DOWNLOAD_DIR, f"in_{message_id}_{original_name}")
        output_path = os.path.join(DOWNLOAD_DIR, new_name)
        
        start_time = time.time()
        await client.download_media(
            message,
            file_name=input_path,
            progress=progress_for_pyrogram,
            progress_args=(f"📥 **Downloading:** `{original_name}`", status_msg, start_time)
        )
        
        # 3. Extract Metadata
        await status_msg.edit_text("⚙️ Processing Metadata...")
        info = await get_video_info(input_path)
        
        # 4. Process via FFmpeg
        await status_msg.edit_text("🔨 Running FFmpeg...")
        success = await process_video(input_path, output_path, new_name)
        
        if not success:
            raise Exception("FFmpeg processing failed")
            
        # 4.5. Thumbnail Generation/Download
        thumb_path = None
        custom_thumb_id = await db.get_thumbnail(chat_id)
        
        if custom_thumb_id:
            await status_msg.edit_text("🖼 Downloading Custom Thumbnail...")
            thumb_path = os.path.join(DOWNLOAD_DIR, f"thumb_{message_id}.jpg")
            try:
                # We need to get the message object containing the photo or just download by file_id
                # Kurigram can download by file_id
                await client.download_media(custom_thumb_id, file_name=thumb_path)
            except Exception as e:
                logger.error(f"Failed to download custom thumb: {e}")
                thumb_path = None
        else:
            await status_msg.edit_text("🖼 Generating Thumbnail...")
            thumb_path = os.path.join(DOWNLOAD_DIR, f"auto_thumb_{message_id}.jpg")
            thumb_success = await generate_thumbnail(output_path, thumb_path, info.get("duration", 0))
            if not thumb_success or not os.path.exists(thumb_path):
                thumb_path = None

        # 5. Generate Caption
        caption = generate_caption(new_name, info, original_size)
        
        # 6. Upload
        await status_msg.edit_text("📤 Uploading...")
        
        upload_start_time = time.time()
        await client.send_document(
            chat_id,
            document=output_path,
            thumb=thumb_path,
            caption=caption,
            file_name=new_name,
            progress=progress_for_pyrogram,
            progress_args=(f"📤 **Uploading:** `{new_name}`", status_msg, upload_start_time)
        )
        
        # Clean up
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        
        await status_msg.delete()
        await db.update_status(doc_id, "COMPLETED")
        logger.info(f"Successfully processed {new_name}")
        
    except Exception as e:
        logger.error(f"Error processing item {doc_id}: {e}")
        await db.update_status(doc_id, "FAILED")
        await bot.send_message(chat_id, "❌ An error occurred while processing your file.")

async def queue_worker():
    """Background loop that continuously checks for pending items."""
    logger.info("Starting Queue Worker...")
    
    # On startup, mark any 'PROCESSING' items back to 'PENDING' for crash-recovery
    await db.queue.update_many({"status": "PROCESSING"}, {"$set": {"status": "PENDING"}})
    
    while True:
        try:
            # Fetch 1 pending item at a time
            pending_items = await db.queue.find({"status": "PENDING"}).limit(1).to_list(length=1)
            
            if pending_items:
                item = pending_items[0]
                await process_item(item)
            else:
                # Sleep briefly if queue is empty
                await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Worker Loop Error: {e}")
            await asyncio.sleep(5)
