# Условное сравнение силовых путей R3

Claim принят PR #47, merge 1dce280bf4c6a790ef0ace10a757fe0a72148b5f;
owner r3-force-path-20261114, lease до 2026-11-16T18:56:30Z без продления.
Предварительные поля предложения нормализованы по факту merge и прямому
поручению продолжить; история сохранена. [Preflight](preflight.json),
[входной аудит WARNING](input_audit.md), [результат](report.md),
[свободные тела/формулы](free_bodies.md), [26 численных величин](calculated.md),
[42 условия состояний](state_matrix.json), [запрос R5](review_request.md).

Из `/workspace/REV`, Python 3.12 / PyYAML 6.0.3:

```bash
.venv/bin/python -m unittest discover -s verification/r3_force_path/analysis -p 'test_*.py' -v
.venv/bin/python verification/r3_force_path/analysis/compare.py
.venv/bin/python verification/r3_force_path/analysis/compare.py --validate-case
.venv/bin/python scripts/check_registry.py --check-git
git diff --check
```

Первый вызов compare без флагов воспроизводит и побайтно сверяет шесть сохранённых
расчётных артефактов без записи. `--validate-case` дополнительно передаёт отдельный
реестр существующему validate(..., repo_root, check_git=True). Проверка активного
реестра последней Python-командой выполняется отдельно: она не проверяет новые
case IDs и не заменяет проверку case. Полная согласованность может занять минуты.
Среда записана в results_A/B.json; другой интерпретатор/версия YAML может потребовать
отдельной сверки чисел/метаданных вместо побайтного сравнения окружения.

Явный `--write` создаёт только новые файлы analysis/ при принятом действующем
claim автора; root registry/CAD/source evidence не пишет. Для проверки R5 запись
не требуется. Тестовые числа — математические fixtures, не новые сценарии REV.

`analysis/params/registry.yaml` — расчётный подреестр: исходные определения
корневого реестра сохранены, добавлены новые CALCULATED коэффициенты и RAW/null
пробелы. Он служит snapshot для results_A/B.json и не является обновлением
активных проектных/конструкторских входов. Его новые ID пока используются только
в данном условном исследовании; перенос в активные данные требует отдельной
приёмки/регистрации. В Markdown они приведены как обычные идентификаторы, а не
ссылки на отсутствующие новые параметры активного реестра.

В manifests: code/input/output hashes, единицы, revisions, engineering_sha256,
snapshot hash, Python/YAML environment. baseline_snapshot.json сохраняет все
44 привязки. params/registry.yaml, исходные loads/strokes, BASE_A/B fixed-budget,
CAD, R4 interface/helper и прежние акты остаются неизменными.

Получены условные компоненты спроса, а не доказанные допустимые нагрузки.
Неизвестные плечи/опоры/материал/сечения/ресурсы не заменены нулём. G1 OPEN,
W02/physical READY NO-GO; архитектура/ТЗ/оборудование не утверждены.
