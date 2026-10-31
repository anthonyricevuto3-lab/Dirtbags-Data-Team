"""Local-first API. Run migrations before serving; no schema changes at startup."""
import os
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import create_engine, select, func, case
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from .models import players, games, outings, pitches
from .ingestion import ingest, ImportProblem


def create_app(database_url=None):
    static = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    app = Flask(__name__, static_folder=None)
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
    engine = create_engine(database_url or os.environ.get('DATABASE_URL', 'sqlite:///development.db'), pool_pre_ping=True)
    app.extensions['db_engine'] = engine

    @app.errorhandler(ImportProblem)
    def invalid(error):
        return jsonify(error=str(error)), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.get('/api/health')
    def health():
        with engine.connect() as connection:
            connection.execute(select(players.c.id).limit(1))
        return jsonify(status='ok')

    @app.post('/api/imports')
    def upload():
        file = request.files.get('file')
        if file is None or not file.filename.lower().endswith('.csv'):
            raise ImportProblem('Choose a CSV file.', 400)
        payload = file.read()
        for attempt in range(2):
            try:
                with engine.begin() as connection:
                    result = ingest(connection, payload, secure_filename(file.filename)[:255] or 'upload.csv',
                                    request.form.get('game_id'), request.form.get('played_on'), request.form.get('opponent'))
                return jsonify(result), 201 if result['inserted'] else 200
            except IntegrityError:
                # A concurrent importer may have created the same identities. Retry from a new transaction.
                if attempt:
                    raise ImportProblem('Import conflicted with another upload. Please retry.', 409)
        raise AssertionError('unreachable')

    @app.get('/api/players')
    def list_players():
        with engine.connect() as connection:
            rows = connection.execute(select(players).order_by(players.c.name)).mappings().all()
        return jsonify([dict(row) for row in rows])

    @app.get('/api/players/<int:player_id>/outings')
    def list_outings(player_id):
        query = select(outings.c.id, games.c.source_key.label('game_id'), games.c.played_on,
                       games.c.opponent, func.count(pitches.c.id).label('pitch_count')).select_from(
                       outings.join(games).join(pitches)).where(outings.c.player_id == player_id).group_by(
                       outings.c.id, games.c.source_key, games.c.played_on, games.c.opponent).order_by(
                       games.c.played_on.desc(), outings.c.id.desc())
        with engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return jsonify([{**dict(row), 'played_on': row['played_on'].isoformat()} for row in rows])

    @app.get('/api/outings/<int:outing_id>')
    def outing(outing_id):
        summary = select(pitches.c.pitch_type, func.count().label('count'),
                         func.avg(pitches.c.velocity).label('velocity'),
                         func.count(pitches.c.velocity).label('velocity_samples'),
                         func.avg(pitches.c.ivb).label('ivb'), func.avg(pitches.c.hb).label('hb'),
                         func.sum(case((pitches.c.swing.is_(True), 1), else_=0)).label('swings'),
                         func.sum(case((pitches.c.whiff.is_(True), 1), else_=0)).label('whiffs'),
                         func.count(pitches.c.swing).label('known_calls')).where(
                         pitches.c.outing_id == outing_id).group_by(pitches.c.pitch_type).order_by(pitches.c.pitch_type)
        with engine.connect() as connection:
            info = connection.execute(select(outings.c.id, players.c.name, games.c.played_on, games.c.opponent)
                .select_from(outings.join(players).join(games)).where(outings.c.id == outing_id)).mappings().first()
            if info is None:
                raise ImportProblem('Outing not found.', 404)
            rows = [dict(row) for row in connection.execute(summary).mappings()]
            locations = [dict(row) for row in connection.execute(select(pitches.c.pitch_number,
                pitches.c.pitch_type, pitches.c.plate_x, pitches.c.plate_z).where(
                pitches.c.outing_id == outing_id).order_by(pitches.c.pitch_number)).mappings()]
        total = sum(row['count'] for row in rows)
        for row in rows:
            row['usage_pct'] = row['count'] / total * 100
            row['whiff_pct'] = (row['whiffs'] / row['swings'] * 100
                if row['swings'] and row['known_calls'] == row['count'] else None)
        return jsonify(**{**dict(info), 'played_on': info['played_on'].isoformat()},
                       pitch_count=total, arsenal=rows, locations=locations)

    @app.get('/')
    def index():
        return send_from_directory(static, 'index.html')

    @app.get('/assets/<path:filename>')
    def assets(filename):
        return send_from_directory(static / 'assets', filename)

    return app
