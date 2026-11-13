# Один пакет интеграции: документальный контракт и предложение CYC-02/03

Подготовка PR без слияния по прямому поручению пользователя. Это изменение
учёта/постановки, не новая редакция проверенного контракта или CAD.

- [Предложение ограниченной интеграции](../../decisions/CC-DOCUMENTARY-INTEGRATION-PROPOSAL.md).
- [Новый task и claim](../r4_cycle_interfaces/README.md).
- input_audit.json — main, owner/lease, 7 неизменяемых пакетов, 17 inputs,
  11 защищённых деревьев и точные SHA.
- preservation.json / checks.json — фактические проверки подготовки;
  pr_body.md — готовое описание PR без conversational history.

В PR входят полными предками C 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed,
решение R1 616135755d1b6cbaa09ae9800bad5af8bbc28aed и акт R5
e3c0d7d828aab7b6a7e14dd230c5c3a01fea9d40. Истории d99afb4/c56e494 и всех
последующих проверок/исправлений сохранены. consecutive_rejections=2 не сброшен.
Проверенные helper/JSON/fixtures/results и review-пакеты не изменяются;
статусы старых stdout не правятся под новый вердикт.

B01 CLOSED по независимому R5 только документально на точном C, общий WARNING.
W01 только документально. **W02 OPEN/NOT_IMPLEMENTED; исполняемая материальная
логика и физический READY NO-GO.** Не утверждены реальная геометрия/прочность,
цикл/безопасность, архитектура/ТЗ/COTS/весь пресс. G1 OPEN.

Родительский task IN_REVIEW до решения о документальной интеграции; он не
объявлен DONE автором. Новый task READY/owner NONE/claim PROPOSED_PENDING_MAIN;
до принятия claim реализация NOT_STARTED. Численные/CAD файлы и инструменты не
меняются; solver/CAD/rebuild/physical tests NOT_RUN.

Проверки из корня репозитория (readonly, не общий rebuild):

```sh
python3 -B verification/r4_cycle_contract/check_documents.py
python3 -B scripts/check_registry.py --check-git
git diff --check
```

Сверка Git trees/blob hashes охватывает все проверенные пакеты и их результаты;
успешный consistency check не является новой инженерной/физической приёмкой.
Рекомендуемый способ последующей интеграции — merge commit с сохранением
истории SHA, без переписывания/сжатия двух отказов и арбитража. Автор PR не сливает.
