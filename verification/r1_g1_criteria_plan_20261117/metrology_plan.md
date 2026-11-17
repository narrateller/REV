# План проверок и метрологии — без разрешения исполнения

Все22 VAL/TEST NOT_RUN. Конкретные средства,редакции методик,диапазоны,разрешение,
неопределённость и число повторов UNKNOWN. Предложены классы методов и бюджетные статьи,
не метрологическая аттестация или выбор приборов.

| VAL / REQ | Карточка | Каналы | Стратегия | Обязательные evidence fields |
|---|---|---|---|---|
| VAL-REV-01 / REQ-REV-01 | CRIT-REQ-REV-01 | EVENT, MATERIAL, TIME, MASS | Будущий TEST-F-05 и аудит функциональной схемы | function_map, input_output_boundary, complete_cycle_log, product_disposition |
| VAL-REV-02 / REQ-REV-02 | CRIT-REQ-REV-02 | MATERIAL, MASS | Будущая характеризация по согласованным методикам | lot_revision, sample_graph, moisture_basis, particle_distribution, contaminants_method |
| VAL-REV-03 / REQ-REV-03 | CRIT-REQ-REV-03 | GEOMETRY, MASS, TIME, EVENT | Будущие TEST-F-03/04: обмер, взвешивание, наблюдение выхода | briquette_id, conditioning_record, dimensions, mass_record, defects, ejection_boundary |
| VAL-REV-04 / REQ-REV-04 | CRIT-REQ-REV-04 | EVENT, TIME, ELECTRICAL, MASS | Будущий TEST-F-05 и раздельный учёт потерь/остановов | material_settings, window_definition, all_products, rejects_stops, energy_records |
| VAL-REV-05 / REQ-REV-05 | CRIT-REQ-REV-05 | EVENT, MOTION, TIME | Будущие проверки автомата и TEST-F-01…05 | state_transition_id, command_feedback, permit_conditions, fault_response |
| VAL-REV-06 / REQ-REV-06 | CRIT-REQ-REV-06 | MATERIAL, EVENT, MOTION | Будущий review интерфейсов и TEST-F-01/02/04 | interface_id, boundary_revision, responsibility_map, buffer_state, transfer_events |
| VAL-REV-07 / REQ-REV-07 | CRIT-REQ-REV-07 | ELECTRICAL, TIME, EVENT | Будущий электрический/энергетический review и измерения | resource_spec, phase_id, startup_record, protective_device_spec, power_source_disposition |
| VAL-REV-08 / REQ-REV-08 | CRIT-REQ-REV-08 | PRESSURE, MOTION, FLOW, TIME, ENVIRONMENT | Будущие синхронные измерения и профильный анализ | hydraulic_point_id, pressure_reference, motion_id, contact_state, material_model_revision |
| VAL-REV-09 / REQ-REV-09 | CRIT-REQ-REV-09 | DOCUMENT, MOTION | Будущий аналитический/CAE review и отдельное подтверждение | case_id, geometry_hash, material_revision, support_contact_spec, criteria_refs, independent_report |
| VAL-REV-10 / REQ-REV-10 | CRIT-REQ-REV-10 | EVENT, MOTION, TIME | Будущий анализ риска и согласованные проверки функций | hazard_id, operating_mode, access_boundary, safety_function_spec, verification_record |
| VAL-REV-11 / REQ-REV-11 | CRIT-REQ-REV-11 | EVENT, PRESSURE, MOTION, TIME | Будущая матрица отказов и проверки только по разрешённой программе | failure_id, residual_energy_basis, retention_state, restart_authorization, recovery_sequence |
| VAL-REV-12 / REQ-REV-12 | CRIT-REQ-REV-12 | EVENT, MOTION, TIME | Будущая проверка измерительной цепи и TEST-F-01…05 | channel_id, quality_flag, calibration_status, time_alignment, inference_basis |
| VAL-REV-13 / REQ-REV-13 | CRIT-REQ-REV-13 | ENVIRONMENT, MATERIAL | Будущий review среды и разрешённые проверки воздействий | environment_id, material_spec_revision, temperature_record, exposure_conditions |
| VAL-REV-14 / REQ-REV-14 | CRIT-REQ-REV-14 | MATERIAL, ENVIRONMENT, DOCUMENT | Будущая характеризация и профильная оценка риска | composition_record, exposure_scenario, dust_properties, control_evidence |
| VAL-REV-15 / REQ-REV-15 | CRIT-REQ-REV-15 | DOCUMENT, EVENT, PRESSURE, MOTION | Будущий сервисный/DFM review и демонстрация по программе | service_task_id, energy_inventory, isolation_boundary, reaccumulation_check, retention_spec |
| VAL-REV-16 / REQ-REV-16 | CRIT-REQ-REV-16 | GEOMETRY, MASS, DOCUMENT | Будущий компоновочный/монтажный review и обмер | layout_revision, mass_centre_basis, support_reaction_basis, lifting_points, service_envelope |
| VAL-REV-17 / REQ-REV-17 | CRIT-REQ-REV-17 | DOCUMENT, GEOMETRY | Будущий DFM и каталоговый review | part_revision, route_revision, supplier_capability, material_spec, COTS_interface_review |
| VAL-REV-18 / REQ-REV-18 | CRIT-REQ-REV-18 | DOCUMENT | Будущий компетентный review применимости | jurisdiction, machine_classification, source_edition, exclusions, competent_review |
| VAL-REV-19 / REQ-REV-19 | CRIT-REQ-REV-19 | DOCUMENT | Аудит описи и воспроизведение применимых проверок | artifact_manifest, input_revisions, author_scope, environment, reproduction_receipt |
| VAL-REV-20 / REQ-REV-20 | CRIT-REQ-REV-20 | DOCUMENT | Будущий review программы; после разрешения выполнение/оценка | program_revision, REQ_VAL_coverage, method_revisions, metrology_budget, stop_rules, independent_program_review |
| VAL-REV-21 / REQ-REV-21 | CRIT-REQ-REV-21 | DOCUMENT | Аудит полной карты происхождения | user_direction, source_locator, decision_revision, maturity_history, reviewed_commit |
| VAL-REV-22 / REQ-REV-22 | CRIT-REQ-REV-22 | EVENT, MASS, DOCUMENT | Будущий TEST-F-05 и аудит журнала происхождения | event_id, from_to_ids, split_merge_refill, lot_revision, residual_loss, missing_reason |

## Предложенные каналы

| Канал | Объект | Метод-класс | Неподтверждённые статьи бюджета |
|---|---|---|---|
| MATERIAL | Состояние сырья/партии | Будущий описанный отбор/подготовка и независимые определения свойств;wet/dry база фиксируется до сравнения | sampling, method bias, representativeness, preparation, instrument, environment |
| GEOMETRY | Геометрия изделия/интерфейса | Калиброванное размерное средство по определённым базам/состоянию;отдельно до/после выдержки | calibration, resolution, datum, repeatability, temperature, conditioning |
| MASS | Массы изделия/дозы/остатка | Калиброванное взвешивание с тарой,идентификацией объекта и временем;объекты не отождествлять | calibration, resolution, tare, repeatability, drift, collection losses |
| TIME | Время/синхронизация | Общий временной базис команд/измерений с задокументированной задержкой и правилами пропусков | clock calibration, resolution, timestamp latency, channel alignment, missing intervals |
| PRESSURE | Давление в заданных точках | Будущий пригодный преобразователь в идентифицированной точке/режиме;absolute/gauge и роль давления фиксируются | calibration, installation, reference pressure, temperature, dynamic response, sampling alignment |
| FLOW | Расход рабочей среды | Будущий расходомер/обоснованный метод в определённой ветви и режиме;не подменять паспортной номинальной подачей | calibration, fluid properties, installation, dynamic response, integration interval |
| ELECTRICAL | Питание/потребление/энергия | Будущий измерительный комплекс с фазовой/временной привязкой и отдельным пуском/работой/паузой | calibration, phase/time alignment, bandwidth, transient capture, integration window |
| MOTION | Движение/позиция/обратная связь | Независимое наблюдение положения/движения и команды;достоверность канала не выводится из команды | calibration, spatial reference, resolution, latency, alignment, failure detection |
| ENVIRONMENT | Среда/воздействия | Будущие методики по выбранной среде/опасности;условия площадки не считаются измеренными | calibration, location, temporal variation, sampling, method applicability |
| EVENT | События/качество данных | Синхронный журнал с исходными данными и независимым основанием интерпретации;потери сохраняются | timestamp alignment, source integrity, completeness, diagnostic coverage |
| DOCUMENT | Документальное свидетельство | Аудит точных версий/хэшей/области и компетентного независимого рассмотрения;не юридическая или физическая аттестация | scope completeness, source authority, revision control, reviewer competence |
