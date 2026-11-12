# Корректирующая редакция 2 — разрешения CYC-01/08/09

**IN_REVIEW / независимый RECHECK NOT_RUN.** Входной акт R5 d99afb4c3231d641d4a4921f39987264ce5ffc23 отклонил binding-контракт на старом C 3cf32daef67a91f393b808adb0dc07ba4c73cac2. B01/W01/W02 остаются OPEN до его независимого решения. Текущая правка — кандидат, не самоприёмка.

- [Условия, актуальность, распространение и восстановление](permissions.md).
- [Полная таблица каждого действия](action_conditions.md), contract.json — 44 transitions / 40 guards / 8 recovery actions.
- [Причины и результаты исправления](../r4_cycle_contract_fix/README.md).
- Старые 59 примеров и 2 условные state traces сохранены с явными дополнительными ASSUMED guards; это не исполняемый материальный журнал.

```sh
python3 -B verification/r4_cycle_contract_fix/check_fix.py --baseline > /tmp/rev-cycle-baseline.json
python3 -B verification/r4_cycle_contract_fix/check_fix.py
python3 -B verification/r4_cycle_contract/check_documents.py
python3 -B scripts/check_registry.py --check-git
git diff --check
```

Baseline запускает неизменённый R5 probe против старых Git blobs в temp-dir; его exit 0 доказывает воспроизведение старых 10 ошибок. Текущий check_fix печатает actual/expected и завершится ненулевым кодом при расхождении. Командный результат, совпадение ожиданий и разрешение конкретного действия различены. Реальные guards UNKNOWN, физика/READY INDETERMINATE, G1 OPEN. Расчёты/CAD неизменны, rebuild/physical tests NOT_RUN.

## История редакции 1 (актуальные ограничения — выше)

# Контракт CYC-01 и ранние CYC-08/09

**T-r4-cycle-contract-01 IN_REVIEW, owner_session r4-linked-20261111.**
Claim принят PR #43/main d22542f1fb9c3ac932fadd12dceeed5b1f9c8ad9;
срок до 2026-11-13T18:16:39Z без продления. Результат — внутренне согласованный
ASSUMED_INTERFACE_PROPOSAL; межролевое одобрение и независимый OUTPUT review
NOT_RUN. Полный C результата — в следующем H / NEXT_MODEL.md.

- [CYC-01: материал, база/журнал, A startup/steady и B repeated gather](material_contract.md).
- [Символические примеры баланса/журнала](ledger_examples.md) без новых расчётов.
- [События и инварианты](events.md), contract.json — guards/states/transitions/READY.
- [Ранний CYC-08](resources_draft.md), resources.json — все 20 строк/ресурсы/UNKNOWN.
- [Ранний CYC-09](ready_draft.md) — READY по узлам **и материалу**.
- [59 примеров](transition_examples.md), transition_examples.json; две связанные
  ASSUMED трассы sequence_examples.json, без численных входов/вычисления физики.
- [10 вопросов R2/R3](questions.md), questions.json; [допущения/неизвестности](assumptions_unknowns.md).
- [Прослеживаемость](traceability.md), traceability.json; [входной акт](input_audit.md), input_acceptance.json.
- [Запрос независимого review](review_request.md); document_checks.json и integrity_checks.json.

```sh
python3 -B verification/r4_cycle_contract/check_documents.py
python3 -B scripts/check_registry.py --check-git
git diff --check
```

Первая команда — read-only проверка целостности/логической согласованности
документов; не численный расчёт, не модель lifecycle, не CAD-verifier и не
доказательство истинности guards. ALLOWED_ASSUMED относится только к явно
условным примерам. Все реальные guards и количественные входы UNKNOWN.
Исходные расчёты, CAD, код инструментов и registry неизменены; solver/CAD/
rebuild/physical tests NOT_RUN. Прежние BLOCKED/UNKNOWN не закрыты, открытие B
и физический L-путь INDETERMINATE. CYC-01…09, R5-CYCLE-W01/W02, G1 OPEN.

## История подготовительного пакета (до принятия PR #43)

**T-r4-cycle-contract-01 READY / PROPOSED_PENDING_MAIN / owner NONE.**
Предлагаемый исполнитель r4-linked-20261111 / Codex / R4.
Контракт ещё не разработан; это постановка/пакет отдельного claim.

- [Исполнимая постановка и критерии](task.md).
- [Claim и граница с прежней CAD-задачей](claim.md).
- preflight.json — точные версии/хэши/проверка области/срока/сохранности.

Основание — принятая карта C 43f03359fabe2b664935b17f9ac7851504093ece,
акт e69a8afbe4df3d53c4cc8b5883319e00eb8130af и решение PR #42.
Новый пакет после принятия claim должен содержать согласованные по терминам/
инвентарю/guards CYC-01/08/09 и примеры; реальные unknown и ответы R2/R3 не
выдумываются. Порядок/границы W01/W02 сохраняются, замечания не закрываются.

До принятия инженерная разработка NOT_STARTED. Solver/CAD/rebuild/физические
испытания NOT_RUN. Прежние расчёты, геометрия, кандидаты/акты не меняются.
Разрешена проверка структуры репозитория:

```sh
python3 -B scripts/check_registry.py --check-git
git diff --check
```

Следующий шаг — последовательное принятие claim в main координатором/оператором,
затем повторная сверка и работа по task.md. Никакой статус этого пакета не
принимает архитектуру/ТЗ/оборудование или всю машину; G1 OPEN.
