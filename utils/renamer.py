import re

def generate_new_name(original_name: str) -> str:
    if not original_name:
        return "Unknown_File"

    name = original_name

    # 1. Strip common website/channel tags like [Scraped], (t.me/Channel)
    # Removes text inside brackets/parentheses if it contains URLs or @
    name = re.sub(r'\[.*?\]|\(.*?\)', lambda m: '' if any(x in m.group(0).lower() for x in ['.com', '.me', '.net', '.org', 'www', 'http', '@', 't.me']) else m.group(0), name)
    
    # Remove Telegram links securely without eating the whole string
    name = re.sub(r't\.me/[a-zA-Z0-9_]+', '', name, flags=re.IGNORECASE)
    name = name.replace('@', '')
    parts = name.rsplit('.', 1)
    if len(parts) > 1:
        base_name, ext = parts[0], parts[1]
    else:
        base_name, ext = name, ""

    # 3. Clean base name
    # Replace common separators with spaces to normalize
    base_name = re.sub(r'[_\-]', ' ', base_name)
    
    # Remove multiple spaces
    base_name = re.sub(r'\s+', ' ', base_name).strip()

    # 4. Convert spaces to dots
    base_name = base_name.replace(' ', '.')

    # Reconstruct name
    if ext:
        return f"{base_name}.{ext}"
    return base_name
