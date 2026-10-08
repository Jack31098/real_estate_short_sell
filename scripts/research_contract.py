"""V2 observation validation, vintage selection, and conservative arithmetic."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from datetime import datetime, timedelta, timezone

from research_sources import ROOT, OUT, digest, write_json

SCOPE_FIELDS = ('entity','period_end','geography','portfolio','occupancy','measurement','basis','netting','ownership')
REQUIRED = ('observation_id','entity_id','entity_scope','period_end','fiscal_label','published_at',
            'available_at','retrieved_at','source_id','page_or_table','metric','value','unit',
            'denominator','portfolio_scope','geography','status','missing_reason',
            'metric_definition_version','assumption_set_id','transform_code_version','scope')


def available_date(published):
    """Date-only documents are usable from next day 12:00 UTC (conservative)."""
    if published is None:
        return None
    if len(published)==10:
        return (datetime.fromisoformat(published).replace(tzinfo=timezone.utc)+timedelta(days=1,hours=12)).isoformat()
    return instant(published).isoformat()


def instant(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must specify timezone')
    return dt.astimezone(timezone.utc)


def scope(entity, period, portfolio='all', measurement='stock', basis='reported', netting='reported', geography='all', occupancy='all', ownership='consolidated'):
    return dict(zip(SCOPE_FIELDS,(entity,period,geography,portfolio,occupancy,measurement,basis,netting,ownership)))


def validate_observation(row, definitions, sources):
    absent = set(REQUIRED)-row.keys()
    if absent:
        raise ValueError(f'Missing fields: {sorted(absent)}')
    if row['status'] not in {'observed','derived','scenario'}:
        raise ValueError('Unknown observation status')
    if row['metric_definition_version'] not in definitions:
        raise ValueError('Unknown metric definition version')
    definition = definitions[row['metric_definition_version']]
    if definition['metric'] != row['metric'] or definition['unit'] != row['unit']:
        raise ValueError('Metric/unit differs from versioned definition')
    if set(SCOPE_FIELDS)-row['scope'].keys():
        raise ValueError('Incomplete scope')
    if row['value'] is None:
        if not row['missing_reason']:
            raise ValueError('Missing values require a reason')
    elif not isinstance(row['value'], (int,float)) or not math.isfinite(row['value']):
        raise ValueError('Observation must be finite numeric or explicit null')
    elif row['missing_reason']:
        raise ValueError('A populated observation cannot also be missing')
    if row['source_id']:
        if row['source_id'] not in sources:
            raise ValueError('Unknown source')
        if row.get('source_sha256') != sources[row['source_id']]['sha256']:
            raise ValueError('Source revision hash mismatch')
    elif row['status'] == 'observed' and row['value'] is not None:
        raise ValueError('Observed value lacks a source')
    if row['available_at'] and row['published_at']:
        pub=row['published_at']
        published=instant(pub if len(pub)>10 else pub+'T00:00:00+00:00')
        if instant(row['available_at']) < published:
            raise ValueError('Availability precedes publication')
    if row['status'] in {'derived','scenario'} and not row.get('input_observation_ids'):
        raise ValueError('Derived value lacks input lineage')
    if row['status']=='scenario' and not row['assumption_set_id']:
        raise ValueError('Scenario lacks assumption set')


def as_of(rows, cutoff):
    """Latest published revision per economic observation, never by retrieval date."""
    selected = {}; moment=instant(cutoff)
    for r in rows:
        if not r['available_at'] or instant(r['available_at']) > moment or r['period_end'] > moment.date().isoformat():
            continue
        key = (r['entity_id'],r['period_end'],r['metric'],json.dumps(r['scope'],sort_keys=True),r['metric_definition_version'])
        old = selected.get(key)
        if old is not None and instant(r['available_at'])==instant(old['available_at']) and r.get('value')!=old.get('value'):
            raise ValueError('Conflicting revisions with the same availability; resolve revision time before selection')
        if old is None or (instant(r['available_at']),r['observation_id']) > (instant(old['available_at']),old['observation_id']):
            selected[key]=r
    return list(selected.values())


def exact_arithmetic(left, right, operation, match, evidence, denominator_scope=None):
    """A tag alone is insufficient: require evidence and compatible typed scopes.

    multiply_fraction: left is an observed percent, and its denominator scope
    must exactly match the right-hand balance. divide_same_scope is for truly
    coextensive quantities; subset ratios require a separately reviewed mapping.
    """
    if match != 'exact' or not evidence:
        raise ValueError('Arithmetic requires verified exact scope match')
    if operation == 'multiply_fraction':
        if left['unit'] != 'percent' or not denominator_scope:
            raise ValueError('Percent and its denominator scope required')
        scopes = denominator_scope,right['scope']
    elif operation == 'divide_same_scope':
        if left['unit'] != right['unit']:
            raise ValueError('Unit mismatch')
        scopes = left['scope'],right['scope']
    else:
        raise ValueError('Unsupported operation')
    if any(k not in s or s[k] in (None,'unknown','unreviewed') for s in scopes for k in SCOPE_FIELDS):
        raise ValueError('Unreviewed scope dimension')
    if any(scopes[0][k] != scopes[1][k] for k in SCOPE_FIELDS):
        raise ValueError('Scope mismatch despite exact tag')
    a,b=left['value'],right['value']
    if a is None or b is None or not all(math.isfinite(v) for v in (a,b)):
        raise ValueError('Arithmetic on missing or nonfinite value')
    if operation=='multiply_fraction':
        if not 0<=a<=100:
            raise ValueError('Percent outside 0–100')
        return a/100*b
    if b==0:
        raise ValueError('Zero denominator')
    return a/b


def deposit_beta(cost_start,cost_end,rate_start,rate_end,min_policy_change_pp=0.25):
    vals=[cost_start,cost_end,rate_start,rate_end]
    if any(v is None or not math.isfinite(v) for v in vals):
        return None
    if abs(rate_end-rate_start) < min_policy_change_pp:
        return None
    return (cost_end-cost_start)/(rate_end-rate_start)


def code_manifest(prefix=''):
    """Hash executable inputs, including untracked files; never hash outputs into themselves."""
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    patch=subprocess.check_output(['git','diff','HEAD','--','scripts','config','tests','requirements.txt'],cwd=ROOT)
    files={}
    for folder in ['scripts','config','tests']:
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and path.suffix in {'.py','.json','.csv'} and '__pycache__' not in str(path):
                files[path.relative_to(ROOT).as_posix()]=digest(path.read_bytes())
    files['requirements.txt']=digest((ROOT/'requirements.txt').read_bytes())
    treehash=digest(json.dumps(files,sort_keys=True).encode())
    version=head + '+tree.' + treehash[:16]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(prefix+'executed_code.patch')).write_bytes(patch)
    write_json(OUT/(prefix+'code_manifest.json'),{'git_commit':head,'transform_code_version':version,
               'source_tree_sha256':treehash,'files':files,'patch_sha256':digest(patch),
               'note':'Exact source hashes include untracked files; commit these files to preserve execution tree.'})
    return version
