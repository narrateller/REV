"""Initialize only an untouched template; refuse to reset an existing project."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import uuid
import yaml
from check_registry import UniqueLoader
from repo_support import DOMAINS, flatten, inside_file

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('sources/raw', 'requirements', 'decisions', 'process', 'drives/schematics',
           'controls', 'cad/source', 'cad/export', 'cad/build', 'cae/cases', 'cae/models',
           'cae/results', 'verification', 'manufacturing/routes', 'drawings', 'release',
           'handoffs', 'archive/tasks')


def load(path):
    return yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)


def atomic_write(path, content):
    temp = path.with_name(path.name + '.init-tmp')
    try:
        temp.write_bytes(content)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def init_project(root, project_id, equipment_name, owner, dry_run=False):
    root = Path(root).resolve()
    if not re.fullmatch(r'[A-Z][A-Z0-9_-]*', project_id) or project_id == 'UNSET':
        raise ValueError('Project ID must use uppercase letters, digits, underscore or hyphen')
    for value in (equipment_name, owner):
        if not value.strip() or any(c in value for c in '\n\r|'):
            raise ValueError('Name and owner must be nonempty single-line values without |')
    lock = root / '.init_project.lock'
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        registry_path = inside_file(root, 'params/registry.yaml')
        data = load(registry_path)
        if data.get('mode') != 'TEMPLATE' or data.get('project_id') != 'UNSET' or data.get('schema_version') != '1.1':
            raise ValueError('Initialization requires untouched TEMPLATE 1.1; PROJECT reset is forbidden')
        if any(not key.startswith('DEMO_') or p.get('scope') != 'DEMO' for key, p in flatten(data).items()):
            raise ValueError('Non-DEMO parameters found; initialization refused')
        if load(inside_file(root, 'drives/cots_catalog.yaml')).get('components') != {}:
            raise ValueError('COTS catalog already contains work')
        review_text = inside_file(root, 'reviews/cross_check_log.md').read_text(encoding='utf-8')
        if re.search(r'^record_type:\s*review\s*$', review_text, re.M):
            raise ValueError('Project review records already exist')
        for folder in FOLDERS:
            if folder in ('sources/raw', 'archive/tasks'):
                continue
            path = root / folder
            if path.exists() and (path.is_symlink() or not path.resolve().is_relative_to(root)):
                raise ValueError('External/symlink project directory')
            if path.exists() and any(p.is_file() and p.name != '.gitkeep' for p in path.rglob('*')):
                raise ValueError(f'Project work already exists in {folder}')
        state_path = inside_file(root, 'STATE.md')
        state = state_path.read_text(encoding='utf-8')
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        replacements = {
            '| project_id / изделие | UNSET / UNKNOWN |': f'| project_id / изделие | {project_id} / {equipment_name} |',
            '| Владелец и утверждающий инженер | UNSET |': f'| Владелец и утверждающий инженер | {owner}; утверждающий инженер назначается отдельно |',
            '| Режим | TEMPLATE; DEMO не является данными изделия |': '| Режим | PROJECT; исходные требования ещё не утверждены |',
            '| Последнее обновление UTC / session_id | UNSET / NONE |': f'| Последнее обновление UTC / session_id | {now} / OPERATOR_INIT |',
        }
        for old, new in replacements.items():
            if state.count(old) != 1:
                raise ValueError('STATE differs from template; refusing partial text replacement')
            state = state.replace(old, new)
        if state.count('| NOT_STARTED |') != 5 or '| NONE | NONE | NONE | NONE | NONE | NONE |' not in state:
            raise ValueError('STATE shows active work or changed gate statuses')
        clean = {'schema_version':'1.1', 'project_id':project_id, 'mode':'PROJECT',
                 'units_policy':'SI', 'domains':{name:{} for name in DOMAINS}}
        updates = {registry_path: yaml.safe_dump(clean, allow_unicode=True, sort_keys=False).encode(),
                   state_path: state.encode()}
        # Preserve examples for tests/training; they cannot feed the active registry.
        demo_paths = [root/'scripts/demo_force.py', root/'evidence/demo_force.json']
        demo_paths += list((root/'evidence/snapshots').glob('*.yaml'))
        for src in demo_paths:
            if src.exists():
                inside_file(root, str(src.relative_to(root)))
                dest = root/'examples/template_demo'/src.relative_to(root)
                if dest.exists():
                    raise ValueError(f'Demo archive already exists: {dest}')
                updates[dest] = src.read_bytes()
        updates[root/'examples/template_demo/params/registry.yaml'] = registry_path.read_bytes()
        updates[root/'examples/template_demo/STATE.md'] = state_path.read_bytes()
        updates[root/'examples/template_demo/scripts/repo_support.py'] = inside_file(root, 'scripts/repo_support.py').read_bytes()
        for path in list(updates) + [root/folder/'.gitkeep' for folder in FOLDERS] + [root/'.init_project_backup']:
            if not path.resolve().is_relative_to(root) or path.is_symlink():
                raise ValueError('External or symlink initialization target')
        print(f'Initialize {project_id}: clear active DEMO registry, set passport, preserve examples; gates unchanged')
        if dry_run:
            return
        backup = root/'.init_project_backup'/uuid.uuid4().hex
        backup.mkdir(parents=True)
        before = {p: p.read_bytes() if p.exists() else None for p in set(updates) | set(demo_paths)}
        for path, content in before.items():
            if content is not None:
                dest = backup/path.relative_to(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
        (backup/'manifest.json').write_text(json.dumps({str(p.relative_to(root)): value is not None for p,value in before.items()}, indent=2))
        lock.write_text(str(backup), encoding='utf-8')
        try:
            for path, content in updates.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(path, content)
            for path in demo_paths:
                path.unlink(missing_ok=True)
            for folder in FOLDERS:
                path = root/folder/'.gitkeep'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)
        except Exception:
            for path, content in before.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    atomic_write(path, content)
            raise
        print(f'Initialized {project_id}; backup: {backup.relative_to(root)}; no Git commit/push performed')
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        init_project(args.root, args.id, args.name, args.owner, args.dry_run)
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f'Initialization refused: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
