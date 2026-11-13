Интеграция документального CYC-01 и ранних CYC-08/09 после независимого WARNING
R5; новая задача CYC-02/03 предлагается отдельным claim, её реализация не начата.

- Проверенный C: `0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed`.
- Арбитраж R1: `616135755d1b6cbaa09ae9800bad5af8bbc28aed`.
- Акт R5: `e3c0d7d828aab7b6a7e14dd230c5c3a01fea9d40`, B01 CLOSED только
  документально; W02 OPEN. Оба REJECT и subsequent RECHECK сохранены полными
  Git-предками; consecutive_rejections=2 не обнулён.
- Проверенные contract/helper/fixtures/results/reviews неизменны. Предложение
  интеграции: `decisions/CC-DOCUMENTARY-INTEGRATION-PROPOSAL.md`.
- `T-r4-cycle-interfaces-01`: положения/движения/разрешения дозатора, затвора и
  пуансона; варианты силовой компоновки вне запрещённой области штока, схемы,
  таблицы и критерии последующей проверки. `verification/r4_cycle_interfaces/`.
  Owner NONE, claim PROPOSED_PENDING_MAIN; работа начинается после принятия.
- Расчётные D/d, нагрузки и ходы сохраняются. Необходимость изменения направляется
  R3 отдельным расчётным предложением, не применяется молча.

**Ограничения:** только документальный интерфейс с WARNING. Исполняемая
материальная логика и физический READY — NO-GO; W02/G1 OPEN. Не утверждаются
архитектура/ТЗ/геометрия/физический цикл. Расчёты/CAD не менялись, rebuild и
физические испытания не выполнялись. PR не сливается автором; новый claim
не принимается автором.

Validation: `verification/cc_documentary_integration/checks.json` и
`preservation.json`; `check_documents.py`, registry `--check-git`, `git diff --check`.
Все 7 проверенных пакетов, 17 input blobs и 11 protected trees сохранены.
История review/preservation также включена. При интеграции сохранить историю
проверенных SHA; не переписывать старые акты/результаты под новый вердикт.
