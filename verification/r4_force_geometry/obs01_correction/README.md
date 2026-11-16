# R5-SYM-OBS-01 — ограниченная авторская коррекция, OPEN

Исполнитель R4/session 6afb4750-7918-8191-8569-77b5b0c41050; действующий claim
PR49, срок 2026-11-17T17:44:00Z без продления. Команда/решение R1 прочитаны
на exact C e380f6d05fe58fe5125c940ac90a151c5bba546b. Исходный R5 C
4aa23509b45efc2c2c166935102ca5caa76f55e2, H 92230cef87b71aa7e2d51fe6f21c11360331dd37.
R1/R5 ветки не слиты: reviews рабочего checkout не менялись. Новый акт R5
сохранён в его exact C как добавление к прежнему prefix reviews; scope старого
checker не изменён и акт не удалён для его PASS. Provenance — authority_and_review_provenance.json.

## Дельта

- A-V1/A-V2 datum_motion: удалить только CI-X_B_GATHER; оставить CI-X_COLUMN_GATHER.
- B-V1/B-V2 datum_motion: удалить только CI-X_COLUMN_GATHER; оставить CI-X_B_GATHER.
- render_tables.py: family filter только для этих четырёх строк.
- interfaces.json: ровно четыре удаления; другие поля этих строк/оставшиеся 48
  строк равны исходному C b840dfd5444da2bf62483b7f4a6069d2bb255b71.
- interfaces.md: ровно четыре изменённые строки с тем же единственным исключением.
- source_catalog.json и исходный unknown_inputs.json побайтно сохранены; оба
  CI ID остаются в мастер-каталоге. Row-level provenance не менялся.
- 52 интерфейса, 42 полных source-state объекта, 84 RAW/null, 44 полные bindings,
  54 inputs/12 деревьев/нагрузки/ходы/fixed-budget/registry/CAD сохранены.

## Доказательства и команды

Исходные документы/генератор/валидатор и заменяемые исторические evidence
архивированы побайтно в archive_b840dfd/, archive_manifest.json и Git. Старые
evidence в symbolic_20261116/ не перезаписаны. Historical R5 2422 PASS / 4 FAIL
не ретушируются: original_R5_four_FAIL.json закрепляет исходные records и hash.
Проверка к старой таблице новыми предметными assertions дала ожидаемые 8 FAIL
(отсутствие чужого ID и ровно одно удаление для каждой из четырёх строк): это
negative_original_tables.json, не переименование четырёх reviewer FAIL.
Исправленная таблица: фактические новые counts в table_checks.json (не обещание
старого количества); команды/exit codes — author_check_commands.json.

Добавлены assertions отсутствия чужого/наличия собственного CI ID, полного
упорядоченного равенства остальных refs, неизменности других полей и остальных
48 строк. Проверяются неизменные каталоги и другие renderer outputs.
Детерминированный повтор/точный semantic diff — delta_and_repeatability.json;
fresh actual-session preflight — preflight_start/ и preflight_final/.
Текущий registry --check-git — active_registry.log/status.json; CI exact C
фиксируется после push в H, CI exact H сообщается после фактического завершения.
Это авторские проверки, не независимый recheck и не физическая верификация.

Из /workspace/REV, output paths каждый раз новые:

```bash
git fetch --no-tags origin main e380f6d05fe58fe5125c940ac90a151c5bba546b 4aa23509b45efc2c2c166935102ca5caa76f55e2 92230cef87b71aa7e2d51fe6f21c11360331dd37
.venv/bin/python verification/r4_force_geometry/preflight_20261116/verify_inputs.py --output /tmp/obs01-new-preflight
.venv/bin/python verification/r4_force_geometry/symbolic_20261116/render_tables.py
.venv/bin/python verification/r4_force_geometry/symbolic_20261116/verify_symbolic.py --output /tmp/obs01-new-checks.json
.venv/bin/python scripts/check_registry.py --check-git
git diff --check
```

Файлы claim/task/tracker/STATE/NEXT/капсулы меняют только фактический heartbeat,
состояние ожидания независимого recheck и ссылки на новый C/H/запрос. Полный
список изменений — change_manifest.json. Дополнительный provenance R1/R5 хранится
в этом correction-пакете, не в неизменном source catalog/row-level provenance.

OBS-01 OPEN, targeted R5 recheck нового exact C NOT_RUN. Исходный WARNING/§4/5/6
NOT_RUN, все реальные данные UNKNOWN, 42 состояния не рассчитаны. G1 OPEN,
W02/PLC/physical READY NO-GO, архитектура/ТЗ NOT_APPROVED. Новые размеры/сценарии/
подстановки/CAD-build/rebuild/физические расчёты/испытания не выполнялись и
не разрешены. Старые дефекты/семь REJECT/material history=2 не закрываются.
