"""Interactive project launcher; the template is only read, never initialized in place."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from init_project import init_project

TEMPLATE = Path(__file__).resolve().parents[1]
SCHEMA = '1.0'
IGNORE = shutil.ignore_patterns('.git', '__pycache__', '.venv', 'venv',
                                 '.init_project_backup', '.init_project.lock', '*.pyc')


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def input_files(directory):
    source = Path(directory).expanduser().resolve(strict=True)
    if not source.is_dir():
        raise ValueError('Путь исходных материалов должен указывать на каталог')
    files = []
    for base, dirs, names in os.walk(source, followlinks=False):
        parent = Path(base)
        for item in dirs + names:
            if (parent / item).is_symlink():
                raise ValueError('Символические ссылки в исходных материалах не поддерживаются')
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for name in sorted(names):
            p = parent / name
            if not p.is_file():
                raise ValueError('Обнаружен объект, не являющийся обычным файлом')
            files.append(p)
    return source, files


def create_project(template, destination, project_id, equipment, operator, source_dir=None):
    template = Path(template).resolve(strict=True)
    target = Path(destination).expanduser().resolve()
    if target == template or target.is_relative_to(template) or template.is_relative_to(target):
        raise ValueError('Проект и исходный шаблон должны находиться в разных каталогах')
    if target.exists():
        raise FileExistsError('Целевой каталог уже существует; перезапись запрещена')
    source, files = (None, []) if not source_dir else input_files(source_dir)
    if source and (target == source or target.is_relative_to(source) or source.is_relative_to(target)):
        raise ValueError('Каталог исходных материалов и целевой каталог проекта пересекаются')
    if not (template/'AGENT_PROTOCOL.md').is_file() or not (template/'scripts/init_project.py').is_file():
        raise ValueError('Не найден полный каталог шаблона')
    target.parent.mkdir(parents=True, exist_ok=True)
    # If interrupted, the separate partial directory remains visible for inspection.
    shutil.copytree(template, target, ignore=IGNORE, symlinks=False)
    init_project(target, project_id, equipment, operator)
    raw = target/'sources/raw'
    materials = []
    for path in files:
        rel = path.relative_to(source)
        out = raw/rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            raise FileExistsError(f'Исходный файл уже существует: {rel}')
        shutil.copyfile(path, out)
        digest = checksum(out)
        if digest != checksum(path):
            raise ValueError(f'Файл изменился при копировании: {rel}')
        materials.append({'path': out.relative_to(target).as_posix(), 'sha256': digest,
                          'size_bytes': out.stat().st_size})
    (target/'project').mkdir(exist_ok=True)
    manifest = {'schema_version':SCHEMA, 'project_id':project_id,
                'created_at_utc':now(), 'template_version':'1.2.1-candidate',
                'sources_status':'PRESENT_UNREVIEWED' if materials else 'MISSING',
                'sources':materials,
                'model_access_status':'NOT_VERIFIED',
                'note':'Наличие файлов не подтверждает их пригодность и не открывает G1.'}
    (target/'project/source_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (target/'project/access_challenge.txt').write_text(secrets.token_hex(16)+'\n', encoding='utf-8')
    return target


def add_sources(project, source_dir):
    root = Path(project).resolve(strict=True)
    path = root/'project/source_manifest.json'
    if not path.is_file():
        raise ValueError('Манифест проекта отсутствует; подготовьте проект через консоль')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    source, files = input_files(source_dir)
    raw = (root/'sources/raw').resolve()
    if not raw.is_relative_to(root) or raw == source or raw.is_relative_to(source) or source.is_relative_to(raw):
        raise ValueError('Исходный и целевой каталоги пересекаются или находятся вне проекта')
    if not files:
        raise ValueError('В каталоге нет файлов')
    entries = manifest.get('sources')
    if not isinstance(entries, list):
        raise ValueError('Некорректный манифест исходных материалов')
    names = {e['path'] for e in entries}
    plan = []
    for src in files:
        dest = raw/src.relative_to(source)
        if not dest.resolve().is_relative_to(raw) or dest.exists():
            raise FileExistsError(f'Конфликт пути, перезапись запрещена: {dest.name}')
        name = dest.relative_to(root).as_posix()
        if name in names:
            raise ValueError(f'Файл уже зарегистрирован: {name}')
        plan.append((src, dest, name))
    copied = []
    try:
        for src, dest, name in plan:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation avoids replacing a file created after preflight.
            with src.open('rb') as reader, dest.open('xb') as writer:
                copied.append(dest)
                shutil.copyfileobj(reader, writer)
            digest = checksum(dest)
            if digest != checksum(src):
                raise ValueError(f'Файл изменился при копировании: {name}')
            entries.append({'path':name,'sha256':digest,'size_bytes':dest.stat().st_size})
        manifest['sources_status'] = 'PRESENT_UNREVIEWED'
        manifest['updated_at_utc'] = now()
        temp = path.with_name(path.name+'.init-tmp')
        temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        os.replace(temp, path)
    except Exception:
        for dest in copied:
            dest.unlink(missing_ok=True)
        raise
    print('Добавлено исходных файлов:', len(plan))


def local_checks(project):
    root = Path(project).resolve(strict=True)
    problems = []
    path = root/'project/source_manifest.json'
    if not path.is_file():
        return ['MISSING: project/source_manifest.json'], None
    manifest = json.loads(path.read_text(encoding='utf-8'))
    for required in ('AGENTS.md','AGENT_PROTOCOL.md','STATE.md','NEXT_MODEL.md',
                     'project/access_challenge.txt'):
        if not (root/required).is_file():
            problems.append(f'MISSING: обязательный файл проекта {required}')
    entries = manifest.get('sources', [])
    if not isinstance(entries, list) or not entries:
        problems.append('MISSING: исходные материалы не зарегистрированы')
        entries = []
    names = set()
    for entry in entries:
        name = entry.get('path')
        if not isinstance(name, str) or name in names:
            problems.append('ERROR: некорректная/повторная запись исходного файла')
            continue
        names.add(name)
        path = (root/name).resolve()
        if not path.is_relative_to((root/'sources/raw').resolve()) or not path.is_file():
            problems.append(f'ERROR: исходный файл недоступен: {name}')
        elif checksum(path) != entry.get('sha256') or path.stat().st_size != entry.get('size_bytes'):
            problems.append(f'CHANGED: исходный файл: {name}')
    actual = {p.relative_to(root).as_posix() for p in (root/'sources/raw').rglob('*')
              if p.is_file() and p.name != '.gitkeep'} if (root/'sources/raw').exists() else set()
    for unregistered in sorted(actual - names):
        problems.append(f'UNREGISTERED: {unregistered}')
    result = subprocess.run([sys.executable, str(root/'scripts/check_registry.py')],
                            cwd=root, text=True, capture_output=True, check=False)
    if result.returncode:
        problems.append('ERROR: проверка реестра не пройдена; запустите scripts/check_registry.py')
    return problems, manifest


def doctor(project, remote=None):
    root = Path(project).resolve(strict=True)
    problems, manifest = local_checks(root)
    print('ПРОВЕРКА ПРОЕКТА')
    if manifest:
        print('Проект:', manifest.get('project_id', 'UNKNOWN'))
        print('Исходные материалы:', len(manifest.get('sources', [])),
              '(наличие/хэш проверены; содержание ещё не оценено)')
    for item in problems:
        print(item)
    if not problems:
        print('Локальные файлы и реестр: структурная проверка пройдена')
    if remote:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_.-]+', remote):
            problems.append('ERROR: неверный адрес OWNER/REPO')
        else:
            try:
                identity = gh_identity()
                result = subprocess.run(['gh','api','--hostname','github.com','repos/'+remote],
                                        capture_output=True,text=True,check=False)
                if result.returncode:
                    print('GitHub UNKNOWN: не удалось прочитать сведения о репозитории текущим аккаунтом.')
                    problems.append('UNKNOWN: GitHub repo metadata')
                else:
                    meta = json.loads(result.stdout)
                    print('GitHub оператор:', identity, 'репозиторий:', meta.get('full_name'),
                          'видимость:', 'private' if meta.get('private') else 'public',
                          'права:', meta.get('permissions', {}).get('push', 'UNKNOWN'))
                    if str(meta.get('full_name', '')).lower() != remote.lower():
                        problems.append('ERROR: GitHub вернул другой адрес репозитория')
            except (ValueError, RuntimeError, OSError) as exc:
                print('GitHub UNKNOWN:', exc)
                problems.append('UNKNOWN: операторский GitHub-доступ')
    else:
        print('GitHub: адрес не задан; публикация и доступ оператора не проверены.')
    receipts = sorted((root/'project/access_receipts').glob('*.json')) if (root/'project/access_receipts').is_dir() else []
    if not receipts:
        print('Доступ моделей: NOT_VERIFIED; подтверждения сессий отсутствуют.')
    for receipt in receipts:
        try:
            r = json.loads(receipt.read_text(encoding='utf-8'))
            print('Доступ (заявление оператора):', r['model_label'], r['session_id'],
                  'чтение:', r['read_status'], 'запись:', r['write_status'], 'время:', r['recorded_at_utc'])
        except (ValueError, KeyError, OSError):
            print('ERROR: повреждённое подтверждение доступа:', receipt.name)
            problems.append('Повреждённое подтверждение доступа')
    print('Старые подтверждения не доказывают актуальные права. Пароли и токены сюда не вносятся.')
    print('Допуск к исследованию: пользователь оценивает доступ и исходные материалы; ворота G1 не закрыты.')
    return 1 if problems else 0


def record_access(project, model, session, commit, challenge, probe_ref=None):
    root = Path(project).resolve(strict=True)
    if not model.strip() or any(c in model for c in '\n\r'):
        raise ValueError('Нужно короткое однострочное имя модели')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', session):
        raise ValueError('Некорректный идентификатор сессии')
    if not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', commit):
        raise ValueError('Нужен полный SHA коммита, прочитанного моделью')
    actual = (root/'project/access_challenge.txt').read_text(encoding='utf-8').strip()
    if not actual or challenge.strip() != actual:
        raise ValueError('Ответ модели не совпадает с challenge проекта')
    def git_show(revision, path):
        result = subprocess.run(['git','-C',str(root),'show',f'{revision}:{path}'],
                                capture_output=True,text=True,check=False)
        if result.returncode:
            raise ValueError('Git-объект не найден локально; получите нужную ветку из origin')
        return result.stdout.strip()
    if git_show(commit, 'project/access_challenge.txt') != actual:
        raise ValueError('Challenge указанного коммита не совпадает с текущим проектом')
    write_status = 'NOT_VERIFIED'
    if probe_ref:
        expected_ref = 'refs/remotes/origin/access/'+session
        if probe_ref != expected_ref:
            raise ValueError('Ожидается refs/remotes/origin/access/<session_id>')
        if git_show(probe_ref, 'project/access_probes/'+session+'.md') != actual:
            raise ValueError('Содержимое проверочной записи не совпадает с challenge')
        write_status = 'REMOTE_TRACKING_REF_OBSERVED_LOCALLY'
    receipts = root/'project/access_receipts'
    if receipts.is_symlink() or not receipts.resolve().is_relative_to(root):
        raise ValueError('Каталог подтверждений находится вне проекта')
    receipts.mkdir(exist_ok=True)
    path = receipts/(session+'.json')
    record = {'schema_version':SCHEMA,'model_label':model,'session_id':session,
              'reported_read_commit':commit,'read_status':'OPERATOR_REPORTED_RESPONSE_MATCHED_GIT',
              'write_status':write_status,'probe_ref':probe_ref,'recorded_at_utc':now(),
              'note':'Подтверждение оператора не устанавливает личность модели и не гарантирует текущий доступ.'}
    with path.open('x', encoding='utf-8') as out:
        json.dump(record,out,ensure_ascii=False,indent=2)
        out.write('\n')
    print('Записано подтверждение сессии:', session)


def next_message(repo=None, branch='main'):
    text = 'Войди в курс дел и текущий статус проекта.'
    if repo:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Ожидается адрес OWNER/REPO')
        if not re.fullmatch(r'[A-Za-z0-9._/-]+', branch) or '..' in branch or branch.startswith('-'):
            raise ValueError('Некорректная ветка')
        text = f'Репозиторий: https://github.com/{repo}; ветка: {branch}.\n'+text
    return text


def gh_identity():
    if shutil.which('gh') is None:
        raise RuntimeError('GitHub CLI не найден. Установите gh и выполните gh auth login.')
    # The actual API identity accounts for GH_TOKEN/GITHUB_TOKEN overriding gh's configured account.
    result = subprocess.run(['gh','api','--hostname','github.com','user','--jq','.login'],
                            text=True, capture_output=True, check=False)
    login = result.stdout.strip()
    if result.returncode or not re.fullmatch(r'[A-Za-z0-9-]+', login):
        raise RuntimeError('Не удалось подтвердить действующий GitHub-аккаунт. Проверьте gh auth status.')
    return login


def publish(project, owner_repo, visibility, expected_user, confirmation):
    root = Path(project).resolve(strict=True)
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_.-]+', owner_repo):
        raise ValueError('Ожидается адрес OWNER/REPO на github.com')
    if visibility not in ('private','public'):
        raise ValueError('Видимость должна быть private или public')
    if confirmation != f'CREATE {owner_repo}':
        raise ValueError('Подтверждение создания не совпадает с адресом')
    identity = gh_identity()
    if identity.lower() != expected_user.lower():
        raise RuntimeError('Действующий GitHub-аккаунт не совпадает с указанным; создание отменено')
    problems, _ = local_checks(root)
    if problems:
        raise RuntimeError('Локальная проверка выявила проблемы; сначала выполните doctor')
    if (root/'.git').exists():
        raise RuntimeError('Git уже инициализирован: публикация через консоль запрещена; используйте обычный Git/PR')
    if shutil.which('git') is None:
        raise RuntimeError('Git не найден')
    if shutil.which('git-lfs') is None:
        raise RuntimeError('Git LFS не найден: материалы проекта могут содержать файлы LFS')
    for args in (['git','init','-b','main'], ['git','lfs','install','--local'],
                 ['git','add','.'], ['git','commit','-m','chore: initialize engineering project']):
        result = subprocess.run(args, cwd=root, check=False)
        if result.returncode:
            raise RuntimeError('Не удалось подготовить локальный Git; данные сохранены для диагностики')
    # Remote creation/push can partially succeed; never automatically retry or delete the remote.
    cmd = ['gh','repo','create',owner_repo,'--'+visibility,'--source',str(root),'--remote','origin','--push']
    result = subprocess.run(cmd, cwd=root, check=False)
    if result.returncode:
        raise RuntimeError('Создание/отправка не завершены. Проверьте GitHub и локальный Git перед повтором; удаление не выполнялось.')
    print('Репозиторий создан:', 'https://github.com/'+owner_repo)
    print('Доступ моделей, реальные настройки защиты и CI ещё необходимо проверить.')


def prompt(label, default=None):
    answer = input(label + (f' [{default}]' if default else '') + ': ').strip()
    return answer or default or ''


def interactive():
    print('Инженерный шаблон: новый проект в отдельном каталоге')
    print('1 — подготовить проект; 2 — проверить проект; 3 — опубликовать проект; 4 — добавить источники; 5 — сообщение модели')
    action = prompt('Выберите действие', '1')
    if action == '1':
        destination = prompt('Новый локальный каталог проекта')
        pid = prompt('Код проекта (заглавные латинские буквы/цифры/дефис)')
        equipment = prompt('Название и тип изделия')
        operator = prompt('Имя оператора')
        source = prompt('Каталог исходных материалов (можно оставить пустым)')
        root = create_project(TEMPLATE, destination, pid, equipment, operator, source or None)
        print('Проект подготовлен:', root)
        doctor(root)
        print('После размещения в GitHub подключите модель и скажите: «Войди в курс дел и текущий статус проекта».')
    elif action == '2':
        root = prompt('Локальный каталог проекта')
        doctor(root, prompt('GitHub OWNER/REPO для проверки доступа оператора (можно пропустить)') or None)
    elif action == '3':
        root = prompt('Локальный каталог подготовленного проекта')
        owner_repo = prompt('Аккаунт или организация и имя репозитория OWNER/REPO')
        visibility = prompt('Видимость: private или public', 'private')
        identity = gh_identity()
        print('Фактический аккаунт GitHub CLI:', identity)
        expected = prompt('Введите имя этого аккаунта для проверки')
        print('Будет создан новый репозиторий', owner_repo, 'с видимостью', visibility)
        confirmation = prompt('Для создания введите CREATE '+owner_repo)
        publish(root, owner_repo, visibility, expected, confirmation)
    elif action == '4':
        root = prompt('Локальный каталог проекта')
        add_sources(root, prompt('Каталог новых исходных материалов'))
        doctor(root)
    elif action == '5':
        repo = prompt('GitHub OWNER/REPO (пусто, если репозиторий уже выбран в среде)')
        branch = prompt('Ветка', 'main') if repo else 'main'
        print(next_message(repo or None, branch))
    else:
        raise ValueError('Неизвестное действие')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action')
    create = sub.add_parser('prepare')
    create.add_argument('--destination', required=True)
    create.add_argument('--id', required=True)
    create.add_argument('--name', required=True)
    create.add_argument('--operator', required=True)
    create.add_argument('--sources')
    check = sub.add_parser('doctor'); check.add_argument('--project', required=True); check.add_argument('--remote')
    add = sub.add_parser('add-sources'); add.add_argument('--project', required=True); add.add_argument('--sources', required=True)
    access = sub.add_parser('record-access')
    access.add_argument('--project', required=True); access.add_argument('--model', required=True)
    access.add_argument('--session', required=True); access.add_argument('--commit', required=True)
    access.add_argument('--challenge', required=True); access.add_argument('--probe-ref')
    message = sub.add_parser('message'); message.add_argument('--repo'); message.add_argument('--branch', default='main')
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            root = create_project(TEMPLATE, args.destination, args.id, args.name, args.operator, args.sources)
            print('Создана локальная копия:', root)
            return doctor(root)
        if args.action == 'doctor':
            return doctor(args.project, args.remote)
        if args.action == 'add-sources':
            add_sources(args.project, args.sources)
            return doctor(args.project)
        if args.action == 'record-access':
            record_access(args.project, args.model, args.session, args.commit, args.challenge, args.probe_ref)
            return doctor(args.project)
        if args.action == 'message':
            print(next_message(args.repo, args.branch))
            return 0
        interactive()
        return 0
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError, KeyboardInterrupt) as exc:
        print('Операция не завершена:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
