# Targeted independent R5 recheck — OBS-01 OPEN

REQ-R5-R4-SYM-OBS01-TARGETED-RECHECK-01; UTC 2026-11-16T21:23:17.533074+00:00.
Точный новый target C: **`beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe`**.
https://github.com/narrateller/REV/commit/beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe
Ветка work-r4/T-r4-force-geometry-01/6afb4750-7918-8191-8569-77b5b0c41050.
Этот запрос — следующий H, не часть target C. Не подменять target плавающим head.

Исходный R4 C b840dfd5444da2bf62483b7f4a6069d2bb255b71 / H
9433ef749df14a3bbf8ea32331e2f895fd5bf7aa. Независимый акт R5 C
4aa23509b45efc2c2c166935102ca5caa76f55e2 / H 92230cef87b71aa7e2d51fe6f21c11360331dd37:
WARNING, 2422 PASS / 4 advisory FAIL. R1 выбрал удаление четырёх refs на C
e380f6d05fe58fe5125c940ac90a151c5bba546b. Исходные reviewer oracle/акт/четыре
FAIL не исправлялись, provenance и архивы закреплены в obs01_correction/.

## Предмет точечной проверки

| Строка | Чужой ID должен отсутствовать | Собственный ID должен сохраниться |
|---|---|---|
| A-V1/datum_motion | CI-X_B_GATHER | CI-X_COLUMN_GATHER |
| A-V2/datum_motion | CI-X_B_GATHER | CI-X_COLUMN_GATHER |
| B-V1/datum_motion | CI-X_COLUMN_GATHER | CI-X_B_GATHER |
| B-V2/datum_motion | CI-X_COLUMN_GATHER | CI-X_B_GATHER |

Независимо проверить каждый исходный упорядоченный source_references минус
ровно указанный единственный ref; остальные refs/поля четырёх строк и остальные
48 строк равны исходному C. Source catalog и master unknown_inputs.json
побайтно прежние, оба gather ID остаются в мастер-каталоге. Проверить renderer
и interfaces.md/json согласованно; comparison-only флаг вместо удаления не применялся.

Проверить отсутствие новых FAIL/ограничений и сохранение 52 строк/42 полных
source states/84 RAW-null/44 full bindings/54 pinned inputs/12 исходных trees,
нагрузок/ходов/fixed-budget/CAD/активного registry. Сверить архив прежней версии
и старые evidence, дополнительную authority, детерминированный повтор, текущие
команды/exit codes/counts и CI exact C. Новый авторский 1341 PASS не является
независимым review; negative control 1337 PASS/8 FAIL — отдельная авторская
проверка старого target, не ретушь исходных четырёх R5 FAIL.

Если читать reviews из R5/R1 ветки, ожидается добавленный акт при сохранённом
старом prefix; не требовать старый полный tree hash от ветки с новым актом.
Ветка R4 ради чтения R5/R1 не сливалась, рабочие reviews не менялись.

Reviewer R5 — отдельный исполнитель вне author_sessions, не R4 под другой ролью.
Запрос не назначает reviewer, не создаёт claim/lease и не продлевает R4 срок
2026-11-17T17:44:00Z. Независимый recheck нового target **NOT_RUN**.
**OBS-01 остаётся OPEN** до фактического независимого recheck exact нового C;
автор/R1 не закрывают его этой поставкой. Сохранить отдельный акт/результаты
по четырём строкам и сохранности, точные C/H, новые PASS/FAIL/NOT_RUN и область.

§4/5/6 NOT_RUN, 42 состояния не рассчитаны, реальные данные UNKNOWN.
Прочность/устойчивость/реакции/capacity/margins/полный цикл не подтверждены.
Архитектура/ТЗ NOT_APPROVED, G1 OPEN, W02/physical READY NO-GO; новых численных
сценариев/подстановок/CAD-build/rebuild/физических расчётов/испытаний не разрешено.
Старые дефекты/семь REJECT/material history=2 не закрывать и не сбрасывать.
