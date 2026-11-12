# REV-R4-FEED-POWER-INPUT-01

R4 r4-linked-20261111, 2026-11-12T01:10:28.517669Z. main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 после fetch; принятый PR #35/подтверждение пользователя, claim 79e9c3aa9aaca33778814957fafecd93a4adc392 ancestor main. Owner r4-linked-20261111, lease до 2026-11-12T18:06:24Z (12 ноября 21:06 МСК) действует, не продлён; другой принятый owner не найден. Историческое NONE/PENDING main сохраняется с основанием нормализации, координатор сверяет перед интеграцией. Scope all-press A/B geometry/motions/service включает текущую коррекцию непринятого исследования, нового claim не требуется.

Вход C a5d5bad6dd8928045512bca16836fd1d2544b7ca, точный RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430 (REV-R5-FRAME-NEW-B01-001): B01 CLOSED в его области, выпуск ACCEPT_WITH_WARNING; геометрическая группа 18 пар принята с WARNING; 20 residual native пар OPEN. История review/probe/evidence получена fast-forward без изменений. Прежние 34 Python-модуля (core/layout/analysis/frame release) фиксируются в frozen_tool.json, менять их запрещено; новые адаптация/проверки cad/feed_power требуют независимого review.

| Аудит | Итог | Основание |
|---|---|---|
| Требования/границы | PASS | Выбранные 20 пар и все old ID сохранены; геометрия следующей группы без выбора архитектуры REV |
| Источники | PASS | before_inventory.json с native witness каждой пары; новый отдельный ASSUMED rev8 до построения, реальные registry/COTS UNKNOWN |
| Размерности/базы | PASS | SI m/s, прежние оси/рабочие ходы и doser_slide неизменны; новый условный service retract/park отдельно |
| Силы/прочность | NOT_APPLICABLE | Только номинальная топология опор/сопряжений; крепёж, материал, способность нести силу/момент UNKNOWN |
| Геометрия | PASS | Pocket/doser-floor и doser-wall/hopper-floor butt planes, motor end-face mounts/tank support. Gap для старого cap UP сохраняется между split tray/guides, тела не удаляются |
| Цикл/сервис | PASS | Восемь limited исходов, полный ход/возврат; новая doser side→UP→DOWN→side, motor/tank sequences. Старый прямой UP через неподвижный hopper НЕ исправляется маркировкой: все 6 native positive пар остаются BLOCKED-контрпримером в полных матрицах |
| Прослеживаемость | PASS | Статические 14 пар должны стать zero volume; новые сервисные траектории проверяются отдельно. Любой положительный legacy overlap остаётся видимым, не переводится в INDETERMINATE. Реальная выполнимость extra service stroke/оснастки INDETERMINATE из-за UNKNOWN привода/расстыковки/подъёма |

Вход WARNING: разрешено только ограниченное исследование ASSUMED. Принятую геометрию frame/gate/portal и проверенный инструмент сохранить, новый оркестратор/контактные объяснения требуют R5. Не запускать прежний hardcoded frame verifier как будто он проверил новые CAD; новый readonly adapter обязан использовать те же проверенные public CAD/scene APIs и отдельный manifest. Генерация отдельно от verifier. Физические испытания NOT_RUN, весь пресс не принят, G1 OPEN.
