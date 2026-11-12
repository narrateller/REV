# Независимый RECHECK B02 QueryVolumes

Точный code/results C `de377f012da08f34796b2e59aee663ba0b2b3d2b`, ветка work-r4/build-layout/r4-linked-20261111. Входной акт REV-R5-CAD-TOOL-FIX-01-001 на 8f381c4b080d902cb023429c54d518bfd6fab681, проверенный прежний C 5449fb9bc4c20fcbc40fdec932876dcecc90ef4d.

Проверить оставшийся B02/Q01: все нативные QueryVolumes A/B, включая CylinderRemoval/DoserRemoval, сверяются с каноническими формулами входов по форме, размерам, локальному/глобальному положению и Role до/после recompute. Обновлённый hash не заменяет семантическую проверку; неподтверждённая зона запрещает общий CAD PASS, API/CLI дают явный FAILED. Новые 64 negative cases включают 60 обновлённых hashes и подмену manifest-списка. Старый probe сохранён с его ошибочным Q01 assertion, исходный ошибочный PASS воспроизведён до правки.

B01 CLOSED независимым R5 в проверенной области и не переоткрыт; lifecycle-код неизменён, повторены 20 его независимых regressions. B02 OPEN до нового независимого решения, самоприёмка не выполняется.

После materialize LFS и сохранения копии исходных результатов:

```sh
/usr/bin/python3 cad/layout/run_all.py
```

73 unit tests, 64 новых query-negative, 14 прежних CAD-negative, 33 lifecycle, 20 независимых lifecycle, 8 limited outcomes PASS. Все 14 команд exit 0; файлы cad/build/research_layout/validation.json, checks/query_regressions.json, checks/geometry_preservation.json, checks/report.json и assessment.md. Отдельная команда query_regressions — BUILD_README.md.

Исходная геометрия зон/компоновок и все 107486 записей фаз/пар сохранены. Прежние native проникновения R5 повторились: статически 17 A / 18 B положительных common volumes плюс прежние промежуточные случаи. Полный READY INDETERMINATE; физика/безопасность UNKNOWN, архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Слияние не выполняется.
