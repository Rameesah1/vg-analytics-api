import uuid
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean,
    Text, ForeignKey, UniqueConstraint, Index,
    DateTime, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


#LOOKUP TABLES 

class Platform(Base):
    __tablename__ = 'platform'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    manufacturer = Column(Text)
    release_year = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', name='platform_name_idx'),
    )


class Genre(Base):
    __tablename__ = 'genre'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', name='genre_name_idx'),
    )


class Developer(Base):
    __tablename__ = 'developer'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    country = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', name='developer_name_idx'),
    )


class Publisher(Base):
    __tablename__ = 'publisher'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', name='publisher_name_idx'),
    )


# core tables

class Game(Base):
    __tablename__ = 'game'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_title = Column(Text, nullable=False)
    normalized_title = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    releases = relationship('GameRelease', back_populates='game', cascade='all, delete')

    __table_args__ = (
        UniqueConstraint('normalized_title', name='game_normalized_title_idx'),
    )


class GameRelease(Base):
    __tablename__ = 'game_release'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey('game.id', ondelete='CASCADE'), nullable=False)
    platform_id = Column(UUID(as_uuid=True), ForeignKey('platform.id'), nullable=False)

    release_date = Column(Text)
    release_year = Column(Integer)

    # VGChartz sales data (in millions)
    total_sales = Column(Numeric(6, 2))
    na_sales = Column(Numeric(6, 2))
    jp_sales = Column(Numeric(6, 2))
    pal_sales = Column(Numeric(6, 2))
    other_sales = Column(Numeric(6, 2))

    # VGChartz critic score (0-10 scale)
    vg_critic_score = Column(Numeric(4, 2))

    # Metacritic data (joined from second dataset)
    meta_score = Column(Numeric(5, 2))      # 0-100 scale
    user_review = Column(Numeric(4, 2))     # 0-10 scale
    summary = Column(Text)

    # Mashup provenance fields
    match_confidence = Column(Numeric(3, 2), default=0)
    match_strategy = Column(Text, default='NONE')   # EXACT, FUZZY, NONE
    has_vgchartz = Column(Boolean, default=False)
    has_metacritic = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    game = relationship('Game', back_populates='releases')
    platform = relationship('Platform')
    genres = relationship('GameReleaseGenre', back_populates='game_release', cascade='all, delete')
    developers = relationship('GameReleaseDeveloper', back_populates='game_release', cascade='all, delete')
    publishers = relationship('GameReleasePublisher', back_populates='game_release', cascade='all, delete')

    __table_args__ = (
        Index('release_platform_year_idx', 'platform_id', 'release_year'),
        Index('release_year_idx', 'release_year'),
        Index('release_sales_idx', 'total_sales'),
        Index('release_meta_score_idx', 'meta_score'),
        Index('release_user_review_idx', 'user_review'),
    )


# join tables

class GameReleaseGenre(Base):
    __tablename__ = 'game_release_genre'

    game_release_id = Column(UUID(as_uuid=True), ForeignKey('game_release.id', ondelete='CASCADE'), nullable=False, primary_key=True)
    genre_id = Column(UUID(as_uuid=True), ForeignKey('genre.id', ondelete='CASCADE'), nullable=False, primary_key=True)

    game_release = relationship('GameRelease', back_populates='genres')
    genre = relationship('Genre')

    __table_args__ = (
        UniqueConstraint('game_release_id', 'genre_id', name='grg_pk'),
        Index('grg_genre_idx', 'genre_id'),
    )


class GameReleaseDeveloper(Base):
    __tablename__ = 'game_release_developer'

    game_release_id = Column(UUID(as_uuid=True), ForeignKey('game_release.id', ondelete='CASCADE'), nullable=False, primary_key=True)
    developer_id = Column(UUID(as_uuid=True), ForeignKey('developer.id', ondelete='CASCADE'), nullable=False, primary_key=True)

    game_release = relationship('GameRelease', back_populates='developers')
    developer = relationship('Developer')

    __table_args__ = (
        UniqueConstraint('game_release_id', 'developer_id', name='grd_pk'),
        Index('grd_dev_idx', 'developer_id'),
    )


class GameReleasePublisher(Base):
    __tablename__ = 'game_release_publisher'

    game_release_id = Column(UUID(as_uuid=True), ForeignKey('game_release.id', ondelete='CASCADE'), nullable=False, primary_key=True)
    publisher_id = Column(UUID(as_uuid=True), ForeignKey('publisher.id', ondelete='CASCADE'), nullable=False, primary_key=True)

    game_release = relationship('GameRelease', back_populates='publishers')
    publisher = relationship('Publisher')

    __table_args__ = (
        UniqueConstraint('game_release_id', 'publisher_id', name='grp_pk'),
        Index('grp_pub_idx', 'publisher_id'),
    )


# Users

class User(Base):
    __tablename__ = 'user'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, nullable=False, unique=True)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default='USER')  # USER or ADMIN
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    squads = relationship('Squad', back_populates='user', cascade='all, delete')
    battles = relationship('Battle', back_populates='user', cascade='all, delete')

    __table_args__ = (
        UniqueConstraint('username', name='user_username_idx'),
        UniqueConstraint('email', name='user_email_idx'),
    )


# Squads
class Squad(Base):
    __tablename__ = 'squad'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship('User', back_populates='squads')
    items = relationship('SquadItem', back_populates='squad', cascade='all, delete')

    __table_args__ = (
        Index('squad_user_idx', 'user_id'),
    )


class SquadItem(Base):
    __tablename__ = 'squad_item'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    squad_id = Column(UUID(as_uuid=True), ForeignKey('squad.id', ondelete='CASCADE'), nullable=False)
    game_release_id = Column(UUID(as_uuid=True), ForeignKey('game_release.id', ondelete='CASCADE'), nullable=False)
    notes = Column(Text)
    added_at = Column(DateTime, server_default=func.now(), nullable=False)

    squad = relationship('Squad', back_populates='items')
    game_release = relationship('GameRelease')

    __table_args__ = (
        UniqueConstraint('squad_id', 'game_release_id', name='squad_item_unique'),
        Index('squad_item_squad_idx', 'squad_id'),
    )


# Battles

class Battle(Base):
    __tablename__ = 'battle'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    squad_a_id = Column(UUID(as_uuid=True), ForeignKey('squad.id'), nullable=False)
    squad_b_id = Column(UUID(as_uuid=True), ForeignKey('squad.id'), nullable=False)
    winner_squad_id = Column(UUID(as_uuid=True), ForeignKey('squad.id'), nullable=True)  # null = draw
    score_a = Column(Numeric(8, 3))
    score_b = Column(Numeric(8, 3))
    score_diff = Column(Numeric(8, 3))
    weights_json = Column(Text)     # stored as JSON string
    dna_a_json = Column(Text)       # squad A DNA snapshot at battle time
    dna_b_json = Column(Text)       # squad B DNA snapshot at battle time
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship('User', back_populates='battles')

    __table_args__ = (
        Index('battle_user_idx', 'user_id'),
        Index('battle_squad_a_idx', 'squad_a_id'),
        Index('battle_squad_b_idx', 'squad_b_id'),
    )