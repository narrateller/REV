# Две последовательные отрицательные проверки и арбитраж

1. C `3cf32daef67a91f393b808adb0dc07ba4c73cac2`, независимый акт
   `d99afb4c3231d641d4a4921f39987264ce5ffc23`: REJECT_WITH_BLOCKER, пропущенные
   обязательные READY условия / удержание A. Его файлы и probe сохранены.
2. Коррекция C `4f31ed624336e1101b0ba04857f4316c73e4d375`, H
   `ec4968f81ba8ec51c707689d804d7a588bddec35`; RECHECK
   `c56e494a2e89ffa65b5876bfce6a4d6b4ae62f1b`: REJECT_WITH_BLOCKER. 26 случаев
   исправлены, 3/45 новых расходятся из-за чужого снятия/потери rejected A.
   W01 CLOSED только документально на этом C, W02 OPEN.
3. R1 `616135755d1b6cbaa09ae9800bad5af8bbc28aed`, ARB-R1-CC-01:
   consecutive_rejections=2, точный probe/R5 JSON воспроизведены; разрешена
   только B01 корректировка с адресными fault и накопительными rejected IDs.
   Полноценный W02 движок отложен; принятие и stable CYC02/03 BLOCKED.
4. Перед правкой SHA решения записан в capsule, входы/main/owner/lease сверены.
   Оба R5 и R1 decision/evidence включены полными Git-предками нового C.
   baseline_second_rejection.json побайтно совпал с сохранёнными R5/R1 результатами.
5. Текущий кандидат не обнуляет отказы и не закрывает B01. Старые formal review
   artifacts/index сохраняют reviewed SHA/verdict/findings/hashes; validity
   последнего индекса помечается STALE для изменённой редакции по протоколу.
   Оригинальные CURRENT записи доступны на исходных review commits, сами акты
   и независимые probe неизменны.
6. Изменены только documentary fault/history semantics и связанные fixtures/
   checker/документы. Материальные L1–L5, реальные UNKNOWN, вычислительные и CAD
   инструменты/артефакты не менялись. Независимый новый RECHECK NOT_RUN.
