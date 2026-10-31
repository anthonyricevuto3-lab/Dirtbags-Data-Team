"""Initial immutable schema for player development imports."""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = depends_on = None


def upgrade():
    op.create_table('players', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('source_key', sa.String(200), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False))
    op.create_table('games', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('source_key', sa.String(200), nullable=False, unique=True),
        sa.Column('played_on', sa.Date, nullable=False), sa.Column('opponent', sa.String(200), nullable=False))
    op.create_table('imports', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('game_id', sa.Integer, sa.ForeignKey('games.id'), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False), sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('inserted_count', sa.Integer, nullable=False), sa.Column('skipped_count', sa.Integer, nullable=False),
        sa.UniqueConstraint('game_id', 'checksum'))
    op.create_table('outings', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('player_id', sa.Integer, sa.ForeignKey('players.id'), nullable=False),
        sa.Column('game_id', sa.Integer, sa.ForeignKey('games.id'), nullable=False),
        sa.UniqueConstraint('player_id', 'game_id'))
    op.create_table('pitches', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('outing_id', sa.Integer, sa.ForeignKey('outings.id'), nullable=False),
        sa.Column('import_id', sa.Integer, sa.ForeignKey('imports.id'), nullable=False),
        sa.Column('pitch_number', sa.Integer, nullable=False),
        sa.Column('pitch_type', sa.String(100), nullable=False), sa.Column('pitch_call', sa.String(100), nullable=False),
        *[sa.Column(name, sa.Float) for name in ('velocity', 'spin_rate', 'ivb', 'hb', 'plate_x', 'plate_z')],
        sa.Column('swing', sa.Boolean), sa.Column('whiff', sa.Boolean), sa.Column('canonical', sa.JSON, nullable=False),
        sa.UniqueConstraint('outing_id', 'pitch_number'), sa.CheckConstraint('pitch_number > 0'),
        sa.CheckConstraint('velocity IS NULL OR velocity > 0'))
    op.create_index('ix_outings_game', 'outings', ['game_id'])
    op.create_index('ix_pitches_outing_type', 'pitches', ['outing_id', 'pitch_type'])


def downgrade():
    for table in ('pitches', 'outings', 'imports', 'games', 'players'):
        op.drop_table(table)
