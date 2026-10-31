"""Strict import boundary; no inferred plate appearance outcomes or silent corrections."""
import csv
import hashlib
import io
import math
from datetime import date

import pandas as pd
from sqlalchemy import select, insert

from src.schemas.trackman_schema import TrackmanSchema
from src.schemas.custom_tags import apply_custom_tag_calls, filter_warmup_when_live_present
from .models import players, games, outings, pitches, imports


class ImportProblem(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def required(value, label, limit=200):
    value = str(value or '').strip()
    if value.lower() in ('', 'nan', 'none', '<na>', 'null') or len(value) > limit:
        raise ImportProblem(f'{label} is required and must be at most {limit} characters.')
    return value


def parse_csv(payload):
    try:
        text = payload.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(text), strict=True)
        header = next(reader)
        for line, fields in enumerate(reader, 2):
            if fields and len(fields) != len(header):
                raise ImportProblem(f'Row {line}: column count does not match the header.')
        if len(header) != len(set(header)):
            raise ImportProblem('Duplicate CSV column headers are not supported.')
        raw = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except (UnicodeError, StopIteration, csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ImportProblem('Upload a nonempty UTF-8 CSV with a header and consistent rows.') from exc
    if raw.empty or len(raw) > 50000:
        raise ImportProblem('Upload between 1 and 50,000 pitch rows.')
    original_count = len(raw)
    raw = filter_warmup_when_live_present(raw)
    # Reuse the repository mapping, but reject ambiguous aliases instead of silently choosing.
    chosen = {}
    for column in raw.columns:
        target = TrackmanSchema.COLUMN_MAPPING.get(column, column)
        if column == 'Pitcher' and 'PitcherId' in raw.columns:
            target = 'pitcher_name'
        if column == 'AutoPitchType' and 'TaggedPitchType' in raw.columns:
            continue
        if column in ('VertBreak', 'PfxZ') and 'InducedVertBreak' in raw.columns:
            continue
        if column == 'VertBreak':
            continue  # Total break is not induced vertical break.
        if column == 'PfxX' and 'HorzBreak' in raw.columns:
            continue
        if target in chosen:
            # Batter identity is not part of milestone-one pitch metrics.
            if target == 'batter_id':
                continue
            raise ImportProblem(f'Ambiguous columns for {target}; supply one source column.')
        chosen[target] = column
    for field in ('pitcher_id', 'pitch_number', 'pitch_type', 'pitch_call'):
        if field not in chosen:
            raise ImportProblem(f'Missing {field}; supported TrackMan aliases include PitcherId/Pitcher, PitchNo, TaggedPitchType and PitchCall.')
    canonical = pd.DataFrame({target: raw[col] for target, col in chosen.items()})
    canonical = apply_custom_tag_calls(canonical)
    records, seen = [], set()
    for index, row in canonical.iterrows():
        line = index + 2
        key = required(row['pitcher_id'], f'Row {line}: pitcher identity')
        if chosen['pitcher_id'] == 'Pitcher':
            key = required('name:' + key, f'Row {line}: name-based identity')
        name = required(row.get('pitcher_name', row['pitcher_id']) or key, f'Row {line}: pitcher name')
        number = str(row['pitch_number']).strip()
        if not number.isascii() or not number.isdigit() or len(number) > 10 or not 1 <= int(number) <= 2147483647:
            raise ImportProblem(f'Row {line}: pitch number must be a positive integer.')
        number = int(number)
        identity = (key, number)
        if identity in seen:
            raise ImportProblem(f'Row {line}: duplicate pitch number for the same pitcher.')
        seen.add(identity)
        record = {'pitch_number': number,
                  'pitch_type': required(row['pitch_type'], f'Row {line}: pitch type', 100),
                  'pitch_call': required(row['pitch_call'], f'Row {line}: pitch call', 100)}
        for field in ('velocity', 'spin_rate', 'ivb', 'hb', 'plate_x', 'plate_z'):
            value = row.get(field, '')
            if pd.isna(value) or str(value).strip().lower() in ('', 'nan', 'na', 'null'):
                record[field] = None
                continue
            try:
                value = float(value)
            except (ValueError, TypeError) as exc:
                raise ImportProblem(f'Row {line}: {field} must be numeric or blank.') from exc
            if not math.isfinite(value) or (field in ('velocity', 'spin_rate') and value <= 0):
                raise ImportProblem(f'Row {line}: invalid {field}.')
            if chosen.get(field) in ('PlateLocSide', 'PlateLocHeight'):
                value *= 12  # Existing canonical schema uses inches.
            record[field] = value
        call = record['pitch_call'].lower()
        swings = {'strikeswinging', 'foulball', 'foulballfieldable', 'foulballnotfieldable', 'inplay'}
        takes = {'strikecalled', 'ballcalled', 'ballindirt', 'hitbypitch', 'ballintentional'}
        record['swing'] = call in swings if call in swings | takes else None
        record['whiff'] = call == 'strikeswinging' if call in swings | takes else None
        records.append((key, name, record))
    warnings = []
    if chosen['pitcher_id'] == 'Pitcher':
        warnings.append('Player identity uses names. Prefer PitcherId to distinguish same-name players.')
    if any(record['swing'] is None for _, _, record in records):
        warnings.append('Unknown pitch calls: whiff rate is unavailable for affected pitch groups.')
    if len(raw) != original_count:
        warnings.append('Warmup rows were excluded because this file contains live pitches.')
    return records, warnings


def ingest(connection, payload, filename, game_key, played_on, opponent):
    game_key = required(game_key, 'Game ID')
    opponent = required(opponent, 'Opponent')
    try:
        played_on = date.fromisoformat(played_on)
    except (TypeError, ValueError) as exc:
        raise ImportProblem('Game date must use YYYY-MM-DD.') from exc
    records, warnings = parse_csv(payload)
    game = connection.execute(select(games).where(games.c.source_key == game_key)).mappings().first()
    if game and (game['played_on'] != played_on or game['opponent'] != opponent):
        raise ImportProblem('This Game ID already has a different date or opponent.', 409)
    gid = game['id'] if game else connection.execute(insert(games).values(
        source_key=game_key, played_on=played_on, opponent=opponent)).inserted_primary_key[0]
    checksum = hashlib.sha256(payload).hexdigest()
    previous = connection.execute(select(imports).where(
        imports.c.game_id == gid, imports.c.checksum == checksum)).mappings().first()
    if previous:
        return {'import_id': previous['id'], 'inserted': 0, 'skipped': len(records), 'warnings': warnings}
    iid = connection.execute(insert(imports).values(game_id=gid, checksum=checksum,
        filename=filename, inserted_count=0, skipped_count=0)).inserted_primary_key[0]
    inserted = skipped = 0
    cache, pending = {}, []
    for key, name, record in records:
        if key not in cache:
            pid = connection.execute(select(players.c.id).where(players.c.source_key == key)).scalar_one_or_none()
            if pid is None:
                pid = connection.execute(insert(players).values(source_key=key, name=name)).inserted_primary_key[0]
            oid = connection.execute(select(outings.c.id).where(
                outings.c.game_id == gid, outings.c.player_id == pid)).scalar_one_or_none()
            if oid is None:
                oid = connection.execute(insert(outings).values(game_id=gid, player_id=pid)).inserted_primary_key[0]
            existing_rows = connection.execute(select(pitches.c.pitch_number, pitches.c.canonical).where(
                pitches.c.outing_id == oid)).all()
            cache[key] = (oid, dict(existing_rows))
        oid, existing_records = cache[key]
        existing = existing_records.get(record['pitch_number'])
        if existing is not None:
            if existing != record:
                raise ImportProblem(f'Pitch {record["pitch_number"]} conflicts with an existing record. No changes were saved; corrections require review.', 409)
            skipped += 1
        else:
            pending.append(dict(outing_id=oid, import_id=iid, canonical=record, **record))
            inserted += 1
    for start in range(0, len(pending), 1000):
        connection.execute(insert(pitches), pending[start:start + 1000])
    connection.execute(imports.update().where(imports.c.id == iid).values(
        inserted_count=inserted, skipped_count=skipped))
    return {'import_id': iid, 'inserted': inserted, 'skipped': skipped, 'warnings': warnings}
