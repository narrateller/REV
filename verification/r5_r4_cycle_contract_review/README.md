# R5 OUTPUT-review документального контракта

Акт: [review.md](review.md). Проверенный C `3cf32daef67a91f393b808adb0dc07ba4c73cac2`, H `bd7d3bf8f02f4504ec04114ada7cccbd64e11af5`.

```bash
.venv/bin/python -B verification/r5_r4_cycle_contract_review/independent_probe.py > /tmp/r5-cycle-contract-independent.json
.venv/bin/python -B verification/r5_r4_cycle_contract_review/reproduce.py
```

Первый скрипт независимо проверяет 59 авторских примеров и две state-трассы,
строит 26 новых случаев с корректными ожиданиями, фиксирует **10 расхождений**.
Его exit 0 означает успешное сохранение эксперимента, **не PASS контракта**.
Ожидания получены отдельной трёхзначной моделью и символическими инвариантами;
авторский classify используется как проверяемая реализация. Test-atoms не
являются численными параметрами REV, а два conservation witnesses не являются
исполнением отсутствующего материального движка или физическими испытаниями.

Второй скрипт воспроизводит checker/registry, сверяет 17 Git-входов, 11 main
деревьев и отдельный CAD-кандидат. Пишет новые служебные логи только в этот
каталог review; при повторе timestamps/времена и удалённая main могут измениться.
Для нового checkout требуются точные исходные commits (включая CAD3591),
проектные файлы и Python/PyYAML; никакие solver/CAD генераторы не вызываются.

independent_results.json содержит корректные ожидания и фактические исходы,
reproduction.json — командные логи и сохранность; object_identity.json — байты
пакета C. environment.json фиксирует Python/платформу. evidence_hashes.json
хэширует акт и доказательства, кроме самого списка.

Вердикт REJECT_WITH_BLOCKER для однозначного контракта действий/READY; журнал и
ресурсы пригодны как черновик с WARNING. Архитектура/ТЗ/оборудование не утверждены,
physical tests NOT_RUN, G1 OPEN.
