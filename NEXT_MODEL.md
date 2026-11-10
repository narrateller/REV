# Следующая модель — T-INIT / codex-01

- Статус: ожидание принятия claim в main; анализ источников не начат.
- Роль: R1, модель Codex, сессия codex-01; назначение подтверждено пользователем.
- Задача: T-INIT; первый объём — инвентаризация четырёх PDF и паспорт источников.
- База main: 2e479849cea10dab9376a68cb44d2ff716c215da; ветка work/T-INIT/codex-01.
- claim_record_commit / work_commit C: a31a6d86cde8799807e6d21454deda8db55b695a.
- Heartbeat UTC: 2026-11-10T12:06:09Z; lease_expires_at: 2026-11-11T12:06:09Z.
- Входы: AGENTS.md, AGENT_PROTOCOL.md, STATE.md, ISSUES_AND_TASKS.md, roles/role_profiles_summary.md, params/registry.yaml, reviews/cross_check_log.md, project/source_manifest.json, sources/raw/ в базе 2e479849cea10dab9376a68cb44d2ff716c215da.
- Результат: предложение claim в ISSUES_AND_TASKS.md; инженерных результатов нет.
- Капсула: handoffs/T-INIT/codex-01.md; независимый review: NONE.
- Доступность при записи: LOCAL_ONLY; после push проверять удалённую ветку по SHA.
- Первый шаг: получить актуальную main и проверить, что claim принят, владелец codex-01, lease действителен, входы актуальны. Запись в рабочей ветке сама по себе права начать анализ не даёт.
- При истечении lease или конкурирующем claim: восстановление/продление по протоколу, без автоматического захвата.
- После принятия: оформить входной акт по протоколу до инженерных выводов, затем начать инвентаризацию. G1 остаётся открытым до независимой проверки и утверждения ТЗ.
