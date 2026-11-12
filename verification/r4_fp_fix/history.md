# История исправления R5-FP-NEW-B01

Пять исходных false PASS воспроизведены до правки в отдельной копии, включая независимые native witnesses. Основной checkout не мутировался probe.

Первая semantic reanalysis остановилась при сравнении function witness: frozen API возвращает tuple для пары, JSON хранит list. Это не расхождение геометрии. Новый код нормализует только сериализуемое представление; collision/method/continuity критерии не ослаблены. Лог отказа сохранён, ошибка не засчитана как выполненная проверка.

Повторная явная reanalysis прошла полную fresh сверку всех matrices/intervals/classifications/assessment. Native CAD, входы, body states и исходные геометрические before/after не менялись. Верификация и генерация по-прежнему разделены; verifier не исправляет stale пакет.

Дополнен critical subset: все пары сервисов обязательны, changed-set выводится из inputs. Геометрические service outcomes и физическая пригодность отделены от выполнения команды/negative test expectation. B01 остаётся OPEN до независимого R5.
