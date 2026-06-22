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
    
    caption = (
        f"**{file_name}**\n\n"
        f"⚙️ **Video:** `{res_str}`\n"
        f"⏱ **Duration:** `{duration_str}`\n"
        f"💾 **Size:** `{size_str}`"
    )
    
    return caption
