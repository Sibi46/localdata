"""Offline, additive GeoNames import. Never reparents or deletes existing locations."""
import gzip
import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from django.core.management.base import CommandError
from django.db import transaction
from .models import Country, State, District

SNAPSHOT = Path(__file__).parent / 'data/geonames/admin-divisions-2026-10-13.json.gz'
SHA256 = '184aa116f2f9bf16c4bd26cc3a292e7b62b08c237dea3186a235aefe2c441f76'


def normal(name):
    return ''.join(c for c in unicodedata.normalize('NFKD', name).casefold() if c.isalnum())


def load_snapshot():
    raw = SNAPSHOT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise CommandError('Geography snapshot checksum mismatch. Import stopped.')
    data = json.loads(gzip.decompress(raw))
    for key, count in [('states', 3865), ('districts', 47642)]:
        if len(data[key]) != count:
            raise CommandError('Geography snapshot row count mismatch.')
        ids, codes = set(), set()
        for row in data[key]:
            if len(row) != 4 or not row[3].isdigit() or not row[1] or len(row[1]) > 100 or row[0] in codes or row[3] in ids:
                raise CommandError('Invalid or duplicate geography row.')
            ids.add(row[3]); codes.add(row[0])
    return data


def available_name(name, source_code, occupied):
    candidate = name
    if normal(candidate) in occupied:
        suffix = ' (' + source_code + ')'
        candidate = name[:100-len(suffix)] + suffix
    if normal(candidate) in occupied:
        raise CommandError('Conflicting location name: ' + source_code)
    occupied.add(normal(candidate))
    return candidate


@transaction.atomic
def import_world_geography(*, dry_run=True, data=None):
    data = load_snapshot() if data is None else data
    countries = Country.objects.all()
    if not dry_run:
        # Serialize imports; source IDs also have database uniqueness constraints.
        countries = countries.select_for_update()
    country_map = {c.code.upper(): c for c in countries}
    if not country_map:
        raise CommandError('Apply country migrations before importing geography.')
    stats = {'states_created': 0, 'districts_created': 0, 'states_linked': 0,
             'districts_linked': 0, 'states_existing': 0, 'districts_existing': 0}
    skipped = defaultdict(list)
    states = list(State.objects.all())
    by_id = {s.geonames_id: s for s in states if s.geonames_id}
    by_name = defaultdict(list)
    used_names = {normal(s.name) for s in states}
    used_codes = {s.code.casefold() for s in states}
    for s in states:
        by_name[(s.country_id, normal(s.name))].append(s)
    created_states, linked_states, parents = [], [], {}
    for code, name, ascii_name, gid in data['states']:
        gid = int(gid)
        country = country_map.get(code.split('.')[0])
        if country is None:
            skipped['unknown_country'].append(code); continue
        state = by_id.get(gid)
        if state:
            if state.country_id != country.pk:
                skipped['state_parent_conflict'].append(code); continue
            stats['states_existing'] += 1
        else:
            names = {normal(name), normal(ascii_name)}
            if code == 'IN.01': names.add(normal('Andaman and Nicobar Islands'))
            matches = {s.pk: s for key in names for s in by_name.get((country.pk, key), []) if not s.geonames_id}
            if len(matches) > 1:
                skipped['ambiguous_state'].append(code); continue
            if matches:
                state = next(iter(matches.values()))
                state.geonames_id = gid
                linked_states.append(state)
                stats['states_linked'] += 1
            else:
                state_code = 'GN' + str(gid)
                if state_code.casefold() in used_codes:
                    skipped['state_code_conflict'].append(code); continue
                used_codes.add(state_code.casefold())
                state = State(country=country, name=available_name(name, code, used_names), code=state_code, geonames_id=gid)
                created_states.append(state)
                stats['states_created'] += 1
        parents[code] = state
    districts = list(District.objects.all())
    district_ids = {d.geonames_id: d for d in districts if d.geonames_id}
    district_names, occupied = defaultdict(list), defaultdict(set)
    indian_states = {s.pk for s in states if s.country_id == getattr(country_map.get('IN'), 'pk', None)}
    def district_key(name, is_india):
        if is_india and name.lower().endswith(' district'):
            name = name[:-9]
        return normal(name)
    for d in districts:
        district_names[(d.state_id, district_key(d.name, d.state_id in indian_states))].append(d)
        occupied[('pk', d.state_id)].add(normal(d.name))
    created_districts, linked_districts = [], []
    for code, name, ascii_name, gid in data['districts']:
        gid = int(gid)
        state = parents.get(code.rsplit('.', 1)[0])
        if not state:
            skipped['missing_state'].append(code); continue
        district = district_ids.get(gid)
        if district:
            if district.state_id != state.pk:
                skipped['district_parent_conflict'].append(code); continue
            stats['districts_existing'] += 1
            continue
        keys = {district_key(n, code.startswith('IN.')) for n in [name, ascii_name]}
        matches = {d.pk: d for key in keys for d in district_names.get((state.pk, key), []) if not d.geonames_id} if state.pk else {}
        if len(matches) > 1:
            skipped['ambiguous_district'].append(code); continue
        if matches:
            district = next(iter(matches.values()))
            district.geonames_id = gid
            linked_districts.append(district)
            stats['districts_linked'] += 1
        else:
            parent_key = ('pk', state.pk) if state.pk else ('source', state.geonames_id)
            district = District(state=state, name=available_name(name, code, occupied[parent_key]), geonames_id=gid)
            created_districts.append(district)
            stats['districts_created'] += 1
    if not dry_run:
        State.objects.bulk_create(created_states, batch_size=500)
        State.objects.bulk_update(linked_states, ['geonames_id'], batch_size=500)
        state_pks = dict(State.objects.filter(geonames_id__isnull=False).values_list('geonames_id', 'pk'))
        for d in created_districts:
            d.state_id = state_pks[d.state.geonames_id]
        District.objects.bulk_create(created_districts, batch_size=500)
        District.objects.bulk_update(linked_districts, ['geonames_id'], batch_size=500)
    stats['dry_run'] = dry_run
    stats['skipped'] = dict(skipped)
    stats['countries_without_state_rows'] = sorted(set(country_map) - {c.split('.')[0] for c in parents})
    stats['countries_without_district_rows'] = sorted(set(country_map) - {r[0].split('.')[0] for r in data['districts'] if r[0].rsplit('.', 1)[0] in parents})
    return stats
