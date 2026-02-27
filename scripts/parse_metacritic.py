import pandas as pd
from dataclasses import dataclass
from typing import Optional
from scripts.normalise import normalise_title, normalise_platform, extract_year


@dataclass
class MetacriticRow:
    name: str
    normalized_name: str
    platform: str
    normalized_platform: str
    release_date: Optional[str]
    release_year: Optional[int]
    summary: Optional[str]
    meta_score: Optional[float]
    user_review: Optional[float]


def zap_float(val) -> Optional[float]:
    """Parse float or return None."""
    try:
        if pd.isna(val) or str(val).strip() in ('', 'tbd'):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_metacritic(file_path: str) -> list[MetacriticRow]:
    print('📂 Reading Metacritic CSV...')
    df = pd.read_csv(file_path, dtype=str).fillna('')

    print(f'📊 Raw Metacritic rows: {len(df)}')

    rows = []
    for _, r in df.iterrows():
        name = r.get('name', '').strip()
        if not name:
            continue

        rows.append(MetacriticRow(
            name=name,
            normalized_name=normalise_title(name),
            platform=r.get('platform', '').strip(),
            normalized_platform=normalise_platform(r.get('platform', '')),
            release_date=r.get('release_date', '').strip() or None,
            release_year=extract_year(r.get('release_date', '')),
            summary=r.get('summary', '').strip() or None,
            meta_score=zap_float(r.get('meta_score')),
            user_review=zap_float(r.get('user_review')),
        ))

    print(f'✅ Parsed {len(rows)} valid Metacritic rows')
    return rows