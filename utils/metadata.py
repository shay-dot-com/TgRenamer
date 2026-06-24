import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# INSPIRATION CREDIT: PIROXTG / MediaInfo-Bot
# The _LANGUAGE_MAP and advanced FFprobe metadata extraction patterns (HDR, 
# 10-bit, Dolby Vision) are heavily inspired by the robust parsing engine 
# from https://github.com/PIROXTG/MediaInfo-Bot. 
# We have adapted them here to perfectly fit our renamer architecture.
# -------------------------------------------------------------------------

_LANGUAGE_MAP: dict[str, str] = {
    'en': 'English',  'eng': 'English',
    'hi': 'Hindi',    'hin': 'Hindi',
    'ta': 'Tamil',    'tam': 'Tamil',
    'te': 'Telugu',   'tel': 'Telugu',
    'ml': 'Malayalam','mal': 'Malayalam',
    'kn': 'Kannada',  'kan': 'Kannada',
    'bn': 'Bengali',  'ben': 'Bengali',
    'mr': 'Marathi',  'mar': 'Marathi',
    'gu': 'Gujarati', 'guj': 'Gujarati',
    'pa': 'Punjabi',  'pun': 'Punjabi',
    'bho':'Bhojpuri',
    'zh': 'Chinese',  'chi': 'Chinese',  'cmn': 'Chinese',
    'ko': 'Korean',   'kor': 'Korean',
    'pt': 'Portuguese','por': 'Portuguese',
    'th': 'Thai',     'tha': 'Thai',
    'tl': 'Tagalog',  'tgl': 'Tagalog',  'fil': 'Tagalog',
    'ja': 'Japanese', 'jpn': 'Japanese',
    'es': 'Spanish',  'spa': 'Spanish',
    'sv': 'Swedish',  'swe': 'Swedish',
    'fr': 'French',   'fra': 'French',   'fre': 'French',
    'de': 'German',   'deu': 'German',   'ger': 'German',
    'it': 'Italian',  'ita': 'Italian',
    'ru': 'Russian',  'rus': 'Russian',
    'ar': 'Arabic',   'ara': 'Arabic',
    'tr': 'Turkish',  'tur': 'Turkish',
    'nl': 'Dutch',    'nld': 'Dutch',    'dut': 'Dutch',
    'pl': 'Polish',   'pol': 'Polish',
    'vi': 'Vietnamese','vie': 'Vietnamese',
    'id': 'Indonesian','ind': 'Indonesian',
    'ms': 'Malay',    'msa': 'Malay',    'may': 'Malay',
    'fa': 'Persian',  'fas': 'Persian',  'per': 'Persian',
    'ur': 'Urdu',     'urd': 'Urdu',
    'he': 'Hebrew',   'heb': 'Hebrew',
    'el': 'Greek',    'ell': 'Greek',    'gre': 'Greek',
    'hu': 'Hungarian','hun': 'Hungarian',
    'cs': 'Czech',    'ces': 'Czech',    'cze': 'Czech',
    'ro': 'Romanian', 'ron': 'Romanian', 'rum': 'Romanian',
    'da': 'Danish',   'dan': 'Danish',
    'fi': 'Finnish',  'fin': 'Finnish',
    'no': 'Norwegian','nor': 'Norwegian',
    'uk': 'Ukrainian','ukr': 'Ukrainian',
    'ca': 'Catalan',  'cat': 'Catalan',
    'hr': 'Croatian', 'hrv': 'Croatian',
    'sk': 'Slovak',   'slk': 'Slovak',   'slo': 'Slovak',
    'sr': 'Serbian',  'srp': 'Serbian',
    'bg': 'Bulgarian','bul': 'Bulgarian',
    'unknown': 'Unknown',
}

def get_full_language_name(code: str) -> str:
    if not code:
        return 'Unknown'
    cleaned = code.split('(')[0].strip()
    return _LANGUAGE_MAP.get(cleaned.lower(), cleaned.title() if cleaned.islower() else cleaned)

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
        "-show_entries", "stream=codec_type,codec_name,profile,width,height,pix_fmt,color_transfer,color_space,bits_per_raw_sample,bits_per_coded_sample,tags,channels",
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
            "subs_count": 0,
            "subs_languages": []
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
                    codec_raw = stream.get("codec_name", "Unknown").lower()
                    
                    if codec_raw in ["hevc", "h265"]: codec = "HEVC"
                    elif codec_raw in ["h264", "avc"]: codec = "x264"
                    elif codec_raw == "av1": codec = "AV1"
                    elif codec_raw == "vp9": codec = "VP9"
                    elif codec_raw in ["mpeg4", "xvid"]: codec = "MPEG4"
                    else: codec = codec_raw.upper() if codec_raw != "unknown" else codec_raw
                    
                    info["video_codec"] = codec
                    
                    # Profile, Bit Depth & HDR parsing (Inspired by MediaInfo-Bot)
                    profile = stream.get("profile", "")
                    pix_fmt = stream.get("pix_fmt", "")
                    color_transfer = stream.get("color_transfer", "").lower()
                    color_space = stream.get("color_space", "").lower()
                    
                    # 1. Check Bit Depth
                    bps = str(stream.get("bits_per_raw_sample") or stream.get("bits_per_coded_sample") or "")
                    bit_depth_str = ""
                    if bps.isdigit() and int(bps) >= 10:
                        bit_depth_str = f"{bps}Bit"
                    elif "10" in profile.lower() or "10" in pix_fmt.lower():
                        bit_depth_str = "10Bit"
                    elif bps.isdigit() and int(bps) == 8:
                        bit_depth_str = "8Bit"
                    elif "8" in profile.lower() or "8" in pix_fmt.lower() or profile.lower() in ["main", "high"]:
                        bit_depth_str = "8Bit"
                        
                    # 2. Check HDR / Dolby Vision
                    hdr_str = ""
                    tags = stream.get("tags", {})
                    # Dolby vision can sometimes be in tags or profile
                    if "dolby" in str(tags).lower() or "dv" in profile.lower():
                        hdr_str = "Dolby Vision"
                    elif any(x in color_transfer for x in ("smpte2084", "arib-std-b67", "smpte428")):
                        hdr_str = "HDR"
                    elif "bt2020" in color_space:
                        hdr_str = "HDR"
                    elif "hdr" in profile.lower():
                        hdr_str = "HDR"
                        
                    # Combine profile string
                    prof_parts = [p for p in (bit_depth_str, hdr_str) if p]
                    if prof_parts:
                        info["video_profile"] = " ".join(prof_parts)
                        
                elif c_type == "audio":
                    info["audio_count"] += 1
                    codec = stream.get("codec_name", "").upper()
                    if codec == "AAC": codec = "AAC"
                    
                    channels = stream.get("channels")
                    ch_str = ""
                    if channels == 2: ch_str = " 2CH"
                    elif channels == 6: ch_str = " 6CH" # Usually 5.1 but 6 channels
                    elif channels == 8: ch_str = " 8CH" # Usually 7.1
                    elif channels: ch_str = f" {channels}CH"
                    
                    full_codec = f"{codec}{ch_str}".strip()
                    if full_codec and full_codec not in info["audio_codecs"]:
                        info["audio_codecs"].append(full_codec)
                        
                    tags = stream.get("tags", {})
                    # Priority 1: ISO language tag mapped to full name
                    lang_raw = tags.get("language", "und").lower()
                    if lang_raw != "und":
                        mapped_lang = get_full_language_name(lang_raw)
                        if mapped_lang not in info["audio_languages"] and mapped_lang != "Unknown":
                            info["audio_languages"].append(mapped_lang)
                    else:
                        # Priority 1.5: Stream Title check
                        title = tags.get("title", "").lower()
                        extracted = extract_languages_from_filename(title)
                        for l in extracted:
                            # Map extracted to ensure perfect casing
                            mapped_l = get_full_language_name(l)
                            if mapped_l not in info["audio_languages"] and mapped_l != "Unknown":
                                info["audio_languages"].append(mapped_l)
                        
                elif c_type == "subtitle":
                    info["subs_count"] += 1
                    tags = stream.get("tags", {})
                    lang_raw = tags.get("language", "und").lower()
                    if lang_raw != "und":
                        mapped_lang = get_full_language_name(lang_raw)
                        if mapped_lang not in info["subs_languages"] and mapped_lang != "Unknown":
                            info["subs_languages"].append(mapped_lang)
                    
            # Priority 2: Original Caption Language Parsing
            if info["audio_count"] >= 1 and not info["audio_languages"] and original_caption:
                extracted = extract_languages_from_caption(original_caption)
                if extracted:
                    info["audio_languages"] = [get_full_language_name(l) for l in extracted]
                    
            # Priority 3: Filename Language Parsing
            if info["audio_count"] >= 1 and not info["audio_languages"] and original_name:
                extracted = extract_languages_from_filename(original_name)
                info["audio_languages"] = [get_full_language_name(l) for l in extracted]
                
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
