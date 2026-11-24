# PLAN — REV, функциональный аналог BP500

Цель: рабочая КД по ЕСКД на пресс с параметрами не хуже BP500 (`ops/criteria/design_criteria.yaml`).
Статусы: TODO / RUN / REVIEW / DONE / BLOCKED. Одна строка на задачу, итог — в конце строки.

## Шаг 0 — перезапуск базы и гейты (24–27.11)
| ID | Роль / исполнитель | Задача | Зависит от | Статус |
|---|---|---|---|---|
| T-0.0 | ГК (Claude Code) | Тег `legacy-fork2-20261120` на `8537ff2`. Перенос CODEX_HOME bos/alm в `%LOCALAPPDATA%\rev-orch\codex\`. Коммит: `CLAUDE.md`, `DECISIONS.md`, `PLAN.md`, `ops/criteria`, `ops/tasks`, `docs/AUDIT_OPUS_REPORT.md`; `AGENTS.md` ← `ops/AGENTS.executor.md`; `.gitignore` (ops/state, ops/runs, ops/review_queue); временный минимальный CI | — | DONE 24.11: тег, CODEX_HOME bos/alm перенесены (voh/alm/bos logged in), база закоммичена |
| T-0.1 | CAD-инструмент, Codex high | Геометрические гейты G-ENV, G-MASS, G-COLL, G-FEED, G-CLEAR под freecadcmd + калибровка на W02-04 | T-0.0 | DONE 24.11 c08e928: W02 A/B V1/V2 — MASS/ENV/FEED/CLEAR FAIL, COLL PASS; VER Sonnet ACCEPT_WITH_NOTES → T-0.1a |
| T-0.2 | Расчётный инструмент, Codex high | Расчётные гейты G-PFACE, G-DOSE, G-CYCLE + G-SCOPE + `design/params.yaml` (схема) + калибровка на W02-04 | T-0.0 | DONE 24.11 068d459: W02 PFACE 20,9 МПа / DOSE 740 > 310 мм / CYCLE 59,9 с FAIL; синтетика PASS; VER Sonnet ACCEPT_WITH_NOTES → T-0.2a |
| T-0.3 | Инструмент, Codex high | Раннер `ops/run_task.py` + адаптер codex + детектор лимитов + ResultBundle + сборщик пакета проверки | T-0.0 | TODO |
| T-0.1a | CAD-инструмент, Codex high | Остаточные дефекты: G-CLEAR (эксцентриситет → ложный PASS), G-FEED (контакт по ребру), consumed_objects — **закрыть до первой силовой CAD-модели** | T-0.1 | TODO |
| T-0.2a | Расчётный инструмент, Codex high | Остаточные замечания: G-CYCLE (тавтология пика), G-DOSE (подвод = 0 по умолчанию), installed_kW — **закрыть до D1** | T-0.2 | TODO |
| T-0.4 | ГК | Наследие → ветка `archive/legacy`, удаление из `main`. Итоговый CI: гейты + тесты. Отчёт калибровки `ops/calibration/w02_04.json` | T-0.1–T-0.3 | TODO |
| G0 | ГК | **Гейт шага 0:** калибровка совпала с ожиданием (FAIL: масса, габарит, давление, подача, зазор, доза; PASS: коллизии), раннер прошёл пробную задачу | T-0.4 | TODO |

## Шаг 1 — технологический расчёт (с 25–28.11, 2 потока)
| ID | Роль / исполнитель | Задача | Статус |
|---|---|---|---|
| M-1 | ГК (Opus) | Мастер-расчёт: силовая схема, сечение 150 × 60, сила, Ø главного цилиндра, подпрессовка, доза и ход, циклограмма 6 с, мощность — вручную, с вилками | TODO |
| T-1.1 | TECH, Codex high | Модель уплотнения p(ρ), K, μ, упругое восстановление → требуемое давление (литература с DOI) | TODO |
| T-1.2 | TECH, Codex high | Камеры подпрессовки и главная: сечения, длины, доза, ход | TODO |
| T-1.3 | HYD, Codex high | Главный цилиндр, подпрессовка, шибер: силы, площади, давления (≤ 300 бар) | TODO |
| T-1.4 | HYD, Codex high | Циклограмма ≤ 6 с, насос и аккумулятор, мощность ≤ 30 кВт, бак, охладитель | TODO |
| T-1.5 | HYD, Codex high | Принципиальная гидросхема (ISO 1219), клапаны, блокировки фаз | TODO |
| X-1 | Codex high | Независимый пересчёт M-1 другим методом | TODO |
| D1 | ГК + оператор | Решающий гейт: параметры технологической схемы зафиксированы | TODO |

## Шаги 2–5
См. `ORCHESTRATION_PLAN_OPUS.md` §4.2 и §9. Карточки создаются ГК после D1.
