# T-2.2g

Все команды выполняются из корня worktree. Использованы Python 3.13, NumPy, SciPy, PyYAML, Gmsh 4.15 и CalculiX 2.22 из комплекта FreeCAD. Решатели запускаются с одним потоком. Промежуточные геометрии, сетки, INP, FRD и DAT хранятся только во временных каталогах и удаляются при выходе расчёта.

## Воспроизведение

~~~powershell
$revPython = 'E:/Tools/Python313/python.exe'
& $revPython -B ops/gates/calc_gates.py --params calc/T-2.6/params/params.t26a.yaml --criteria ops/criteria/design_criteria.yaml --out gates.t22g.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 16 13 11 --radius 30 --wall 104 --band 172 --liner --elastic --cases long_skew --out calc/T-2.2g/fea/ring_three_meshes.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 16 13 11 --radius 30 --wall 104 --band 172 --liner --elastic --cases long_skew --out calc/T-2.2g/fea/ring_replay.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 13 --radius 1 --screen --out calc/T-2.2g/fea/ring_screen_r1.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 13 --radius 15 --wall 68 --band 132 --screen --out calc/T-2.2g/fea/ring_screen_r15.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 13 --radius 15 --wall 68 --band 132 --liner --screen --out calc/T-2.2g/fea/ring_screen_liner.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 17 --radius 22 --wall 82 --band 148 --liner --elastic --proof-only --cases long_skew long_centred short_skew --out calc/T-2.2g/fea/ring_screen_r22_elastic.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 17 --radius 30 --wall 104 --band 172 --liner --elastic --proof-only --cases long_skew long_centred short_skew --out calc/T-2.2g/fea/ring_screen_mass_limit.json
& $revPython -B calc/T-2.2g/fea/ring.py --mesh 17 --radius 30 --wall 104 --band 172 --liner --elastic --braced --screen --cases long_skew --out calc/T-2.2g/fea/ring_screen_saddles.json
& $revPython -B calc/T-2.2g/fea/lamella.py --mesh 8 --out calc/T-2.2g/fea/lamella_screen.json
& $revPython -B calc/T-2.2g/fea/window.py --mesh 18 --quick --out calc/T-2.2g/fea/window_screen.json
& $revPython -B calc/T-2.2g/fea/window.py --mesh 18 --quick --reinforced --out calc/T-2.2g/fea/window_reinforced.json
& $revPython -B calc/T-2.2g/fea/cassette.py 0 1 2
& $revPython -B calc/T-2.2g/fea/cassette.py 2 --iterative --label t22g_iterative
& $revPython -B calc/T-2.2g/fea/key_contact.py --mesh 7 --out calc/T-2.2g/fea/key_contact.json
& $revPython -B calc/T-2.2g/fea/key_contact.py --mesh 7 --proof-travel-mm 0.137 --out calc/T-2.2g/fea/key_proof.json
& $revPython -B calc/T-2.2g/run.py
& $revPython -B calc/T-2.2g/report.py
& $revPython -B calc/T-2.2g/check.py
~~~

G-CYCLE входит в вывод гейта и имеет справочный статус по D-GK-13 и D-OP-16. Из-за него команда возвращает ненулевой код при PASS двух обязательных гейтов. Команда check.py сверяет две независимые сборки расчётных артефактов, повторяет обязательные гейты и сравнивает двукратный прогон трёх сеток крыши с абсолютным допуском 10⁻⁶.

## Модели

Копии расчётов T-2.2f в prior содержат огибающую перехода дозы под крышу и базовую формулу ведомости. Изменены относительные ссылки и импорт. Нагрузки, проектные расчёты и каталог источников имеют отдельные файлы.

В модели крыши R30 стальная подкладка заменена распределёнными по плоским опорам нагрузками Janssen и трением. Связь с колоннами представлена осевыми пружинами. В пробе поперечных опор добавлены пружины с жёсткостью по изгибу рычагов. Эта проба показывает чувствительность крыши к силовому замыканию у шибера. Материальная податливость полок и продольных стенок учитывается через C3D10. Проверки K×μ, двух длин и перекоса сохранены в JSON.

Окно и башмак состоят из отдельных тел C3D10. Усилие через три разнесённые полосы ключа передают связи по средним перемещениям реальных полос с эквивалентной податливостью ключа. Верхний и нижний упоры задней станции моделируются по знаку продольного момента. Локальная модель контакта разбирает три площадки переднего засова. Модель кассеты воспроизводит вырез траверсы, натяг колонн, плиту и кассету T-1.7d при новом усилии.

Ведомость массы сводит объёмы расчётных тел, отдельные размерные строки и резервы. Силовые присоединения, работоспособность полного пространственного узла и ресурс остаются открытыми при статусе STOP в отчёте.

