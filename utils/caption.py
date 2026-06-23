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
    res_str = "Unknown"
    if height >= 2160: res_str = "4K"
    elif height >= 1080: res_str = "1080p"
    elif height >= 720: res_str = "720p"
    elif height >= 480: res_str = "480p"
    elif height > 0: res_str = f"{width}x{height}"
    
    # Video string
    vid_tags = [res_str]
    if info.get("video_codec") and info.get("video_codec") != "Unknown": vid_tags.append(info.get("video_codec"))
    if info.get("video_profile"): vid_tags.append(info.get("video_profile"))
    video_str = " | ".join(vid_tags)
    
    # Audio string
    audio_tags = []
    if info.get("audio_count", 0) > 1:
        langs = []
        for l in info.get("audio_languages", []):
            if l == "hin": langs.append("Hindi")
            elif l == "eng": langs.append("English")
            elif l == "tam": langs.append("Tamil")
            elif l == "tel": langs.append("Telugu")
            elif l == "mal": langs.append("Malayalam")
            
        if langs:
            audio_tags.append(f"Dual Audio ({', '.join(langs)})" if info["audio_count"] == 2 else f"Multi Audio ({', '.join(langs)})")
        else:
            audio_tags.append("Dual Audio" if info["audio_count"] == 2 else "Multi Audio")
    elif info.get("audio_count", 0) == 1:
        if "eng" in info.get("audio_languages", []): audio_tags.append("English")
        elif "hin" in info.get("audio_languages", []): audio_tags.append("Hindi")
        
    if info.get("audio_codecs"):
        audio_tags.append(", ".join(info.get("audio_codecs")))
        
    audio_str = " | ".join(audio_tags) if audio_tags else "Unknown"
    
    # Subs string
    subs_str = ""
    if info.get("subs_count", 0) > 1:
        subs_str = f"💬 **Subs:** `M-Sub`\n"
    elif info.get("subs_count", 0) == 1:
        subs_str = f"💬 **Subs:** `E-Sub`\n"
        
    # Series vs Movie
    series_match = re.search(r'S(\d+)E(\d+)', file_name, re.IGNORECASE)
    clean_name = file_name.replace(".", " ").replace("_", " ").rsplit(" ", 1)[0]
    
    if series_match:
        season = series_match.group(1)
        episode = series_match.group(2)
        caption = (
            f"**{clean_name}**\n\n"
            f"📺 **Season:** `{season}`\n"
            f"🍿 **Episode:** `{episode}`\n"
            f"⚙️ **Video:** `{video_str}`\n"
            f"🔊 **Audio:** `{audio_str}`\n"
            f"{subs_str}"
            f"⏱ **Duration:** `{duration_str}`\n"
            f"💾 **Size:** `{size_str}`"
        )
    else:
        caption = (
            f"**{clean_name}**\n\n"
            f"⚙️ **Video:** `{video_str}`\n"
            f"🔊 **Audio:** `{audio_str}`\n"
            f"{subs_str}"
            f"⏱ **Duration:** `{duration_str}`\n"
            f"💾 **Size:** `{size_str}`"
        )
        
    return caption
