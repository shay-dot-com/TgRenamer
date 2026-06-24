import math
import asyncio
import os
import time
import logging
from aiofiles import open as aiopen
from bot.client import bot, fast_clients, userbot

logger = logging.getLogger(__name__)

async def fast_download(message, output_path: str, progress_cb=None, progress_args=()):
    """
    Downloads media using multiple parallel TCP connections to bypass DC throttling.
    """
    # Identify the media type
    available_media = ("audio", "document", "photo", "sticker", "animation", "video", "voice", "video_note")
    media = None
    for kind in available_media:
        media = getattr(message, kind, None)
        if media is not None:
            break
            
    if not media:
        raise ValueError("Message does not contain any downloadable media.")
        
    file_size = getattr(media, "file_size", 0)
    
    if file_size == 0:
        logger.warning("File size is 0, falling back to standard download")
        return await bot.download_media(message, file_name=output_path, progress=progress_cb, progress_args=progress_args)
        
    chunk_size = 1024 * 1024 # 1MB chunks natively yielded by Pyrogram
    total_chunks = math.ceil(file_size / chunk_size)
    
    # Pre-allocate the entire file on disk
    async with aiopen(output_path, "wb") as f:
        await f.seek(file_size - 1)
        await f.write(b"\0")
        
    chunk_queue = asyncio.Queue()
    for i in range(total_chunks):
        chunk_queue.put_nowait(i)
        
    downloaded_bytes = [0]
    start_time = time.time()
    
    # Select architecture based on size
    if file_size <= 2 * 1024**3:
        # Use Bot + Fast Client Pool (Up to 4 Physical TCP Connections)
        active_clients = [bot] + fast_clients
    else:
        # >2GB Requires Userbot
        if not userbot:
            raise Exception("File is >2GB but no Userbot String Session was provided!")
        # Simulate pool using the same Userbot client (Multiplexing over 1 TCP connection)
        active_clients = [userbot] * 4 
        
    write_lock = asyncio.Lock()
    
    async def download_worker(client):
        while not chunk_queue.empty():
            try:
                chunk_index = chunk_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
            offset_bytes = chunk_index * chunk_size
            success = False
            retries = 3
            
            while not success and retries > 0:
                try:
                    # Stream exactly 1 chunk (1MB) starting from chunk_index
                    async for chunk_data in client.stream_media(message, limit=1, offset=chunk_index):
                        
                        # Thread-safe byte-offset injection
                        if hasattr(os, "pwrite"):
                            # Linux/Oracle VPS: Atomic concurrent write (Zero bottlenecks)
                            fd = os.open(output_path, os.O_WRONLY)
                            try:
                                os.pwrite(fd, chunk_data, offset_bytes)
                            finally:
                                os.close(fd)
                        else:
                            # Windows Fallback: Locked seek-and-write
                            async with write_lock:
                                async with aiopen(output_path, "r+b") as f:
                                    await f.seek(offset_bytes)
                                    await f.write(chunk_data)
                                    
                        downloaded_bytes[0] += len(chunk_data)
                        
                        # Trigger UI Update
                        if progress_cb:
                            await progress_cb(downloaded_bytes[0], file_size, *progress_args)
                            
                        success = True
                        
                except Exception as e:
                    # e.g., FloodWaits or connection drops on this specific TCP connection
                    retries -= 1
                    await asyncio.sleep(2)
            
            if not success:
                # If totally failed, push the chunk back to queue for another worker to grab
                chunk_queue.put_nowait(chunk_index)

    # Spawn workers
    tasks = []
    for client in active_clients:
        tasks.append(asyncio.create_task(download_worker(client)))
        
    # Wait for all chunks to finish
    await asyncio.gather(*tasks)
    return output_path
