# Авторский нормативный минимум v1 — по ARB-R1-CI-SEMANTICS-01

Основание: решение R1 `5fe510bbc55a052c360ab39a2491a061584b8fb7`, пункты 1–7.
Это нормативный вход документального checker для независимого RECHECK, не
утверждение инженерной архитектуры, физики или конструкции.

minimum.json расположен отдельно от mutable proposal/--package. Его schema,
ревизия и SHA закреплены в semantic_minimum.py; источником нормы не являются
текущие permissions.json, renderer или свежий exports_manifest. Manifest только
дополнительно связывает представления. Неизвестная ревизия нормы даёт UNSUPPORTED.

build_minimum.py — явная авторская операция. Она читает только неизменяемые
Git blobs, а не текущий payload:

- frozen material contract C0c4eb5d: исходные состояния, режимы, guards,
  fault scope/revisions и допустимые recovery actions;
- проверенный C144941c: документально закрытые B01/B02, позы/parent topology,
  частичные и полные ходы, 44 неизменных source bindings;
- независимые таблицы FAMILY/COMMON и явные результаты, выведенные из R1
  clauses 1/3/4/5 для всех семейств. В частности, producer FILL требует текущий
  D1, оба направления дозатора требуют собственного D_PATH_CLEAR, открытие G
  требует G_PATH_CLEAR, RELOCK — всех независимых closure results. Исключение
  generic DEPENDENCY_VALID только для двух recovery подстадий B.

Каждая норма хранит источники и ограничение применения. Новая ревизия нормы
требует записанного основания и RECHECK; checker не запускает builder и не
переписывает ослабленную норму ради MATCH. Нормы текущей v1 впервые предъявляются
на проверку в этой корректирующей итерации, отдельная приёмка R5 ещё не выполнена.

coverage.csv/json задают матрицу всех 53 действий и 84 пар действие/режим:
from/to, legal parent, собственные минимальные ENTRY, точные COMMIT/outputs,
parent invariants, жизненный цикл prerequisite/active parent, выбранные позы,
источник правила и check ID. Одни и те же условия распространяются на оба
невыбранных force options своего варианта A/B, без приёмки геометрии.

Outputs — обязательства получить актуальное свидетельство, **actual UNKNOWN**.
GUARD_CONFIRMATION и CURRENT_POSE/PRESERVED_POSE различены. Лишний output,
пропавший completion и неподтверждённый end pose не получают MATCH. Хранимая
поза инструмента не заменяет material receipt или физическое разрешение.

Для всех 18 поз типизированы unit/axis/frame и выражения отдельно по сценарию.
P1/P2/P3 используют только approach/work/eject своих BASE_A/BASE_B источников;
P_RETURN_END явно включает минус полного source return. Номинальный P0 после
полного возврата не подменён нулевой формулой без ссылки на return. Неизвестные
D/G/partial/stop/lock координаты обозначены как неизвестные символы/типы, без
назначения размеров. Поддержаны signed linear sums, точные pose aliases и
упорядоченные интервалы; перестановка/ассоциативность сумм нормализуется.
Умножение, функции, неизвестные символы/операции не получают MATCH автоматически.
Подпись, coordinate string и AST сравниваются с одной нормой, а не друг с другом.

Recovery binding — типизированное требование к **будущему конкретному** fault ID,
исходной scope/revisions и разрешённому result type по frozen helper. Это не
придуманный действующий fault. Binding/schema не служит положительным recovery
result. recovery_value проверяет конкретный synthetic request по frozen history,
fault ID, scope, типу guard/action, revisions и ENTRY; ничего не снимает и не
меняет. Null/wildcard/чужой target не дают TRUE. Историю, rejected IDs, остальные
faults и окончательное RECONCILE_HISTORY обслуживает неизменённый helper.

CLI возвращает ненулевой exit и FAILED verification gate для:

- SEMANTIC_MISMATCH — поддержанное, но противоречащее норме содержимое;
- INPUT_ERROR — повреждённый/неполный структурный вход;
- UNSUPPORTED — неизвестная схема, поле, режим или выражение.

Успешный gate только PASSED_DOCUMENTARY_ONLY. Геометрические sweep, W02, PLC,
материальная/физическая достоверность не проверяются; G1 OPEN, physical READY NO-GO.
