import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from src.db.session import SessionLocal
from src.db.models import (
    Platform, Genre, Developer, Publisher,
    Game, GameRelease,
    GameReleaseGenre, GameReleaseDeveloper, GameReleasePublisher,
)
from scripts.parse_vgchartz import parse_vgchartz
from scripts.parse_metacritic import parse_metacritic
from scripts.normalise import fuzzy_match


def upsert_by_name(db: Session, model, name: str) -> str:
    """Insert if not exists, return id."""
    existing = db.execute(select(model).where(model.name == name)).scalar_one_or_none()
    if existing:
        return existing.id
    obj = model(name=name)
    db.add(obj)
    db.flush()
    return obj.id


def main():
    print('Starting seed...\n')
    db = SessionLocal()

    try:
        # Parse and insert VGChartz data
        vg_rows = parse_vgchartz('./data_comp3011/vgchartz-2024.csv')
        print('\n Inserting VGChartz data...')

        inserted = 0
        skipped = 0

        for row in vg_rows:
            try:
                platform_id = upsert_by_name(db, Platform, row.normalized_console or row.console)
                genre_id = upsert_by_name(db, Genre, row.genre)
                developer_id = upsert_by_name(db, Developer, row.developer)
                publisher_id = upsert_by_name(db, Publisher, row.publisher)

                existing_game = db.execute(
                    select(Game).where(Game.normalized_title == row.normalized_title)
                ).scalar_one_or_none()

                if existing_game:
                    game_id = existing_game.id
                else:
                    game = Game(canonical_title=row.title, normalized_title=row.normalized_title)
                    db.add(game)
                    db.flush()
                    game_id = game.id

                existing_release = db.execute(
                    select(GameRelease).where(
                        and_(
                            GameRelease.game_id == game_id,
                            GameRelease.platform_id == platform_id,
                        )
                    )
                ).scalar_one_or_none()

                if existing_release:
                    release_id = existing_release.id
                else:
                    release = GameRelease(
                        game_id=game_id,
                        platform_id=platform_id,
                        release_date=row.release_date,
                        release_year=row.release_year,
                        total_sales=row.total_sales,
                        na_sales=row.na_sales,
                        jp_sales=row.jp_sales,
                        pal_sales=row.pal_sales,
                        other_sales=row.other_sales,
                        vg_critic_score=row.critic_score,
                        has_vgchartz=True,
                        match_strategy='NONE',
                        match_confidence=0,
                    )
                    db.add(release)
                    db.flush()
                    release_id = release.id

                # join tables
                db.merge(GameReleaseGenre(game_release_id=release_id, genre_id=genre_id))
                db.merge(GameReleaseDeveloper(game_release_id=release_id, developer_id=developer_id))
                db.merge(GameReleasePublisher(game_release_id=release_id, publisher_id=publisher_id))

                inserted += 1
                if inserted % 1000 == 0:
                    db.commit()
                    print(f'  Inserted {inserted} releases...')

            except Exception:
                db.rollback()
                skipped += 1

        db.commit()
        print(f'\n VGChartz: {inserted} inserted, {skipped} skipped')

        # -match metacritic 
        mc_rows = parse_metacritic('./data_comp3011/all_games.csv')
        print('\n Matching Metacritic data...')

        matched = 0
        fuzzy_matched = 0
        unmatched = 0

        enable_fuzzy = os.environ.get('SEED_ENABLE_FUZZY', 'false').lower() == 'true'

        for row in mc_rows:
            try:
                platform = db.execute(
                    select(Platform).where(Platform.name == row.normalized_platform)
                ).scalar_one_or_none()

                if not platform:
                    unmatched += 1
                    continue

                game = db.execute(
                    select(Game).where(Game.normalized_title == row.normalized_name)
                ).scalar_one_or_none()

                release = None

                if game:
                    release = db.execute(
                        select(GameRelease).where(
                            and_(
                                GameRelease.game_id == game.id,
                                GameRelease.platform_id == platform.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if release:
                        release.meta_score = row.meta_score
                        release.user_review = row.user_review
                        release.summary = row.summary
                        release.has_metacritic = True
                        release.match_strategy = 'EXACT'
                        release.match_confidence = 1.00
                        db.commit()
                        matched += 1
                        continue

                if enable_fuzzy:
                    platform_releases = db.execute(
                        select(GameRelease, Game.normalized_title)
                        .join(Game, Game.id == GameRelease.game_id)
                        .where(GameRelease.platform_id == platform.id)
                    ).all()

                    best_match = None
                    best_score = 0.0

                    for rel, norm_title in platform_releases:
                        score = fuzzy_match(row.normalized_name, norm_title)
                        if score > best_score:
                            best_score = score
                            best_match = rel

                    if best_match and best_score >= 0.80:
                        best_match.meta_score = row.meta_score
                        best_match.user_review = row.user_review
                        best_match.summary = row.summary
                        best_match.has_metacritic = True
                        best_match.match_strategy = 'FUZZY'
                        best_match.match_confidence = round(best_score, 2)
                        db.commit()
                        fuzzy_matched += 1
                        continue

                unmatched += 1

            except Exception:
                db.rollback()
                unmatched += 1

        print(f'Exact matches: {matched}')
        print(f' Fuzzy matches: {fuzzy_matched}')
        print(f' Unmatched: {unmatched}')
        print('\nSeed complete!')

    finally:
        db.close()


if __name__ == '__main__':
    main()