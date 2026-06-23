import re

def generate_new_name(original_name: str, info: dict = None) -> str:
    if not original_name:
        return "Unknown_File"

    name = original_name

    # 1. Strip leading brackets like [IMDB] or (TelegramChannel) from the VERY start of the filename
    name = re.sub(r'^\[.*?\] *|^\(.*?\) *', '', name)

    # 2. Remove Telegram links securely
    name = re.sub(r't\.me/[a-zA-Z0-9_]+', '', name, flags=re.IGNORECASE)
    name = name.replace('@', '')
    
    # Extract extension
    parts = name.rsplit('.', 1)
    if len(parts) > 1:
        base_name, ext = parts[0], parts[1]
    else:
        base_name, ext = name, ""
        
    # 3. Strip known garbage quality/codec tags so we don't duplicate them
    garbage_tags = r'\b(2160p|1440p|1080p|720p|480p|360p|240p|x264|x265|hevc|h264|8bit|10bit|hdr|web-dl|webdl|bluray|brrip|hdrip|dvdrip|hq)\b'
    base_name = re.sub(garbage_tags, '', base_name, flags=re.IGNORECASE)

    # 4. Clean separators
    base_name = re.sub(r'[_\-\[\]\(\)#]', ' ', base_name)
    base_name = re.sub(r'\s+', ' ', base_name).strip()
    
    # Title Case for aesthetics
    base_name = base_name.title()
    
    # Restore standard acronym casing
    acronyms = {
        "Webrip": "WEBRip", "Web dl": "WEB-DL", "Web Dl": "WEB-DL",
        "Web": "WEB", "Hdcam": "HDCAM", "Psa": "PSA", "Yts": "YTS",
        "Yify": "YIFY", "Rarbg": "RARBG", "Esub": "ESub", "Msub": "MSub",
        "Hc": "HC", "Aac": "AAC", "Eac3": "EAC3", "Ch": "CH"
    }
    for old, new in acronyms.items():
        base_name = re.sub(rf'\b{old}\b', new, base_name)
    
    base_name = base_name.replace(' ', '.')
    
    # Fix double dots that occur when middle tags are removed
    base_name = re.sub(r'\.+', '.', base_name)
    
    base_name = base_name.strip('.') # Clean trailing dots
    
    # 5. Inject accurate dynamic metadata
    if info:
        tags = []
        if info.get("resolution") and info["resolution"] != "Unknown":
            tags.append(info["resolution"])
            
        # Add primary languages
        if info.get("audio_languages"):
            lang_map = {
                "hin": "Hindi", "eng": "English", "tam": "Tamil", "tel": "Telugu",
                "mal": "Malayalam", "kan": "Kannada", "spa": "Spanish", "fra": "French",
                "jpn": "Japanese", "kor": "Korean", "chi": "Chinese", "en": "English",
                "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "ml": "Malayalam"
            }
            langs = [lang_map.get(l.lower(), l.title() if l.islower() else l) for l in info["audio_languages"]]
            tags.append(".".join(langs))
            
        if info.get("video_codec") and info["video_codec"] != "Unknown":
            tags.append(info["video_codec"])
            
        if info.get("video_profile") and info["video_profile"] != "8Bit":
            tags.append(info["video_profile"])
            
        if tags:
            tag_str = ".".join(tags)
            base_name = f"{base_name}.{tag_str}"

    if ext:
        return f"{base_name}.{ext}"
    return base_name
