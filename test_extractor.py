import asyncio
import os
import sys

sys.path.append(os.getcwd())
from config import Config
Config.TMDB_API_KEY = "278485718e2e5bb6fc83d931581e3ddb"

from utils.title_extractor import extract_title_from_filename
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    filenames = [
        "@FBM_ALL.Diwanjimoola.2018.Malayalam.DVDrip.720p.mkv",
        "@CC Diwanjimoola Grand Prix 2018 720p DVDRip x265.mkv",
        "Channel @I_M_D_B 360.Darajeh.1394.720p.DVDRip.mkv",
        "@CK_Moviez.Chess.2006.Mal.HDRip.x264.mp4"
    ]
    for fname in filenames:
        print(f"\n=====================\nTesting: {fname}")
        res = await extract_title_from_filename(fname)
        print(f"Final Result: {res}")

if __name__ == "__main__":
    asyncio.run(test())
