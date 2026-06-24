def get_readable_size(size_bytes: int) -> str:
    if not size_bytes:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def get_readable_time(seconds: int) -> str:
    if not seconds:
        return "00:00:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

import re

def generate_caption(file_name: str, info: dict, original_size: int) -> str:
    """Generates the formatted HTML/Markdown caption based on metadata."""
    
    size_str = get_readable_size(original_size)
    duration_str = get_readable_time(info.get("duration", 0))
    width = info.get("width", 0)
    height = info.get("height", 0)
    
    # Determine basic resolution string
    res_str = info.get("resolution", "Unknown")
    
    # Video string
    vid_tags = [res_str]
    if info.get("video_codec") and info.get("video_codec") != "Unknown": vid_tags.append(info.get("video_codec"))
    if info.get("video_profile"): vid_tags.append(info.get("video_profile"))
    video_str = " | ".join(vid_tags)
    
    lang_str = ", ".join(info.get("audio_languages", [])) if info.get("audio_languages") else "Unknown"
    codec_str = ", ".join(info.get("audio_codecs", [])) if info.get("audio_codecs") else "Unknown"
    
    # Subs string
    subs_str = ""
    subs_count = info.get("subs_count", 0)
    subs_langs = info.get("subs_languages", [])
    
    if subs_count > 0:
        if subs_langs:
            lang_list = ", ".join(subs_langs)
            if subs_count > 1:
                subs_str = f"💬 **Subs:** `M-Sub ({lang_list})`\n"
            else:
                subs_str = f"💬 **Subs:** `E-Sub ({lang_list})`\n"
        else:
            if subs_count > 1:
                subs_str = f"💬 **Subs:** `M-Sub`\n"
            else:
                subs_str = f"💬 **Subs:** `E-Sub`\n"
        
    # Series vs Movie
    season = None
    episode = None
    
    # Try multiple regex patterns for robust matching
    patterns = [
        r'S(\d+).*?E(\d+)',            # S01E04, S01 E04
        r'(\d+)x(\d+)',                # 1x04, 01x04
        r'Season\s*(\d+)\s*Episode\s*(\d+)' # Season 1 Episode 4
    ]
    
    for pattern in patterns:
        match = re.search(pattern, file_name, re.IGNORECASE)
        if match:
            season = match.group(1).zfill(2)
            episode = match.group(2).zfill(2)
            break
            
    clean_name = file_name.replace(".", " ").replace("_", " ").rsplit(" ", 1)[0]
    
    if season and episode:
        caption = (
            f"**{clean_name}**\n\n"
            f"📺 **Season:** `{season}`\n"
            f"🍿 **Episode:** `{episode}`\n"
            f"⚙️ **Video:** `{video_str}`\n"
            f"🔊 **Audio Codec:** `{codec_str}`\n"
            f"🗣 **Language:** `{lang_str}`\n"
            f"{subs_str}"
            f"⏱ **Duration:** `{duration_str}`\n"
            f"💾 **Size:** `{size_str}`"
        )
    else:
        caption = (
            f"**{clean_name}**\n\n"
            f"⚙️ **Video:** `{video_str}`\n"
            f"🔊 **Audio Codec:** `{codec_str}`\n"
            f"🗣 **Language:** `{lang_str}`\n"
            f"{subs_str}"
            f"⏱ **Duration:** `{duration_str}`\n"
            f"💾 **Size:** `{size_str}`"
        )
        
    return caption
