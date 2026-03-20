import re
from rapidfuzz import fuzz

EDITION_WORDS = r'\b(goty|remastered|definitive edition|complete edition|hd|remake|deluxe|plus|collection)\b'

PLATFORM_MAP = {
    'playstation 4': 'PS4',
    'playstation 3': 'PS3',
    'playstation 2': 'PS2',
    'playstation': 'PS1',
    'playstation 5': 'PS5',
    'playstation vita': 'PSV',
    'psp': 'PSP',
    'xbox one': 'XOne',
    'xbox 360': 'X360',
    'xbox series x': 'XS',
    'xbox': 'XB',
    'nintendo 64': 'N64',
    'nintendo switch': 'NS',
    'switch': 'NS',
    'game boy advance': 'GBA',
    'nintendo ds': 'DS',
    'nintendo 3ds': '3DS',
    'wii u': 'WiiU',
    'wii': 'Wii',
    'gamecube': 'GC',
    'dreamcast': 'DC',
    'stadia': 'Stadia',
    'pc': 'PC',
}


def normalise_title(title: str) -> str:
    """Strip punctuation, lowercase, remove edition words for consistent matching."""
    title = title.lower()
    title = re.sub(r'[:\-–—]', ' ', title)
    title = re.sub(r'[^a-z0-9 ]', '', title)
    title = re.sub(EDITION_WORDS, '', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()


def normalise_platform(platform: str) -> str:
    """Normalise platform names so 'PS4' matches 'PlayStation 4'."""
    lower = platform.lower().strip()
    return PLATFORM_MAP.get(lower, platform.strip())


def extract_year(date_str: str) -> int | None:
    """Extract year from various date formats."""
    if not date_str:
        return None
    match = re.search(r'\d{4}', date_str)
    return int(match.group()) if match else None


def fuzzy_match(a: str, b: str) -> float:
    """Fuzzy match — returns similarity score 0-1. Replaces string-similarity."""
    return fuzz.ratio(normalise_title(a), normalise_title(b)) / 100