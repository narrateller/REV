# Копии LAP и карточки OSTI для независимой проверки R5

Подготовлено R2 `r2-material-01` по акту REV-R5-R2-SOURCES-RECHECK-02-001 на `c5f22ecc35f27066a8f2e04cc0ed39adef8326ee`. Дата получения 2026-11-11 UTC. Проверены наличие PDF, титулы и приведённые на них идентификаторы/даты; полное чтение методик, независимая проверка R5, действительность редакций и применимость для смеси REV **NOT_RUN**. Получение копии не является утверждением метода.

| Файл | URL получения | Идентификатор и данные титула копии | SHA-256 |
|---|---|---|---|
| `NREL-42620.pdf` | https://docs.nlr.gov/docs/gen/fy08/42620.pdf | NREL/TP-510-42620, *Preparation of Samples for Compositional Analysis*; Issue Date 8/06/2008, Revised August 2008 | `e3d3afc47572ff3fa28dff1258da31348f217b8a9d127a68132a603371786e1c` |
| `NREL-42621.pdf` | https://docs.nlr.gov/docs/gen/fy08/42621.pdf | NREL/TP-510-42621, *Determination of Total Solids in Biomass and Total Dissolved Solids in Liquid Process Samples*; Issue Date 3/31/2008, Revised March 2008 | `bca9e0a067a83a8ed2a092bbf5ef7a594b63db86596a6da883aedaff1e41e8c3` |
| `NREL-42622.pdf` | https://docs.nlr.gov/docs/gen/fy08/42622.pdf | NREL/TP-510-42622, *Determination of Ash in Biomass*; Issue Date 7/17/2005, на титуле January 2008 | `ae20ddf840f27d11297e8960fe1c7abbb47cf074f355602eab131b358d24bda6` |
| `osti-1328338.json` | https://www.osti.gov/api/v1/records/1328338 | Сохранённый полный ответ OSTI API, HTTP 200; по полям карточки: дата публикации 2016-07-11, DOI 10.1016/j.powtec.2016.07.016, тип Accepted Manuscript | `7073a0d546e63902e4c6c7a156c84d302263b38be5811fde34d4940e2a64f4ea` |

Карточка OSTI содержит метаданные записи SRC-02 и ссылку на полный текст, но это само по себе не устанавливает тождество конкретного файла `copies/SRC-02.pdf` именно опубликованной или принятой версии; независимая проверка связи **NOT_RUN**. Ответ JSON сохранён без редактирования. Хэши устанавливают идентичность передаваемых байтов, не подлинность, актуальность или применимость.

Ранее запросы `www.nrel.gov/docs/gen/fy08/42620.pdf`, `42621.pdf`, `42622.pdf` вернули CONNECT 403. 2026-11-11 запросы `docs.nrel.gov/docs/gen/fy08/42620.pdf`, `42621.pdf`, `42622.pdf` также вернули curl exit 56, HTTP 000, CONNECT 403. URL `docs.nlr.gov` из таблицы вернули HTTP 200 и PDF, сохранены точные полученные байты. Дополнительный запрос к `www.nrel.gov/docs/fy08osti/42621.pdf` — CONNECT 403. Различие дат 42620 с цитируемым в SRC-04 2010 годом оставлено для отдельной проверки; наличие иной версии не установлено. Официальные библиографические сведения не заменяют проверку реального документа и актуальной редакции.

PDF используют Git LFS. Для R5 в чистой копии: `git lfs install --local`, затем `git lfs pull --include="verification/r2_primary_sources/lap_evidence/*.pdf"`; далее `sha256sum verification/r2_primary_sources/lap_evidence/NREL-*.pdf verification/r2_primary_sources/lap_evidence/osti-1328338.json`. После этого сверить титулы, идентификаторы, версии и необходимые разделы с результатами R2; JSON доступен как обычный Git-файл. Сохранять уведомления о правах и условиях использования, содержащиеся в полных оригиналах PDF.

R5-SRC-B01 OPEN до независимого решения; никакая методика или применимость к REV не утверждена. Текущие редакции, лабораторная оценка, физические пробы, калибровка и испытания NOT_RUN; B01–B03 и G1 OPEN.
