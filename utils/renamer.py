import re
from utils.title_extractor import extract_title_from_filename

async def generate_new_name(original_name: str, info: dict = None) -> str:
    if not original_name:
        return "Unknown_File"

    name = original_name

    # 1. Strip leading brackets like [IMDB] or (TelegramChannel) from the VERY start of the filename
    name = re.sub(r'^\[.*?\] *|^\(.*?\) *', '', name)

    # 2. Remove Telegram links securely
    name = re.sub(r't\.me/[a-zA-Z0-9_]+', '', name, flags=re.IGNORECASE)
    
    # Extract extension
    parts = name.rsplit('.', 1)
    if len(parts) > 1:
        base_name, ext = parts[0], parts[1]
    else:
        base_name, ext = name, ""
        
    # Semantic TMDB Title Extraction
    title_data = await extract_title_from_filename(base_name)
    clean_title = title_data.get("title", base_name)
    clean_year = title_data.get("year", "")
    clean_episode = title_data.get("episode", "")
    
    # Title Case for aesthetics (unless TMDB returned official casing)
    # Actually TMDB returns official casing! So we don't need .title() if TMDB succeeds!
    # But just in case TMDB failed and it's a fallback:
    if clean_title == base_name or clean_title == clean_title.lower():
        clean_title = clean_title.title()
        
    # Reconstruct the base name with dots instead of spaces
    base_name = clean_title.replace(' ', '.')
    
    # Append the Year if it exists
    if clean_year:
        base_name = f"{base_name}.{clean_year}"
        
    # Append the Episode Tag if it exists
    if clean_episode:
        base_name = f"{base_name}.{clean_episode}"
        
    # Note: We removed the hardcoded acronyms dictionary because TMDB validation 
    # handles acronyms perfectly (e.g., returning "Spider-Man: No Way Home").
    # If TMDB fails, it just uses standard Title Case.
    
    base_name = base_name.strip('.') # Clean trailing dots
    base_name = base_name.replace('@', '') # Clean any remaining @ symbols
    
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
            v_codec = info["video_codec"]
            if v_codec == "X265": v_codec = "x265" 
            elif v_codec == "X264": v_codec = "x264"
            tags.append(v_codec)
            
        # Add bit depth (including 8Bit now)
        if info.get("video_profile"):
            tags.append(info["video_profile"])
            
        # Add Audio Codecs & Channels (e.g., AAC.2CH)
        if info.get("audio_codecs"):
            for a_codec in info["audio_codecs"]:
                # Replace space with dot to maintain standard formatting (AAC 2CH -> AAC.2CH)
                tags.append(a_codec.replace(" ", "."))
            
        if tags:
            tag_str = ".".join(tags)
            base_name = f"{base_name}.{tag_str}"

    if ext:
        return f"{base_name}.{ext}"
    return base_name
