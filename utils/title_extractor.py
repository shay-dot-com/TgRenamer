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

async def search_tmdb(query: str, session: aiohttp.ClientSession, expected_year: str = "") -> dict:
    if not Config.TMDB_API_KEY or not query.strip():
        return None
        
    url = f"https://api.themoviedb.org/3/search/multi?api_key={Config.TMDB_API_KEY}&query={query}&page=1"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("results"):
                    best_match = data["results"][0]
                    
                for r in data.get("results", []):
                    # Ignore people (actors/directors)
                    if r.get("media_type") not in ["movie", "tv"]:
                        continue
                        
                    title = r.get("title") or r.get("name")
                    year_str = r.get("release_date") or r.get("first_air_date")
                    year = year_str.split("-")[0] if year_str else ""
                    popularity = r.get("popularity", 0)
                    
                    if title:
                        query_lower = query.lower()
                        title_lower = title.lower()
                        confidence = 50 # Base
                        
                        if expected_year and year and str(year) == expected_year:
                            confidence += 30 # Massive boost if the uploader's year matches exactly!
                        if query_lower == title_lower:
                            confidence += 40
                        elif title_lower in query_lower or query_lower in title_lower:
                            confidence += 20
                        else:
                            # TMDB Hallucination Penalty: if TMDB returns a totally different string
                            confidence -= 40
                            
                        # Heavily penalize short 1-word queries that are only partial matches
                        if len(query.split()) == 1 and len(query) <= 4:
                            if query_lower != title_lower:
                                confidence -= 40
                                
                        # Boost by popularity (max +10)
                        confidence += min(popularity / 10, 10)
                        
                        return {
                            "query": query,
                            "title": title,
                            "year": year,
                            "confidence": confidence,
                            "popularity": popularity,
                            "media_type": r.get("media_type")
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

def extract_episode_tag(text: str) -> tuple[str, str]:
    """Extracts and standardizes Season/Episode tags, removing them from text"""
    # Matches: S01E01, S1 E1, s01e01, season 1 episode 1
    s_e_match = re.search(r'(?i)\bs(?:eason)?\s*(\d{1,2})\s*e(?:p(?:isode)?)?\s*(\d{1,4})\b', text)
    if s_e_match:
        s, e = s_e_match.groups()
        tag = f"S{int(s):02d}E{int(e):02d}"
        clean_text = text[:s_e_match.start()] + " " + text[s_e_match.end():]
        return tag, clean_text
        
    # Matches: Ep01, EP 1, Episode 1, E01
    e_match = re.search(r'(?i)\b(?:e(?:p(?:isode)?)?)\s*(\d{1,4})\b', text)
    if e_match:
        e = e_match.groups()[0]
        tag = f"E{int(e):02d}"
        clean_text = text[:e_match.start()] + " " + text[e_match.end():]
        return tag, clean_text
        
    return "", text

def remove_channel_tags(text: str) -> str:
    """Aggressively strips @Channel tags before tokenization"""
    # 1. Remove "Channel @XYZ "
    text = re.sub(r'(?i)^channel\s*@[a-z0-9_]+[\s\._\-]*', '', text)
    
    # 2. Remove "@XYZ " or "@XYZ_" or "@XYZ."
    text = re.sub(r'(?i)^@[a-z0-9_]+[\s\._\-]*', '', text)
    
    return text

async def extract_title_from_filename(filename: str) -> dict:
    """
    Nio's TMDB Sliding Window Extraction Pipeline
    """
    if not filename: return {"title": "Unknown", "year": ""}
    
    # Remove file extension
    base_name = filename.rsplit('.', 1)[0]
    
    # 0. Pre-Extraction Channel Tag Erasure
    base_name = remove_channel_tags(base_name)
    
    # 1. Normalize separators
    normalized = re.sub(r'[_\-\[\]\(\)#\.]', ' ', base_name)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # 2. Episode Pre-Extraction Layer
    extracted_episode, normalized = extract_episode_tag(normalized)
    
    # 2. Year Anchoring & Prefix Dropping
    tokens = normalized.split()
    clean_tokens = []
    extracted_year = ""
    
    for i, token in enumerate(tokens):
        # Stop at the first valid Year (13XX, 14XX for Persian, 19XX, 20XX for Gregorian)
        if re.match(r'^(13\d{2}|14\d{2}|19\d{2}|20\d{2})$', token):
            extracted_year = token
            break
            
        # Strip @ prefix token if it's the very first token (Fallback if remove_channel_tags missed it)
        if i == 0 and token.startswith('@'):
            token = token[1:] # Just remove the @, we let sliding window handle the rest
            
        if token.lower() not in JUNK_TOKENS:
            clean_tokens.append(token)
            
    if not clean_tokens:
        return {"title": base_name, "year": extracted_year, "episode": extracted_episode}
        
    # Generate windows
    windows = generate_windows(clean_tokens)
    
    # If no TMDB Key, just return the full cleaned left side
    if not Config.TMDB_API_KEY:
        title = " ".join(clean_tokens)
        return {"title": title, "year": extracted_year, "episode": extracted_episode}
        
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
        tasks = [search_tmdb(window, session, extracted_year) for window in search_windows]
        results = await asyncio.gather(*tasks)
        
        valid_results = [r for r in results if r is not None]
        
        if valid_results:
            # Sort by number of words DESC (to prefer longer valid phrases), then by confidence
            valid_results.sort(key=lambda x: (len(x["query"].split()), x["confidence"], x["popularity"]), reverse=True)
            
            # Accept the longest phrase that meets our minimum confidence threshold
            for res in valid_results:
                if res["confidence"] >= 60:
                    best_result = res
                    break
            
    if best_result: 
        # TMDB's year is the ultimate truth. Overwrite the uploader's year if TMDB found one!
        final_year = best_result.get("year") or extracted_year
        return {
            "title": best_result["title"],
            "year": final_year,
            "episode": extracted_episode
        }
        
    # Fallback if TMDB fails or confidence is too low
    return {"title": " ".join(clean_tokens), "year": extracted_year, "episode": extracted_episode}
