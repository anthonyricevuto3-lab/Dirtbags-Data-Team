"""Exercise migrations and the complete upload/query boundary on SQLite or PostgreSQL."""
import io
import os
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, func
from src.player_development.app import create_app
from src.player_development.models import metadata, pitches, imports

SAMPLE = (Path(__file__).parent / 'fixtures/synthetic_outing.csv').read_bytes()

@pytest.fixture
def client(tmp_path, monkeypatch):
    url = os.getenv('TEST_DATABASE_URL', f'sqlite:///{tmp_path}/test.db')
    monkeypatch.setenv('DATABASE_URL', url)
    command.upgrade(Config('alembic.ini'), 'head')
    app = create_app(url)
    app.config['TESTING'] = True
    engine = app.extensions['db_engine']
    with engine.begin() as c:
        for table in reversed(metadata.sorted_tables):
            c.execute(table.delete())
    yield app.test_client()
    engine.dispose()


def upload(client, payload=SAMPLE, **kwargs):
    data = dict(game_id='demo-game1', played_on='2026-10-31', opponent='Demo Opponent',
                file=(io.BytesIO(payload), 'synthetic.csv'))
    data.update(kwargs)
    return client.post('/api/imports', data=data)


def details(client):
    pid = client.get('/api/players').json[0]['id']
    oid = client.get(f'/api/players/{pid}/outings').json[0]['id']
    return client.get(f'/api/outings/{oid}').json


def test_upload_review_and_units(client):
    response = upload(client)
    assert response.status_code == 201, response.json
    assert response.json['inserted'] == 6
    result = details(client)
    assert result['name'] == 'Demo Pitcher'
    slider = next(a for a in result['arsenal'] if a['pitch_type'] == 'Slider')
    assert slider['whiff_pct'] == 50
    assert slider['usage_pct'] == pytest.approx(100/3)
    fastball = next(a for a in result['arsenal'] if a['pitch_type'] == 'Fastball')
    assert fastball['velocity'] == 92
    assert result['locations'][0]['plate_x'] == pytest.approx(1.2)
    assert result['locations'][0]['plate_z'] == pytest.approx(31.2)


def test_duplicates_reordered_file_and_new_game(client):
    upload(client)
    duplicate = upload(client)
    assert duplicate.status_code == 200
    assert duplicate.json['inserted'] == 0
    assert duplicate.json['skipped'] == 6
    lines = SAMPLE.splitlines()
    reordered = b'\n'.join([lines[0]] + list(reversed(lines[1:]))) + b'\n'
    assert upload(client, reordered).json['skipped'] == 6
    assert details(client)['pitch_count'] == 6
    assert upload(client, game_id='demo-game2').json['inserted'] == 6


def test_conflict_rolls_back_every_row_and_import(client):
    upload(client)
    lines = SAMPLE.splitlines()
    # Insert a genuinely new pitch before encountering a conflict.
    extra = lines[1].replace(b',1,Fastball', b',7,Fastball')
    conflict = b'\n'.join([lines[0], extra, lines[1].replace(b',92,', b',99,')])
    response = upload(client, conflict)
    assert response.status_code == 409
    assert details(client)['pitch_count'] == 6
    with client.application.extensions['db_engine'].connect() as c:
        assert c.execute(select(func.count()).select_from(imports)).scalar() == 1


@pytest.mark.parametrize('payload', [b'', b'foo\nbar', SAMPLE.replace(b',92,', b',oops,'),
    SAMPLE.replace(b',92,', b',inf,'), SAMPLE.replace(b',1,Fastball', b',0,Fastball'),
    SAMPLE + SAMPLE.splitlines()[1] + b'\n', b'Pitcher,Pitcher\na,a\n'])
def test_invalid_upload_is_atomic(client, payload):
    assert upload(client, payload).status_code == 422
    assert client.get('/api/players').json == []


def test_missing_and_unknown_values_not_zero(client):
    response = upload(client, SAMPLE.replace(b',92,', b',,').replace(b'StrikeSwinging', b'Unclassified'))
    assert response.status_code == 201
    result = details(client)
    slider = next(a for a in result['arsenal'] if a['pitch_type'] == 'Slider')
    assert slider['whiff_pct'] is None
    fastball = next(a for a in result['arsenal'] if a['pitch_type'] == 'Fastball')
    assert fastball['velocity_samples'] == 2
    assert fastball['velocity'] == 92
    assert b'NaN' not in client.get('/api/players').data


def test_metadata_conflict_and_missing_fields(client):
    upload(client)
    assert upload(client, opponent='Different').status_code == 409
    assert upload(client, played_on='invalid').status_code == 422
    assert upload(client, game_id='').status_code == 422
    assert client.get('/api/outings/9999999').status_code == 404
    assert client.post('/api/imports').status_code == 400


def test_payload_limit(client):
    assert upload(client, b'x' * (11 * 1024 * 1024)).status_code == 413


def test_health(client):
    assert client.get('/api/health').json == {'status': 'ok'}


def test_warmup_filter_and_custom_tags(client):
    lines = SAMPLE.decode().splitlines()
    payload = '\n'.join([lines[0] + ',PitchSession,CustomTags'] +
        [row + (',Warmup,' if i == 0 else ',Live,HC_WHIFF' if i == 1 else ',Live,')
         for i, row in enumerate(lines[1:])]).encode()
    response = upload(client, payload)
    assert response.status_code == 201, response.json
    assert response.json['inserted'] == 5
    fastball = next(a for a in details(client)['arsenal'] if a['pitch_type'] == 'Fastball')
    assert fastball['whiff_pct'] == 50


def test_name_identity_warning_and_ambiguous_headers(client):
    payload = b'Pitcher,PitchNo,TaggedPitchType,PitchCall\nDemo,1,Fastball,StrikeCalled\n'
    assert upload(client, payload).json['warnings']
    ambiguous = b'Pitcher,PitchNo,pitch_number,TaggedPitchType,PitchCall\nDemo,1,1,Fastball,StrikeCalled\n'
    assert upload(client, ambiguous).status_code == 422


def test_wrong_column_count(client):
    assert upload(client, b'a,b\n1,2,3\n').status_code == 422


def test_built_frontend_is_served(client):
    if not Path('frontend/dist/index.html').exists():
        pytest.skip('Run npm run build to enable the static asset smoke test.')
    response = client.get('/')
    assert response.status_code == 200
    assert b'<div id="root">' in response.data
    for asset in Path('frontend/dist/assets').iterdir():
        assert client.get('/assets/' + asset.name).status_code == 200
