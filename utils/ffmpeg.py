import asyncio
import logging

logger = logging.getLogger(__name__)

async def process_video(input_path: str, output_path: str, new_title: str) -> bool:
    """
    Uses ffmpeg to process the video.
    For this phase, we copy streams (-c copy) and inject metadata.
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-map", "0",
        "-c", "copy",
        "-metadata", f"title={new_title}",
        output_path,
        "-y"
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg failed: {stderr.decode()}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"ffmpeg exception: {e}")
        return False

async def generate_thumbnail(video_path: str, output_path: str, duration: int) -> bool:
    """Extracts a thumbnail from the video."""
    # Extract at EXACTLY the 10% mark dynamically
    target_time = max(1, duration // 10)
    target_time_str = str(target_time)

    cmd = [
        "ffmpeg",
        "-ss", target_time_str,
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path,
        "-y"
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        return process.returncode == 0
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return False
