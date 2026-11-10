"""Cross-file checks, separated from basic parameter validation."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml
from repo_support import (COMMIT_RE, ID_RE, SHA_RE, REF_RE, engineering_sha,
                          finite, flatten, inside_file, nonempty, sha256)

FENCES = re.compile(r'^```yaml\s*\n(.*?)^```\s*$', re.M | re.S)


def check_repository(data, root, params, loader, strict=False, check_git=False):
    root = Path(root).resolve()
    errors, reviews = [], {}

    def need(condition, message):
        if not condition:
            raise ValueError(message)

    def run(label, fn):
        try:
            fn()
        except (ValueError, KeyError, TypeError, AttributeError, OSError,
                OverflowError, RecursionError, yaml.YAMLError) as exc:
            errors.append(f'{label}: {exc}')

    def file(path):
        return inside_file(root, path)

    def load(path):
        return yaml.load(file(path).read_text(encoding='utf-8'), Loader=loader)

    def json_load(path):
        def unique(pairs):
            result = {}
            for key, value in pairs:
                need(key not in result, f'Duplicate JSON key: {key}')
                result[key] = value
            return result
        def invalid(value):
            raise ValueError(f'Non-finite JSON value: {value}')
        return json.loads(file(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                          parse_constant=invalid)

    def git_blob(commit, path):
        result = subprocess.run(['git', '-C', str(root), 'show', f'{commit}:{path}'], capture_output=True)
        need(result.returncode == 0, f'Git object unavailable: {commit}:{path}')
        return result.stdout

    def blocks(path, kind):
        result = []
        for block in FENCES.findall(file(path).read_text(encoding='utf-8')):
            obj = yaml.load(block, Loader=loader)
            if isinstance(obj, dict) and obj.get('record_type') == kind:
                result.append(obj)
        return result

    def refs(items, current=True):
        need(isinstance(items, list), 'parameter_refs must be a list')
        seen = set()
        for ref in items:
            need(isinstance(ref, dict), 'Invalid parameter reference')
            key = ref.get('id')
            need(isinstance(key, str) and key in params and key not in seen, f'Unknown/duplicate reference: {key}')
            seen.add(key)
            need(type(ref.get('revision')) is int and ref['revision'] > 0, 'Invalid reference revision')
            digest = ref.get('engineering_sha256')
            need(isinstance(digest, str) and SHA_RE.fullmatch(digest), f'Missing parameter hash: {key}')
            if current:
                need(ref['revision'] == params[key]['revision'], f'Obsolete reference: {key}')
                need(params[key]['validity'] == 'CURRENT', f'STALE reference: {key}')
                need(digest == engineering_sha(params[key]), f'Changed parameter definition: {key}')

    def artifacts(items, current=True, commit=None):
        need(isinstance(items, list) and bool(items), 'Artifact manifest required')
        names = set()
        for item in items:
            need(isinstance(item, dict), 'Invalid artifact')
            name, digest = item.get('path'), item.get('sha256')
            path = file(name)
            need(name not in names, f'Duplicate artifact: {name}')
            names.add(name)
            need(isinstance(digest, str) and SHA_RE.fullmatch(digest), f'Invalid artifact hash: {name}')
            if current:
                need(sha256(path) == digest, f'Artifact hash mismatch: {name}')
            if check_git and commit:
                blob = git_blob(commit, name)
                # An LFS-tracked Git blob is a pointer, not the materialized file.
                # Compare its declared object hash; `file` and the current
                # worktree SHA256 check above still require actual file bytes.
                pointer = re.fullmatch(
                    rb'version https://git-lfs\.github\.com/spec/v1\r?\n'
                    rb'oid sha256:([a-f0-9]{64})\r?\nsize ([0-9]+)\r?\n?', blob)
                recorded = pointer.group(1).decode('ascii') if pointer else hashlib.sha256(blob).hexdigest()
                need(recorded == digest,
                     f'Artifact differs from commit: {name}')

    def text_ref(text):
        m = REF_RE.fullmatch(text) if isinstance(text, str) else None
        need(m is not None, 'Expected [ID@revision] reference')
        key, revision = m.group(1), int(m.group(2))
        need(key in params, f'Unknown parameter reference: {key}')
        need(params[key]['revision'] == revision, f'Outdated Markdown reference: {key}')
        need(params[key]['validity'] == 'CURRENT', f'STALE Markdown reference: {key}')
        return key

    def calculation(key, p):
        calc = p['calculation']
        need(isinstance(calc, dict), 'Invalid calculation')
        script, output = file(calc['script']), file(calc['output'])
        need(calc['output'] in p['evidence'], 'Output absent from evidence list')
        ev = json_load(calc['output'])
        need(isinstance(ev, dict) and ev.get('schema_version') == '1.1', 'Evidence schema_version must be 1.1')
        current = p['validity'] == 'CURRENT'
        digest = ev.get('script_sha256')
        need(isinstance(digest, str) and SHA_RE.fullmatch(digest), 'script_sha256 required')
        if current:
            need(digest == sha256(script), 'script_sha256 mismatch')
        snapshot = file(ev.get('registry_snapshot'))
        need(ev.get('registry_sha256') == sha256(snapshot), 'registry_sha256 mismatch')
        snap_data = load(ev['registry_snapshot'])
        need(snap_data.get('project_id') == data.get('project_id'), 'Snapshot project mismatch')
        snap = flatten(snap_data)
        inputs, outputs = ev.get('inputs'), ev.get('outputs')
        refs(inputs, current); refs(outputs, current)
        need({x['id'] for x in inputs} == {x['id'] for x in p['depends_on']}, 'Input dependency set mismatch')
        need(key in {x['id'] for x in outputs}, 'Output parameter missing from manifest')
        for ref in inputs + outputs:
            old = snap[ref['id']]
            need(ref['revision'] == old['revision'] and ref['engineering_sha256'] == engineering_sha(old),
                 'Snapshot parameter definition mismatch')
            need(finite(ref.get('value')) and ref['value'] == old['value'] and ref.get('unit') == old['unit'],
                 'Evidence value/unit mismatch')
        codes = calc.get('code_files')
        need(isinstance(codes, list) and calc['script'] in codes, 'code_files must include main script')
        artifacts(ev.get('code_files'), current)
        need(set(codes) == {x['path'] for x in ev['code_files']}, 'Code file set mismatch')
        need(isinstance(ev.get('environment'), dict) and bool(ev['environment']), 'Environment missing')
        if ev.get('artifacts'):
            artifacts(ev['artifacts'], current)

    def review(r):
        rid = r['review_id']
        need(r.get('verdict') in ('PASS', 'WARNING', 'REJECT_WITH_BLOCKER'), 'Invalid verdict')
        need(r.get('validity') in ('CURRENT', 'STALE'), 'Invalid review validity')
        current = r['validity'] == 'CURRENT'
        author_sessions, reviewer = r.get('author_sessions'), r.get('reviewer')
        need(isinstance(author_sessions, list) and bool(author_sessions) and all(nonempty(s) for s in author_sessions), 'Missing review authors')
        need(isinstance(reviewer, dict) and reviewer.get('role') in ('R1','R2','R3','R4','R5','R6')
             and nonempty(reviewer.get('session_id')), 'Missing reviewer')
        need(reviewer['session_id'] not in author_sessions, 'Self-verification')
        need(nonempty(r.get('scope')) and nonempty(r.get('independence_basis')), 'Scope/independence basis required')
        commit = r.get('reviewed_commit')
        need(isinstance(commit, str) and COMMIT_RE.fullmatch(commit), 'Invalid reviewed_commit')
        refs(r.get('parameter_refs'), current)
        artifacts(r.get('artifacts'), current, commit)
        checks = r.get('checks')
        need(isinstance(checks, list) and bool(checks), 'Checks required')
        for c in checks:
            need(isinstance(c, dict) and all(nonempty(c.get(k)) for k in ('method','expected','observed','reasoning')),
                 'Incomplete check')
            need(c.get('result') in ('PASS','FAIL','NOT_APPLICABLE','NOT_RUN'), 'Invalid check result')
            if r['verdict'] == 'PASS':
                need(c['result'] in ('PASS','NOT_APPLICABLE'), 'PASS with failed/unrun check')
        if check_git:
            baseline = flatten(yaml.load(git_blob(commit, 'params/registry.yaml'), Loader=loader))
            for ref in r['parameter_refs']:
                need(ref['id'] in baseline and engineering_sha(baseline[ref['id']]) == ref['engineering_sha256'],
                     'Parameter differs from reviewed commit')

    def load_reviews():
        for r in blocks('reviews/cross_check_log.md', 'review'):
            rid = r.get('review_id')
            need(isinstance(rid, str) and ID_RE.fullmatch(rid), 'Invalid review_id')
            need(rid not in reviews, f'Duplicate review_id: {rid}')
            reviews[rid] = r
            run(rid, lambda obj=r: review(obj))

    def decision(key, p):
        did = p['baseline_id']
        need(isinstance(did, str) and ID_RE.fullmatch(did), 'Invalid baseline_id')
        ds = blocks(f'decisions/{did}.md', 'decision')
        need(len(ds) == 1, 'Exactly one decision record required')
        d = ds[0]
        need(d.get('decision_id') == did, 'Decision ID mismatch')
        need(d.get('status') == 'APPROVED' and d.get('blocking_issues_remaining') == [],
             'LOCKED requires APPROVED without blockers')
        need(d.get('gate') in ('G1','G2','G3','G4','G5'), 'Invalid gate')
        need(nonempty(d.get('approved_by')) and nonempty(d.get('authorization_evidence')) and nonempty(d.get('scope')),
             'Approver, authorization evidence and scope required')
        if d['gate'] in ('G1','G4','G5'):
            need(d.get('approver_kind') == 'HUMAN', 'Human approval required')
        timestamp = d.get('approved_at_utc')
        need(isinstance(timestamp, str) and timestamp.endswith('Z'), 'UTC approval timestamp required')
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        commit = d.get('baseline_commit')
        need(isinstance(commit, str) and COMMIT_RE.fullmatch(commit), 'Invalid baseline commit')
        refs(d.get('parameter_refs'), p['validity'] == 'CURRENT')
        need(any(x['id'] == key and x['revision'] == p['revision'] for x in d['parameter_refs']), 'Locked parameter not covered')
        need(isinstance(d.get('review_ids'), list) and p['verifier']['review_id'] in d['review_ids'], 'Verification review missing')
        for rid in d['review_ids']:
            need(rid in reviews and reviews[rid].get('verdict') == 'PASS', 'Missing or non-PASS decision review')
            if p['validity'] == 'CURRENT':
                need(reviews[rid].get('validity') == 'CURRENT', 'STALE decision review')
        artifacts(d.get('artifacts'), p['validity'] == 'CURRENT', commit)
        if check_git:
            baseline = flatten(yaml.load(git_blob(commit, 'params/registry.yaml'), Loader=loader))
            for ref in d['parameter_refs']:
                need(ref['id'] in baseline and engineering_sha(baseline[ref['id']]) == ref['engineering_sha256'],
                     'Parameter differs from baseline commit')

    def verification(key, p):
        v = p['verifier']
        need(isinstance(v, dict) and nonempty(v.get('review_id')), 'Verifier review_id required')
        r = reviews.get(v['review_id'])
        need(r is not None, 'Exact review_id not found')
        need(r.get('verdict') == 'PASS', 'Verification requires PASS')
        if p['validity'] == 'CURRENT':
            need(r.get('validity') == 'CURRENT', 'STALE verification review')
        need(v.get('role') == r['reviewer']['role'] and v.get('session_id') == r['reviewer']['session_id']
             and v.get('scope') == r['scope'], 'Verifier/review identity or scope mismatch')
        need(v['session_id'] not in p['author_sessions'], 'Self-verification by coauthor')
        need(set(p['author_sessions']) <= set(r['author_sessions']), 'Review omits coauthors')
        need(any(x['id'] == key and x['revision'] == p['revision'] for x in r['parameter_refs']), 'Review does not cover parameter revision')
        need(set(p['evidence']) <= {a['path'] for a in r.get('artifacts', [])}, 'Review does not cover parameter evidence')
        if p['lifecycle'] == 'LOCKED':
            decision(key, p)

    def markdown():
        for path in root.rglob('*.md'):
            rel = path.relative_to(root)
            if {'.git','.venv','venv','node_modules','__pycache__','.init_project_backup'}.intersection(rel.parts):
                continue
            if rel.parts[0] in ('templates', 'archive', 'examples') or rel.parts[:2] in (('tests', 'fixtures'), ('sources', 'raw')):
                continue
            text = file(str(rel)).read_text(encoding='utf-8')
            for match in REF_RE.finditer(text):
                run(f'{rel}:{text[:match.start()].count(chr(10))+1}', lambda m=match: text_ref(m.group(0)))

    def fits():
        for key, p in params.items():
            tol = p['tolerance']
            if isinstance(tol, dict) and tol['kind'] == 'fit':
                text_ref(tol['nominal_ref'])
                for ref in tol['limits_refs']:
                    text_ref(ref)

    def cots():
        catalog = load('drives/cots_catalog.yaml')
        need(isinstance(catalog, dict) and catalog.get('schema_version') == '1.1', 'COTS schema_version')
        need(isinstance(catalog.get('components'), dict), 'COTS components mapping required')
        for cid, c in catalog['components'].items():
            need(isinstance(c, dict), f'{cid}: invalid COTS record')
            need(c.get('status') in ('CANDIDATE','SELECTED','APPROVED_FOR_LAYOUT'), f'{cid}: invalid status')
            need(c.get('owner_role') in ('R1','R2','R3','R4','R5','R6'), f'{cid}: owner_role required')
            interfaces, ratings = c.get('interface_parameters'), c.get('rating_parameters')
            need(isinstance(interfaces, dict) and isinstance(ratings, dict), f'{cid}: parameter mappings required')
            covered_params = {text_ref(ref) for ref in list(interfaces.values()) + list(ratings.values())}
            if c['status'] == 'APPROVED_FOR_LAYOUT':
                for field in ('manufacturer','model','variant','catalog_revision','source_locator','coordinate_system'):
                    need(nonempty(c.get(field)), f'{cid}: missing {field}')
                need(c.get('source_sha256') == sha256(file(c.get('source_file'))), f'{cid}: catalog hash mismatch')
                required = c.get('required_interfaces')
                need(isinstance(required, list) and bool(required) and all(k in interfaces for k in required),
                     f'{cid}: incomplete required interfaces')
                need(c.get('unresolved_items') == [], f'{cid}: unresolved interfaces')
                r = reviews.get(c.get('review_id'))
                need(r is not None and r.get('verdict') == 'PASS' and r.get('validity') == 'CURRENT', f'{cid}: current PASS review required')
                need(covered_params <= {x['id'] for x in r['parameter_refs']}, f'{cid}: incomplete review coverage')
                need(any(a.get('path') == c.get('source_file') and a.get('sha256') == c.get('source_sha256') for a in r.get('artifacts', [])),
                     f'{cid}: source absent from review artifacts')
                for key in covered_params:
                    need(params[key]['lifecycle'] in ('VERIFIED','LOCKED') and params[key]['scope'] != 'DEMO',
                         f'{cid}: unverified or DEMO interface/rating')

    run('reviews', load_reviews)
    for key, p in params.items():
        if p['calculation'] is not None:
            run(key, lambda k=key, e=p: calculation(k, e))
        if p['lifecycle'] in ('VERIFIED','LOCKED'):
            run(key, lambda k=key, e=p: verification(k, e))
    run('Markdown', markdown)
    run('fits', fits)
    run('COTS', cots)
    return errors
