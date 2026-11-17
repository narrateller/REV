# R1 — рабочий пакет критериев,метрологии и безопасности G1

Это содержательное продолжение плана после PR54,а не очередная квитанция.
Координатор/автор документальной поставки R1 actual session
6afb300b-1540-8191-a5c4-be1a684c20e0. Task T-r1-requirements-draft-01 уже принят
в main; исходный deadline2026-11-18T01:58:30.990734+00:00 не продлён. Новый claim,
роль или инженерный этап не создаются. Новые предложения — DRAFT,NOT_APPROVED.

## Что подготовлено

- criterion_cards.json/md:22 карточки всех REQ/VAL с конкретным наблюдением,
  будущим PASS-предикатом, обязательными evidence fields, source locators,
  классификацией numeric/mixed или objective completeness, недостающими
  определениями и реальным владельцем документальной подготовки R1.
- metrology_plan.json/md:22 строки программы,11 классов измерительных/документальных
  каналов, статьи будущего бюджета неопределённости, контекст/калибровки/синхронизация.
  Конкретные приборы/методики/диапазоны/точность/число повторов UNKNOWN.
- evaluation_rules.json и evidence_schema.json: предложенный порядок NOT_RUN/
  FAIL/INDETERMINATE/PASS и пустая схема many-to-many evidence. Неизвестные значения
  не заменяются нулём; известное нарушение/неполнота не удаляются. Измерений нет.
- hazard_to_evidence.json/safety_plan.md: все существующие H01–H20 сохранены и
  связаны с REQ/VAL, предложенными условиями безопасного состояния и доказательствами.
  PL/SIL/риск/эффективность/полнота не назначены и не подтверждены.
- normative_applicability_plan.json/normative_plan.md: N01–N06 из существующего
  реестра и старого R5 recheck,с сохранением исторической прочитанной области.
  Актуальная консолидированная редакция/обязательность/применимость UNKNOWN;
  нового юридического заключения и проверки полного текста нет.
- source_actions.json/md:3 точных вопроса и closure evidence для SOURCE-POWER,
  SOURCE-PRESSURE-UNIT, SOURCE-MOISTURE-BASIS. R1 владеет desk-check/подготовкой
  вопросов,внешние сообщения не отправлены. Варианты: первичное разъяснение либо
  отдельная обоснованная ревизия собственного критерия с independent review и
  решением пользователя. Ни единица/база,ни power budget не исправлены догадкой.
- execution_board.md: явная текущая очередь R1/доставленные drafts/следующий
  независимый review и человеческое утверждение,без ожидания нового руководителя.

## Проверка источников и область

search_sources.py выполнил pdftotext-поиск4 исходных PDF. Текст доступен на3 страницах
BP500,39 E55,41 WEIMA; у ARS извлечённого текста нет. По заданным шаблонам явного
wet/dry basis определения не найдено. Это ограниченный поиск текстового слоя,
не полное семантическое перечитывание и не доказательство отсутствия в сканах/
изображениях/других формулировках. RAW BP500 excerpts — данные источника,не REV values.
Source issues остаются OPEN. Источник не переаттестован независимо этой сессией.

31 точный вход в input_manifest.json проверен по Git/SHA256/LFS. Входной аудит
WARNING /4 PASS/3 NOT_RUN допускает только documentary supplement;§4/5/6 запрещают
зависимые физические выводы. Уже заданные BP500/сырьё/адаптация площадки не спрашиваются
повторно;готовые будущие чертежи не требуются от оператора.

Rev8 C8d1b45afa84eca078a8de0a9822d6925dd87745b и25 target/26 reviewed artifacts
не изменены; R5 акт04502cfe/H64ac3e остаётся CURRENT/WARNING только для rev8.
Он НЕ проверяет этот новый supplement. Новый independent review NOT_RUN.
Инженерные функции указаны как рекомендации,engineering_owner_session/due null.
Документальный owner R1 не выдаётся за назначение R2/R3/R4/R5/R6 или метролога.

build_plan.py --output-dir TEMP воспроизводит13 outputs. verify_plan.py:
395 PASS/0 FAIL,13 MATCH;source text search replay MATCH кроме observation UTC.
Это авторская целостность/покрытие/воспроизводимость,не independent review/VAL result.
search_sources.py --output TEMP сохраняет собственный результат поиска вне checkout.
Авторский verifier имеет R1 identity guard: reviewer не должен подменять session.

## Ограничения и следующий контроль

Все критерии — предложения,threshold/tolerance/uncertainty/range UNKNOWN/null;
objective completeness отделена от численного порога. Actual records пусты,
все VAL/TEST NOT_RUN, execution_permission false. Реальная конструкция/материал/
нагрузки/контакты/геометрия/COTS/ресурс UNKNOWN. G1 не требует подмены определения
критериев выполненными физическими испытаниями; будущие результаты разделены по этапам.

B01/B02/B03 и source issues не закрыты автором. RAW40/84 UNKNOWN/15 gaps,
44 полные bindings/нагрузки/ходы/CAD,52 interfaces,42 source-state объекта,54 old pins
и12 protected trees сохранены. Старые REJECT/STALE/material2/четыре FAIL/OBS01
exact-C closure не сброшены;WHAT_IF applicability NOT_EVALUATED.

42 состояния не рассчитаны;§4/5/6 NOT_RUN;прочность/устойчивость/реальные реакции/
цикл не подтверждены. Архитектура/ТЗ NOT_APPROVED,G1 OPEN,W02/physical READY NO-GO.
Численный/физический этап,CAD-build/rebuild и физические испытания не разрешены.
C результата фиксирует новый supplement; следующий H даёт exact C и запрос R5.
Публикация в существующем PR55 не разрешает main merge/утверждение ТЗ.
