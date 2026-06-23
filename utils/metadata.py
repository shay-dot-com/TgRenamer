import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

def extract_languages_from_filename(filename: str) -> list:
    lang_patterns = {
        "tamil": "Tamil", "tam": "Tamil",
        "telugu": "Telugu", "tel": "Telugu",
        "hindi": "Hindi", "hin": "Hindi",
        "malayalam": "Malayalam", "mal": "Malayalam",
        "kannada": "Kannada", "kan": "Kannada",
        "english": "English", "eng": "English",
        "spanish": "Spanish", "french": "French",
        "japanese": "Japanese", "korean": "Korean",
        "chinese": "Chinese"
    }
    
    scores = {v: 0 for v in set(lang_patterns.values())}
    filename_lower = filename.lower()
    
    tokens = re.split(r'[^a-z0-9]', filename_lower)
    
    for i, token in enumerate(tokens):
        if token in lang_patterns:
            lang = lang_patterns[token]
            scores[lang] += 5 # Base score
            
            # Context checking
            next_token = tokens[i+1] if i+1 < len(tokens) else ""
            if "dub" in next_token or "audio" in next_token:
                scores[lang] += 10
            elif "sub" in next_token or "esub" in next_token or "msub" in next_token:
                scores[lang] -= 10
                
            prev_token = tokens[i-1] if i-1 >= 0 else ""
            if "dub" in prev_token or "audio" in prev_token:
                scores[lang] += 10
                
    return [lang for lang, score in scores.items() if score > 0]

def get_resolution_bucket(width: int, height: int) -> str:
    pixels = width * height
    # Thresholds tuned for cinematic (2.35:1) aspect ratios
    if pixels >= 3500000: return "4K"
    elif pixels >= 1400000: return "1080p" # Cinematic 1080p is ~1920x800 (1.53M)
    elif pixels >= 600000: return "720p"   # Cinematic 720p is ~1280x536 (686K)
    elif pixels >= 300000: return "480p"   # Cinematic 480p is ~854x360 (307K)
    elif pixels >= 150000: return "360p"   # Cinematic 360p is ~640x272 (174K) or 608x256 (155K)
    else: return "240p"

def extract_languages_from_caption(caption: str) -> list:
    if not caption: return []
    
    audio_line = ""
    for line in caption.split('\n'):
        line_lower = line.lower()
        if '🔊' in line_lower or '🗣' in line_lower or 'audio' in line_lower:
            audio_line = line
            break
            
    if audio_line:
        # High confidence because we specifically isolated the Audio line
        return extract_languages_from_filename(audio_line)
    
    # If no specific line, scan the whole caption but rely on scoring logic
    return extract_languages_from_filename(caption)

async def get_video_info(file_path: str, original_name: str = "", original_caption: str = "") -> dict:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=codec_type,codec_name,profile,width,height,pix_fmt,color_transfer,tags",
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
            "resolution": "",
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
                    pix_fmt = stream.get("pix_fmt", "")
                    color_transfer = stream.get("color_transfer", "")
                    
                    if "10" in profile.lower() or "10" in pix_fmt.lower() or "hdr" in profile.lower() or "smpte2084" in color_transfer.lower() or "arib-std-b67" in color_transfer.lower():
                        info["video_profile"] = "10Bit"
                    elif "8" in profile.lower() or "8" in pix_fmt.lower() or profile.lower() in ["main", "high"]:
                        info["video_profile"] = "8Bit"
                        
                elif c_type == "audio":
                    info["audio_count"] += 1
                    codec = stream.get("codec_name", "").upper()
                    if codec and codec not in info["audio_codecs"]:
                        info["audio_codecs"].append(codec)
                        
                    tags = stream.get("tags", {})
                    # Priority 1: ISO language tag
                    lang = tags.get("language", "und").lower()
                    if lang != "und" and lang not in info["audio_languages"]:
                        info["audio_languages"].append(lang)
                    else:
                        # Priority 1.5: Stream Title check
                        title = tags.get("title", "").lower()
                        extracted = extract_languages_from_filename(title)
                        for l in extracted:
                            if l not in info["audio_languages"]:
                                info["audio_languages"].append(l)
                        
                elif c_type == "subtitle":
                    info["subs_count"] += 1
                    
            # Priority 2: Original Caption Language Parsing
            if info["audio_count"] >= 1 and not info["audio_languages"] and original_caption:
                extracted = extract_languages_from_caption(original_caption)
                if extracted:
                    info["audio_languages"] = extracted
                    
            # Priority 3: Filename Language Parsing
            if info["audio_count"] >= 1 and not info["audio_languages"] and original_name:
                extracted = extract_languages_from_filename(original_name)
                info["audio_languages"] = extracted
                
            # Resolution Detection
            res_match = re.search(r'(2160p|1440p|1080p|720p|480p|360p|240p)', original_name.lower())
            if res_match:
                info["resolution"] = res_match.group(1)
            elif info["width"] > 0:
                info["resolution"] = get_resolution_bucket(info["width"], info["height"])
            else:
                info["resolution"] = "Unknown"
                    
        return info
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}
