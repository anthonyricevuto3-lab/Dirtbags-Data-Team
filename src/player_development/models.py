"""Relational identity and import provenance for the first platform milestone."""
from sqlalchemy import (MetaData, Table, Column, Integer, String, Float, Boolean,
                        Date, ForeignKey, UniqueConstraint, CheckConstraint, JSON, Index)

metadata = MetaData()
players = Table('players', metadata,
    Column('id', Integer, primary_key=True),
    Column('source_key', String(200), nullable=False, unique=True),
    Column('name', String(200), nullable=False))
games = Table('games', metadata,
    Column('id', Integer, primary_key=True),
    Column('source_key', String(200), nullable=False, unique=True),
    Column('played_on', Date, nullable=False),
    Column('opponent', String(200), nullable=False))
imports = Table('imports', metadata,
    Column('id', Integer, primary_key=True),
    Column('game_id', ForeignKey('games.id'), nullable=False),
    Column('checksum', String(64), nullable=False),
    Column('filename', String(255), nullable=False),
    Column('inserted_count', Integer, nullable=False),
    Column('skipped_count', Integer, nullable=False),
    UniqueConstraint('game_id', 'checksum'))
outings = Table('outings', metadata,
    Column('id', Integer, primary_key=True),
    Column('player_id', ForeignKey('players.id'), nullable=False),
    Column('game_id', ForeignKey('games.id'), nullable=False),
    UniqueConstraint('player_id', 'game_id'))
pitches = Table('pitches', metadata,
    Column('id', Integer, primary_key=True),
    Column('outing_id', ForeignKey('outings.id'), nullable=False),
    Column('import_id', ForeignKey('imports.id'), nullable=False),
    Column('pitch_number', Integer, nullable=False),
    Column('pitch_type', String(100), nullable=False),
    Column('pitch_call', String(100), nullable=False),
    Column('velocity', Float), Column('spin_rate', Float),
    Column('ivb', Float), Column('hb', Float),
    Column('plate_x', Float), Column('plate_z', Float),
    Column('swing', Boolean), Column('whiff', Boolean),
    Column('canonical', JSON, nullable=False),
    UniqueConstraint('outing_id', 'pitch_number'),
    CheckConstraint('pitch_number > 0'),
    CheckConstraint('velocity IS NULL OR velocity > 0'))
Index('ix_outings_game', outings.c.game_id)
Index('ix_pitches_outing_type', pitches.c.outing_id, pitches.c.pitch_type)
