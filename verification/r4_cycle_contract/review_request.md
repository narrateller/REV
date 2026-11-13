# Запрос независимого R5 — CYC-01 и ранние CYC-08/09

Автор R4 r4-linked-20261111, T-r4-cycle-contract-01. **OUTPUT review NOT_RUN**.
Объект — неизменяемый C результата, полный SHA фиксируется следующим H в
NEXT_MODEL.md и handoffs/T-r4-cycle-contract-01/r4-linked-20261111.md. H содержит
только учёт/эстафету, не исправленный задним числом контракт. Ветка
work-r4/T-r4-cycle-contract-01/r4-linked-20261111, https://github.com/narrateller/REV.

Проверить независимо от авторского checker:

1. Входы/полномочия на main d22542f1fb9c3ac932fadd12dceeed5b1f9c8ad9,
   принятие claim PR #43, owner/lease и 17 blobs. Сохранность 11 деревьев и
   отдельного CAD-кандидата; не путать чтение отчёта с native-review.
2. L1–L5: одна база, pending внутри PRESS_ACCOUNT, не удвоенный запас;
   lineage/partition/retained и приёмник; REMOVE не теряет вещество и не
   создаёт clear. Смена влажностной базы/потери/обмен остаются неизвестными.
3. A: empty/startup/column/steady различены, реакция не выдумана, продукт не
   появляется раньше преобразования/partition, старый ход не удлиняется из
   предположения «новая доза должна пройти весь канал». B: partial/repeated
   gather не product; unload → unlock → open и reset не заменены HOME/ACK.
4. Согласованность state/event/guard/READY и примеров, в том числе составных
   FALSE+UNKNOWN, раннего REMOVE, исчезновения/двойного остатка, ошибочной базы,
   дубликата ACK, неподдерживаемого метода и неверной последовательности B.
   Положительные примеры/две трассы явно ASSUMED, не реальное разрешение.
5. Все стадии/паузы/потребители/возможные перекрытия и полости/потоки описаны,
   A8/B8 не дополнительная стадия, UNKNOWN не ноль, время оси не полный цикл.
   READY включает материал/приёмник/ресурсы и валидность обратной связи.
6. Ответы/одобрение R2/R3 отсутствуют и не выдуманы; вопросы привязаны к guards.
   Итоговые CYC-08/09 и CYC-02…07 остаются последующими работами.

Авторская воспроизводимость (документы, без solver/CAD/rebuild):

```sh
python3 -B verification/r4_cycle_contract/check_documents.py
python3 -B scripts/check_registry.py --check-git
git diff --check
```

document_checks.json / integrity_checks.json фиксируют фактические результаты
и read-only поведение. Эти команды не независимый анализ баланса или CAD.
R5-CYCLE-W01/W02 и CYC-01…09 автором не закрыты; G1 OPEN, реальная физика/параметры
UNKNOWN, открытие B/физический L-путь INDETERMINATE, physical tests NOT_RUN.
Архитектура/ТЗ/COTS/конструкция не утверждаются. Не выполнять общий rebuild
по этому handoff; сначала отдельный документальный review и межролевые ответы.
