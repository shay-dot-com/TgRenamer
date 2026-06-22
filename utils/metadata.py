import asyncio
import json
import logging

logger = logging.getLogger(__name__)

async def get_video_info(file_path: str) -> dict:
    """Uses ffprobe to extract metadata from a video file."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=width,height,codec_name,bit_rate",
        "-of", "json",
        file_path
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffprobe failed: {stderr.decode()}")
            return {}
            
        data = json.loads(stdout.decode())
        
        info = {
            "duration": 0,
            "width": 0,
            "height": 0
        }
        
        # Parse format
        if "format" in data:
            info["duration"] = int(float(data["format"].get("duration", 0)))
            
        # Parse streams
        if "streams" in data:
            for stream in data["streams"]:
                if "width" in stream and "height" in stream:
                    info["width"] = stream["width"]
                    info["height"] = stream["height"]
                    break
                    
        return info
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}
