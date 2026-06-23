import asyncio
import json
import logging

logger = logging.getLogger(__name__)

async def get_video_info(file_path: str) -> dict:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=codec_type,codec_name,profile,width,height,tags",
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
            "height": 0,
            "video_codec": "Unknown",
            "video_profile": "",
            "audio_codecs": [],
            "audio_count": 0,
            "audio_languages": [],
            "subs_count": 0
        }
        
        # Parse format
        if "format" in data:
            info["duration"] = int(float(data["format"].get("duration", 0)))
            
        # Parse streams
        if "streams" in data:
            for stream in data["streams"]:
                c_type = stream.get("codec_type")
                
                if c_type == "video" and info["width"] == 0:
                    info["width"] = stream.get("width", 0)
                    info["height"] = stream.get("height", 0)
                    codec = stream.get("codec_name", "Unknown")
                    if codec == "hevc": codec = "x265"
                    elif codec == "h264": codec = "x264"
                    info["video_codec"] = codec.upper() if codec != "Unknown" else codec
                    
                    profile = stream.get("profile", "")
                    if "10" in profile.lower():
                        info["video_profile"] = "10Bit"
                    elif "8" in profile.lower() or profile.lower() in ["main", "high"]:
                        info["video_profile"] = "8Bit"
                        
                elif c_type == "audio":
                    info["audio_count"] += 1
                    codec = stream.get("codec_name", "").upper()
                    if codec and codec not in info["audio_codecs"]:
                        info["audio_codecs"].append(codec)
                        
                    tags = stream.get("tags", {})
                    lang = tags.get("language", "und")
                    if lang != "und" and lang not in info["audio_languages"]:
                        info["audio_languages"].append(lang)
                        
                elif c_type == "subtitle":
                    info["subs_count"] += 1
                    
        return info
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}
