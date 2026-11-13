# ARB-R1-CI-SEMANTICS-06 — положительный admission OPEN journal

R1 / codex-01; Q-R1-CI-SEMANTICS-ARBITRATION-01; T-r4-cycle-interfaces-01.
База main `3a9258c57e4bc15d6de98f1d17e8412ad6e8899a`.
Claim R1 PR #44 до 2026-11-13T22:14:32Z; R4 PR #45 до
2026-11-14T00:13:12.404899Z. Области и сроки этим решением не продлеваются.
Уточнение `3aa5ee100f57aa75315d429afef38f8a982b1afc` в прежней документальной области.

## Воспроизведение и основание

R5 `4e52c3953c989c1077107d1d4f4da6d39d923d85` проверил C
`b89854ad709bcb5c2991376bed41bf2f73acef82`, H
`ce1ad73aae7a5700203103c14290375cc519662b`: raw-FALSE fallback исправлен,
но неизвестные OPEN guard tags пропускаются и положительный recovery ошибочно
получает TRUE/ALLOWED_ASSUMED. Седьмой REJECT, interface counter=7; прежние шесть
актов и отдельная material history counter=2 сохраняются без обнуления.

R1 в изолированном checkout H акта
`962a2a9e0d12d8b4ccf7edd27be6163124ad52a3` выполнил unchanged
`reproduce_guard_tag.py` и `independent_probe.py`. Получено 732 case records,
696 matches и 36 FAIL с теми же ID, что у R5. Минимальный контроль:
missing guard даёт UNKNOWN/INDETERMINATE; null guard ошибочно TRUE/ALLOWED_ASSUMED;
корректный известный FEED_CLEAR даёт допустимый адресный TRUE/ALLOWED_ASSUMED.
36 наблюдений — один класс из 18 различающихся порядком сериализации inputs,
не 36 физических дефектов. Caller/proof не изменялись. Это воспроизведение,
не новая независимая приёмка; полная byte equality матрицы R5 не заявляется.

## Решение

Выбрано явное semantic admission всех OPEN записей перед **положительным**
выводом о пригодности журнала. Исправление только ветви exception недостаточно:
отсутствие Python exception не доказывает, что запись поддержана и распознана.
Вариант считать неизвестное имя доказанно посторонним отклонён. Вариант запретить
любой recovery при любом корректном чужом fault также отклонён.

R4 разрешена только корректирующая итерация B03 по этому решению после записи
его точного SHA в капсуле и проверки main/owner/lease/входов. B03 OPEN,
приёмка интерфейса BLOCKED; стабильный documentary/CAD handoff NO-GO до нового
независимого RECHECK. Норматив, frozen helper и расчётные/геометрические входы
не меняются. Полный journal repair, W02 и PLC в эту итерацию не входят.

### Обязательные правила

1. Поддерживаемый набор guard ID берётся из fixed contract definitions, а не из
   journal tags, предполагаемого происхождения fixture или списка собственных
   guards action. Для каждой OPEN-записи до фильтрации проверить, что guard
   определён, имеет требуемый тип и является поддерживаемым известным ID.
   Missing/null/bool/int/array/object/пустая/неизвестная строка не нормализуются
   в известный guard и не игнорируются как просто «не равен own guard».
2. Явно классифицировать записи на подтверждённо применимые, подтверждённо
   неприменимые и неклассифицируемые. Для утверждения неприменимости нужны
   поддержанные guard/scope/адресные causal отношения и все требуемые для
   такой классификации семантические поля по принятой схеме. Общий subject kind,
   отсутствие равенства неизвестного tag или совпавший F-digest сами по себе
   не являются доказательством неприменимости. Если обязательное для решения
   поле неизвестно, запись остаётся неклассифицируемой.
3. Описать bounded schema admission существующего журнала: тип/статус записи,
   origin/guard identity, необходимые scope/revision/causal поля, связь с fixed
   definitions и результат классификации. Не расширять её до материального
   engine или исправления чужих записей. Неизвестный/неподдерживаемый статус
   не считается доказанно RESOLVED/отсутствующим. Применять уже принятую history
   policy; не требовать повторного физического доказательства каждого старого
   события и не переоценивать историческое evidence в неподходящем текущем scope.
4. Положительный journal admission требует охвата **всех** OPEN-записей и
   отсутствия неклассифицируемых записей, способных скрыть обязательный latch.
   Нельзя закончить положительный scan раньше неизвестной записи или проверить
   только заранее отобранные own/target faults. Первое/среднее/последнее место
   записи и порядок известных/неизвестных записей не меняют семантический вывод.
5. При unclassifiable OPEN записи journal status UNKNOWN и вход OUT_OF_DOMAIN
   с причиной; raw TRUE не подтверждает отсутствие latch. При отсутствии
   независимого запрета scoped recovery UNKNOWN и общий INDETERMINATE.
   Не делегировать такой журнал в permissive helper как основание TRUE.
   Это строгость допустимости входа, не требование equality с legacy вне схемы.
6. Сохранить independently validated raw current FALSE, state и достоверные
   адресные causal запреты: при неизвестном журнале общий BLOCKED, а journal/
   scoped diagnostics могут оставаться UNKNOWN. Не трактовать malformed запись
   как самостоятельный доказанный FALSE и не вводить blanket BLOCKED.
7. Корректная известная неприменимая FEED_CLEAR запись в контрольном сценарии
   не запрещает closure recovery. Не удалять её и не менять guard/origin/status,
   hashes, expected snapshots, histories/rejected IDs/pending facts. Readonly,
   положительный адресный путь и ранее исправленные raw/domain/type/gate
   обязательства сохраняются. Успех возможен только внутри явно допустимой
   полной схемы, не от одного отсутствия reader exception.

## Критерии независимого RECHECK

R4 публикует C, полную declared admission/classification table и матрицу покрытия.
R5 использует fixed definitions, а не вывод candidate scan для oracle:

- повторяет missing/null/known-FEED minimal controls и все 36 прежних false TRUE;
- для OPEN тегов проверяет missing/null/bool/int/array/object/empty/unknown ID,
  first/middle/last, сочетания нескольких malformed и известных записей;
- проверяет используемые schema/scope/revision/causal поля, неподдержанный статус
  и невозможность silently skip необработанной записи; bounds проверки явны;
- проверяет raw TRUE/FALSE/UNKNOWN и невозможность false TRUE при неопределённом
  journal, без blanket BLOCKED; known raw/state/causal FALSE сохраняются;
- положительные supported unrelated FEED и адресный recovery, различие «чужой
  известный» и «неизвестный», отсутствие искусственного recovery deadlock;
- journal/raw reader exceptions, stale/foreign controls, snapshot/type/final
  gate/B01/B02 и нормативные/regeneration/readonly регрессии;
- неизменность helper/norm53/84/44 bindings/4force variants/расчётов/CAD и всей
  истории отказов. Новая схема не ослабляется для легализации malformed inputs.

B03 закрывается только новым независимым R5 актом на точном C. R1 этого не делает.
R3 force studies WARNING остаются отдельной разрешённой областью при своём
действующем claim. Прочность/геометрия/physical READY не принимаются; W02/PLC/
исполняемая материальная логика NO-GO. CAD/rebuild/физические испытания NOT_RUN,
архитектура/ТЗ/оборудование не утверждены, G1 OPEN.
