import re
import asyncio
import aiohttp
try:
    from aiohttp_socks import ProxyConnector
except ImportError:
    ProxyConnector = None
import logging
from config import Config

logger = logging.getLogger(__name__)

JUNK_TOKENS = {
    "1080p", "720p", "480p", "2160p", "360p", "240p", "4k", "8k",
    "x264", "x265", "hevc", "h264", "h265", "avc",
    "webrip", "web-dl", "webdl", "bluray", "brrip", "bdrip", "hdrip", "dvdrip", "cam", "hdcam", "ts", "hdts", "tc",
    "aac", "eac3", "ac3", "dd5", "ddp5", "dts", "flac", "mp3", "truehd",
    "esub", "esubs", "msub", "msubs", "hc", "sub", "subs", "subbed", "dub", "dubbed",
    "dual", "audio", "multi",
    "hindi", "tamil", "telugu", "malayalam", "kannada", "english", "eng", "hin", "tam", "tel", "mal", "kan",
    "hq", "proper", "repack", "remux", "internal", "uncut", "extended", "director",
    "10bit", "8bit", "hdr", "sdr", "hdr10", "dolby", "vision", "atmos"
}

async def search_tmdb(query: str, session: aiohttp.ClientSession) -> dict:
    if not Config.TMDB_API_KEY or not query.strip():
        return None
        
    url = f"https://api.themoviedb.org/3/search/multi?api_key={Config.TMDB_API_KEY}&query={query}&page=1"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("results"):
                    best_match = data["results"][0]
                    
                    # Extract title
                    title = best_match.get("title") or best_match.get("name")
                    
                    # Extract year
                    date_str = best_match.get("release_date") or best_match.get("first_air_date") or ""
                    year = date_str[:4] if date_str else ""
                    
                    # Calculate a confidence score
                    # Heuristic: Exact string match is highest confidence
                    popularity = best_match.get("popularity", 0)
                    query_lower = query.lower()
                    title_lower = title.lower() if title else ""
                    
                    confidence = 50 # Base
                    if query_lower == title_lower:
                        confidence += 40
                    elif title_lower in query_lower or query_lower in title_lower:
                        confidence += 20
                        
                    # Boost by popularity (max +10)
                    confidence += min(popularity / 10, 10)
                    
                    return {
                        "query": query,
                        "title": title,
                        "year": year,
                        "confidence": confidence,
                        "popularity": popularity,
                        "media_type": best_match.get("media_type")
                    }
    except Exception as e:
        logger.error(f"TMDB Search failed for {query}: {e}")
    return None

def generate_windows(tokens: list) -> list:
    """Generate all contiguous sub-phrases of length 1 to N"""
    windows = []
    n = len(tokens)
    for length in range(n, 0, -1):
        for i in range(n - length + 1):
            windows.append(" ".join(tokens[i:i+length]))
    return windows

async def extract_title_from_filename(filename: str) -> dict:
    """
    Nio's TMDB Sliding Window Extraction Pipeline
    """
    if not filename: return {"title": "Unknown", "year": ""}
    
    # Remove file extension
    base_name = filename.rsplit('.', 1)[0]
    
    # 1. Normalize separators
    normalized = re.sub(r'[_\-\[\]\(\)#\.]', ' ', base_name)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # 2. Year Anchoring & Prefix Dropping
    tokens = normalized.split()
    clean_tokens = []
    extracted_year = ""
    
    for i, token in enumerate(tokens):
        # Stop at the first valid Year (19XX or 20XX)
        if re.match(r'^(19\d{2}|20\d{2})$', token):
            extracted_year = token
            break
            
        # Strip @ prefix token if it's the very first token
        if i == 0 and token.startswith('@'):
            token = token[1:] # Just remove the @, we let sliding window handle the rest
            
        if token.lower() not in JUNK_TOKENS:
            clean_tokens.append(token)
            
    if not clean_tokens:
        return {"title": base_name, "year": extracted_year}
        
    # Generate windows
    windows = generate_windows(clean_tokens)
    
    # If no TMDB Key, just return the full cleaned left side
    if not Config.TMDB_API_KEY:
        title = " ".join(clean_tokens)
        return {"title": title, "year": extracted_year}
        
    # 3. Asynchronous TMDB Brute Force
    best_result = None
    
    # We only want to search reasonable windows (e.g. up to 10 candidates to avoid spamming)
    # Windows are ordered by length descending. We take the top 10.
    search_windows = windows[:10]
    
    connector = None
    if getattr(Config, 'PROXY_IP', None) and getattr(Config, 'PROXY_PORT', None) and ProxyConnector:
        auth = f"{Config.PROXY_USERNAME}:{Config.PROXY_PASSWORD}@" if getattr(Config, 'PROXY_USERNAME', None) else ""
        proxy_url = f"socks5://{auth}{Config.PROXY_IP}:{Config.PROXY_PORT}"
        connector = ProxyConnector.from_url(proxy_url)
        
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [search_tmdb(window, session) for window in search_windows]
        results = await asyncio.gather(*tasks)
        
        valid_results = [r for r in results if r is not None]
        
        if valid_results:
            # Sort by confidence then popularity
            valid_results.sort(key=lambda x: (x["confidence"], x["popularity"]), reverse=True)
            best_result = valid_results[0]
            
    if best_result and best_result["confidence"] >= 60: # Threshold for accepting a match
        # If TMDB found a year and we didn't have one, use TMDB's year!
        final_year = extracted_year if extracted_year else best_result["year"]
        return {
            "title": best_result["title"],
            "year": final_year
        }
        
    # Fallback if TMDB fails or confidence is too low
    return {"title": " ".join(clean_tokens), "year": extracted_year}
