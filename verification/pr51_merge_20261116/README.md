# PR51 — квитанция разрешённого обычного merge

PR https://github.com/narrateller/REV/pull/51 MERGED 2026-11-16T22:44:16Z.
Merge commit: 3353de6c9fc699fbd565f1ce63cebedad3137a12.
Родители: прежняя main f731910273b47f46c6d45114cecd76de6fa8adf9 и точный
одобренный head 7fac152d7b16e2ebb871386eba0831f50ad18ddb. Дерево merge совпало
с head; squash/rebase и удаление исходных веток не применялись.

Прямое разрешение пользователя и запрет инженерного старта — authorization.json.
Свежая проверка main/head/двух CI/accepted owner/lease/конкуренции/входов —
premerge.json и premerge_preservation.json: 844 PASS, 706 materialized source files,
54 pinned inputs, 12 исходных tree identities, 44 полные bindings, 84 RAW/null.
Merge request использовал merge_method merge и условие exact head SHA.
Реальный ответ GitHub — merge_result.json; родители/дерево/remote main/14
исторических C/H — postmerge.json. CI нового main — main_CI.json после фактического
завершения; root registry этой отдельной ветки — registry_status.json/registry.log.

Эта квитанция и новые сводки сохраняются в отдельной ветке
work-r1/pr51-merge-receipt/r1-pr48-integration-20261116; она не добавляет второй
merge или новые коммиты в main. В main прежние фразы «PR без слияния» в сводке
2026-11-16T22:23:55 — снимок подготовки до разрешения и фактического merge;
актуальное событие интеграции фиксируется этой квитанцией и GitHub PR.

Claim R4, heartbeat, owner 6afb4750-7918-8191-8569-77b5b0c41050 и исходный
lease до 2026-11-17T17:44:00Z не изменены. Истекшие полномочия не продлеваются.
OBS-01 CLOSED только на R4 C beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe;
независимый R5 C/H 3784efa32ca26547f2581101474d6188f000c348 /
fe156cb3fbbb11d86a2716db9adcc7f44057a042, 388 PASS / 0 FAIL, общий WARNING.
Старый акт остаётся STALE с историческими четырьмя FAIL, архивом и исходным
registry FAIL. Параметры/нагрузки/ходы/CAD/история не переписаны.

42 состояния не рассчитаны; §4/5/6 NOT_RUN, отсутствующие реальные данные UNKNOWN.
Прочность, устойчивость, реальные реакции и цикл не подтверждены; архитектура/ТЗ
NOT_APPROVED, G1 OPEN, W02/PLC/physical READY NO-GO. Численный/физический этап,
CAD-build/rebuild, испытания, изготовление/выпуск не начаты и не разрешены.
Прежние блокеры/семь REJECT/material history=2 не закрыты. Предложенный intake
T-r1-force-inputs-intake-01 остаётся PROPOSED, owner NONE/lease null/engineering
NOT_STARTED; текущая команда разрешала только merge PR51.
