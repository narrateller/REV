# Пять независимых ложных PASS — причины и требуемые исходы

Все пять воспроизведены исходным неизменённым R5 probe в отдельном checkout 2592b47; before_counterexamples.json содержит actual exit 0, native witness и snapshot/no-writes. Старый успешный exit probe означает воспроизведение ошибки.

| Случай R5 | Расчёт фактического пути | Пропущенная проверка исходного adapter |
|---|---|---|
| A_new_service_with_retract_omitted | Прямой UP/DOWN, hopper пересекается: BLOCKED | Только IDs/order critical rows сверялись с current scene; их NO-positive статусы и assessment остались от L-пути; expected Y-сегмент не сверялся |
| B_new_service_with_retract_omitted | То же B: BLOCKED | Та же stale-semantic зависимость; успешный return/continuous принимался достаточным |
| A_lift_before_retract | UP до Y, коллизии при непрерывном замкнутом пути: BLOCKED | Фазовые имена/IDs сохранены; фактический порядок displacements не сравнивался с входным планом; доказательства относятся к другому порядку |
| A_powerpack_module_missing_moving_front_plate | Tank проходит через оставленную front plate: BLOCKED | Registry/IDs не потеряны, но состав движущейся группы не пересчитан/не связан с expected plan; старый aggregate moving_penetrations=0 был принят |
| A_unsupported_motor_motion | motion=rotation: INDETERMINATE | Method support не был обязательным fresh gate сервиса; raw INDETERMINATE из пересчитанной матрицы не дошёл до interval/assessment/verifier outcome |

Общее: внешние SHA-256 были корректны для изменённых service файлов, continuity/return/registry сохранены, readonly свойство не нарушалось. Ошибка не в неизменённых 34 модулях и не в исходной подтверждённой геометрии, а в связи текущих state/time с сохранённым вычисленным evidence и конечной агрегацией.

Исправление вычисляет заново все mandatory phases/participants/pairs/method/continuity/return и сверяет полные текущие matrices, interval results, classifications и aggregates. Фактический collision хранится отдельно от unknown; collision доминирует, неизвестное обязательное условие не даёт геометрического успеха. Expected negative BLOCKED может совпасть с тестом, но limited_geometry_success остаётся false. Общая физическая пригодность любой исходной L-сцены остаётся INDETERMINATE.
