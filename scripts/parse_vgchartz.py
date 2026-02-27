import pandas as pd
from dataclasses import dataclass
from typing import Optional
from scripts.normalise import normalise_title, normalise_platform, extract_year


@dataclass
class VGRow:
    title: str
    normalized_title: str
    console: str
    normalized_console: str
    genre: str
    publisher: str
    developer: str
    critic_score: Optional[float]
    total_sales: Optional[float]
    na_sales: Optional[float]
    jp_sales: Optional[float]
    pal_sales: Optional[float]
    other_sales: Optional[float]
    release_date: Optional[str]
    release_year: Optional[int]


def zap_float(val) -> Optional[float]:
    """Parse float or return None."""
    try:
        if pd.isna(val) or str(val).strip() in ('', 'N/A'):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_vgchartz(file_path: str) -> list[VGRow]:
    print('📂 Reading VGChartz CSV...')
    df = pd.read_csv(file_path, dtype=str).fillna('')

    print(f'📊 Raw VGChartz rows: {len(df)}')

    rows = []
    for _, r in df.iterrows():
        title = r.get('title', '').strip()
        if not title:
            continue

        rows.append(VGRow(
            title=title,
            normalized_title=normalise_title(title),
            console=r.get('console', '').strip(),
            normalized_console=normalise_platform(r.get('console', '')),
            genre=r.get('genre', '').strip() or 'Unknown',
            publisher=r.get('publisher', '').strip() or 'Unknown',
            developer=r.get('developer', '').strip() or 'Unknown',
            critic_score=zap_float(r.get('critic_score')),
            total_sales=zap_float(r.get('total_sales')),
            na_sales=zap_float(r.get('na_sales')),
            jp_sales=zap_float(r.get('jp_sales')),
            pal_sales=zap_float(r.get('pal_sales')),
            other_sales=zap_float(r.get('other_sales')),
            release_date=r.get('release_date', '').strip() or None,
            release_year=extract_year(r.get('release_date', '')),
        ))

    print(f'✅ Parsed {len(rows)} valid VGChartz rows')
    return rows