# R4 → независимый R5: narrow B03 type RECHECK

Основание ARB-R1-CI-SEMANTICS-02 на e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3.
SHA прочитан/зафиксирован в капсуле до кода, audit/merge checkpoint 64154d8.
Проверять exact новый C из следующего H; предыдущий R5 3d317b3 проверял Cbd7ce8a.
Три REJECT, interface_consecutive_rejections=3 и material-contract history=2
сохранены. B03 OPEN; автор не закрывает замечание и не заменяет независимый акт.

Норматив v1 и весь semantics_v1, payload/44 bindings/четыре force variants,
frozen helper, нагрузки/расчёты/CAD не изменены. Исправляется только реализация
проверки типов в metadata/source/ref/AST/phase bindings и recovery predicate.

1. Повторить шесть новых R5 контрпримеров и прежние семантические случаи после
   fresh re-export. Проверить ревизии во всех nested A/B reference-классах и
   разных стадиях: bool, integral float, string/null/missing/container, диапазон.
   Нельзя достигнуть MATCH одновременным изменением JSON/CSV/SVG/hashes.
2. Проверить общий metadata_types контракт: exact JSON integer, source revision
   >=1, snapshot/origin counters >=0; recursive metadata type/shape/value.
   Schema/authority, bool flags, recovery bindings и FILL successor не должны
   принимать Python numeric aliases. basis_revision остаётся textual identity tag.
3. Сравнить recovery_value и frozen recover на тех же proof/context/fault.
   Невалидные origin false/0.0 должны дать UNKNOWN/INDETERMINATE, fault OPEN.
   Не чинить snapshots и не преобразовывать типы для искусственного успеха.
   Predicate не применяет возвращённый frozen state к исходному context.
   Проверить правильные integer cases, stale/foreign target/revisions,
   сохранение остальных faults/rejected IDs и обычные WORK-запреты.
4. Убедиться, что строгость метаданных не меняет физическую numeric equality,
   разрешённую нормализацию signed linear expressions и rational times.
   Положительный исходный пакет и корректное recovery обязательны.
5. Повторить readonly/idempotence, отдельный явный exporter, прежние 411 cases
   норматива 53/84 и B01/B02 fixtures. Проверить побайтную сохранность норматива,
   helper и protected inputs; сохранение всех вердиктов/артефактов трёх отказов.

Команды, типы, аудит сравнений и результаты — type_correction/README.md,
checks.json, type_cases.json, independent_replay.json, preservation.json.
765/765 author replay неизменённого probe R5 не является новым актом R5.

Стабильная передача/CAD iteration NO-GO до независимого RECHECK B03. W02/PLC/
CAD/rebuild/physical trials вне scope. Physical READY NO-GO, архитектура/ТЗ
не утверждены, G1 OPEN. Геометрические пары не проверялись.
