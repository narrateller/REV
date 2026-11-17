"""Render a documentary reference candidate; no machine model or design calculation."""
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import os
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = '3353de6c9fc699fbd565f1ce63cebedad3137a12'
SESSION = '6afb300b-1540-8191-a5c4-be1a684c20e0'
SOURCES = {
    'BP500': ('sources/raw/Target_object_BP500.pdf', [3, 4]),
    'E55': ('sources/raw/additional_Prodeco_E55.pdf', [5, 14]),
    'WEIMA': ('sources/raw/additional_Weima200.pdf', [7, 18]),
    'ARS': ('sources/raw/additional_Ars_Rst_500.pdf', [17]),
}
# Numeric tokens below are SOURCE declarations. SI values are exact unit conversions.
# They are never passed to an engineering model or promoted to the active registry.
# key, source, page, printed value, printed unit, SI value, SI unit, source locator, application
FIELDS = [
 ('BPR_MOISTURE_MIN','BP500',3,6,'%',0.06,'1','Basic information: 6-14% humidity','PRIMARY_TARGET_ENVELOPE'),
 ('BPR_MOISTURE_MAX','BP500',3,14,'%',0.14,'1','Basic information: 6-14% humidity','PRIMARY_TARGET_ENVELOPE'),
 ('BPR_AMBIENT_MIN','BP500',3,5,'degC',278.15,'K','Basic information: 5-40 C, indoors','PRIMARY_INSTALLATION_REFERENCE'),
 ('BPR_AMBIENT_MAX','BP500',3,40,'degC',313.15,'K','Basic information: 5-40 C, indoors','PRIMARY_INSTALLATION_REFERENCE'),
 ('BPR_SUPPLY_VOLTAGE','BP500',3,380,'V',380,'V','Electricals: connection required','PRIMARY_INSTALLATION_REFERENCE'),
 ('BPR_SUPPLY_FREQUENCY','BP500',3,50,'Hz',50,'Hz','Electricals: connection required','PRIMARY_INSTALLATION_REFERENCE'),
 ('BPR_SUPPLY_CURRENT','BP500',3,100,'A',100,'A','Electricals: connection required','PRIMARY_INSTALLATION_REFERENCE'),
 ('BPR_MOTOR_COUNT','BP500',3,4,'count',4,'1','Electricals: electrical motors','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_INSTALLED_POWER','BP500',3,34.2,'kW',34200,'W','Electricals: total installed power','PRIMARY_DECLARED_TOTAL_WITH_SOURCE_CONFLICT'),
 ('BPR_MAIN_MOTOR_POWER','BP500',3,30,'kW',30000,'W','Electricals / Hydraulics: main motor','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_INFEED_MOTORS_POWER','BP500',3,2.6,'kW',2600,'W','Electricals: infeed motors','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_COOLING_POWER','BP500',3,1.5,'kW',1500,'W','Electricals: cooling system','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_MAIN_MOTOR_PHASES','BP500',3,3,'count',3,'1','Hydraulics: main motor 3-phase','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_MAIN_MOTOR_SPEED','BP500',3,1500,'rpm',25,'Hz','Hydraulics: main motor; revolutions per second, not rad/s','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_CYLINDER_COUNT','BP500',3,3,'count',3,'1','Hydraulics: three cylinders','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_PUMP_COUNT','BP500',3,2,'count',2,'1','Hydraulics: two pumps','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_HYDRAULIC_PRESSURE_MAX','BP500',3,300,'bar',30000000,'Pa','Hydraulics: Max pressure','PRIMARY_HYDRAULIC_REFERENCE_NOT_MATERIAL_PRESSURE'),
 ('BPR_OIL_TANK_VOLUME','BP500',3,260,'L',0.260,'m^3','Hydraulics: oil tank capacity','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_FILTER_COUNT','BP500',3,4,'count',4,'1','Hydraulics: 4 filters from 3 micrometres','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_FILTER_FROM','BP500',3,3,'um',0.000003,'m','Hydraulics: 4 filters from 3 micrometres','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_BUNKER_OPENING_1','BP500',4,972,'mm',0.972,'m','Material infeed: opening; listed order, axes not inferred','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_BUNKER_OPENING_2','BP500',4,463,'mm',0.463,'m','Material infeed: opening; listed order, axes not inferred','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_BUNKER_HEIGHT','BP500',4,1220,'mm',1.220,'m','Material infeed: opening at height','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_BUNKER_VOLUME','BP500',4,127,'L',0.127,'m^3','Material infeed: volume','REFERENCE_CONFIGURATION_ONLY'),
 ('BPR_BRIQUETTE_SIDE_1','BP500',4,150,'mm',0.150,'m','Main compaction: briquette size; source listed order','PRIMARY_PRODUCT_TARGET'),
 ('BPR_BRIQUETTE_SIDE_2','BP500',4,60,'mm',0.060,'m','Main compaction: briquette size; source listed order','PRIMARY_PRODUCT_TARGET'),
 ('BPR_BRIQUETTE_LENGTH_MIN','BP500',4,40,'mm',0.040,'m','Main compaction: adjustable 40~110 mm','PRIMARY_PRODUCT_TARGET'),
 ('BPR_BRIQUETTE_LENGTH_MAX','BP500',4,110,'mm',0.110,'m','Main compaction: adjustable 40~110 mm','PRIMARY_PRODUCT_TARGET'),
 ('BPR_THROUGHPUT_UPPER','BP500',4,600,'units/h',1/6,'1/s','Throughput: up to 600 units of 0.83kg per hour; material dependent','PRIMARY_UP_TO_CLAIM_NOT_GUARANTEED_MINIMUM'),
 ('BPR_REFERENCE_BRIQUETTE_MASS','BP500',4,0.83,'kg',0.83,'kg','Throughput: units of 0.83kg; size and weight adjustable','PRIMARY_REFERENCE_PRODUCT_NOT_FIXED_ALL_SETTINGS'),
 ('BPR_MACHINE_DIM_1','BP500',4,2100,'mm',2.100,'m','Dimensions: installed without packing table, listed order','REFERENCE_ENVELOPE_SITE_ADAPTS'),
 ('BPR_MACHINE_DIM_2','BP500',4,1900,'mm',1.900,'m','Dimensions: installed without packing table, listed order','REFERENCE_ENVELOPE_SITE_ADAPTS'),
 ('BPR_MACHINE_DIM_3','BP500',4,2200,'mm',2.200,'m','Dimensions: installed without packing table, listed order','REFERENCE_ENVELOPE_SITE_ADAPTS'),
 ('BPR_WITH_TABLE_DIM_1','BP500',4,4860,'mm',4.860,'m','Dimensions: with packing table; other dimensions same listed source','REFERENCE_ENVELOPE_SITE_ADAPTS'),
 ('BPR_MACHINE_MASS','BP500',4,3050,'kg',3050,'kg','Dimensions: machine mass; not moving mass or support reactions','REFERENCE_MACHINE_TOTAL_ONLY'),
 ('BPR_COMPACTION_PRESSURE_LITERAL','BP500',4,'1700','kg/cm^2',None,'Pa','Main compaction: literal 1700 kg/cm2; kg vs kgf unresolved','UNIT_AMBIGUITY_NO_PRESSURE_CONVERSION'),
 ('SUPR_E55_MOISTURE_MIN','E55',14,8,'%',0.08,'1','Prescribed uses: sawdust 8-14% moisture','SUPPLEMENT_ONLY_NOT_REV_ENVELOPE'),
 ('SUPR_E55_MOISTURE_MAX','E55',14,14,'%',0.14,'1','Prescribed uses: sawdust 8-14% moisture','SUPPLEMENT_ONLY_NOT_REV_ENVELOPE'),
 ('SUPR_WEIMA_MOISTURE_MIN','WEIMA',7,8,'%',0.08,'1','Box: not below 8%, material dependent','SUPPLEMENT_ONLY_NOT_REV_ENVELOPE'),
 ('SUPR_WEIMA_MOISTURE_MAX','WEIMA',7,20,'%',0.20,'1','Box: not above 20%, material dependent','SUPPLEMENT_ONLY_NOT_REV_ENVELOPE'),
]

SUPPLEMENT = [
 ('SREF-E55-HOLD','E55',5,'2.4 PRESS TONGS: stop the material exiting during the plunger-return phase',
  'A reaction/retention, material_reaction and reaction_frame',
  'Обосновать отдельное удержание при возврате; наличие зажима в другой машине не доказывает контакт REV.'),
 ('SREF-E55-FEED','E55',5,'2.2 FEED BOX and 2.5 FEED UNIT: slide driven by a cylinder; impeller/disk linked to plunger',
  'A/B receiver_cycle and feeding interface',
  'Сравнить способы дозирования; не переносить размер цилиндра, объём бака или производительность.'),
 ('SREF-E55-MATERIAL','E55',14,'9.1 sawdust moisture; 9.2 nails, iron and metal must not fall into the press',
  'Wood preparation and contamination limits',
  'Не расширять список сырья REV полимерами из E55. Древесный пример не подтверждает свойства строительной смеси.'),
 ('SREF-WEIMA-MATERIAL','WEIMA',7,'Bestimmungsgemaesse Verwendung: wood/similar materials; moisture window material dependent',
  'Sensitivity of product quality to material and moisture',
  'Окно WEIMA остаётся сравнением; не заменять/усреднять первичное окно BP500.'),
 ('SREF-WEIMA-LEVEL','WEIMA',18,'Autom. Betrieb: switch-on by bunker level switch; switch-off after adjustable K3T delay',
  'A/B receiver_cycle and availability sensing',
  'Отделить наличие сырья от полной дозы и READY. Не заимствовать проводку/уставки/разрешение движения.'),
 ('SREF-ARS-BRANCH','ARS',17,'Flowchart: pressure switch and partial extend are separate branches',
  'B gather_partial/work/open-reset documentary branch comparison',
  'ARS относится к другой среде; различать давление и положение, не переносить силу/трение/плотность материала.'),
 ('SREF-ARS-OPEN','ARS',17,'Pressure branch: retract main ram, open door, extend main ram to eject',
  'B unload/unlock/open/eject sequence requirements',
  'Выдержка в чужой схеме не доказывает снятие остаточной реакции и не разрешает открытие REV.'),
 ('SREF-ARS-RESET','ARS',17,'Partial-extend branch: retract main ram, retract gather ram, close door',
  'B close/relock/reset and partial gather comparison',
  'Требовать собственные контакты/датчики/сброс состояния; источник не закрывает B reset/product collision.'),
]

GROUPS = {
 'E_Y':('R4','DESIGN_NOT_DEFINED','Геометрия линии действия e_y(q), локальные базы, обе ветви хода'),
 'E_Z':('R4','DESIGN_NOT_DEFINED','Геометрия линии действия e_z(q), обе плоскости и несоосность'),
 'ROD_FREE_LENGTH_MAX':('R4','DESIGN_NOT_DEFINED','Отдельная свободная длина штока и закрепления по всем позам'),
 'CARRIER_FREE_LENGTH_MAX':('R4','DESIGN_NOT_DEFINED','Отдельная свободная длина носителя; max не заменяет функцию по ходу'),
 'CARRIER_AREA':('R4','DESIGN_NOT_DEFINED','Сечение отдельного носителя; диаметр штока его не определяет'),
 'CARRIER_I':('R4','DESIGN_NOT_DEFINED','Главные моменты инерции отдельного сечения'),
 'CARRIER_W':('R4','DESIGN_NOT_DEFINED','Моменты сопротивления реального сечения и переходов'),
 'CARRIER_J':('R4','DESIGN_NOT_DEFINED','Характеристика кручения реального сечения'),
 'ELASTIC_MODULUS':('R6','MATERIAL_NOT_SELECTED','Материал/состояние/источник E; типовая сталь не назначается'),
 'ALLOWABLE_STRESS':('R5','CRITERIA_NOT_APPROVED','Материал, режимы, ресурс, стандарты и критерии допустимости'),
 'END_FACTOR':('R5','BOUNDARY_CONDITIONS_NOT_DEFINED','Фактические закрепления и применимость модели устойчивости'),
 'FRAME_STIFFNESS':('R4','DESIGN_NOT_DEFINED','Схема/сечения/соединения рамы и совместность'),
 'GUIDE_SPAN':('R4','DESIGN_NOT_DEFINED','Точки/ориентации/шаг направляющих по всем позам'),
 'GUIDE_PRELOAD':('R3','COTS_NOT_SELECTED','Исполнение направляющих, зазор/преднатяг и паспорт'),
 'JOINT_RESISTANCE':('R6','JOINT_DESIGN_NOT_DEFINED','Исполнение двустороннего стыка, контакты, крепёж/сварка и критерии'),
 'JOINT_MOMENT_RESISTANCE':('R6','JOINT_DESIGN_NOT_DEFINED','Геометрия группы/плечи/обратные моменты и материал'),
 'SUPPORT_RESISTANCE':('R5','SUPPORT_MODEL_NOT_DEFINED','Опоры/контакты/жёсткости и применимые критерии'),
 'MOVING_MASS':('R4','DESIGN_OUTPUT_NOT_AVAILABLE','Массы движущихся частей; общая масса BP500 сюда не переносится'),
 'ACCELERATION':('R3','MOTION_PROFILE_NOT_DEFINED','Собственные профили движения и аварийных режимов'),
 'FRICTION_FORCE':('R2','PROCESS_MODEL_NOT_AVAILABLE','Модель контактов/трения по фазам и её область применимости'),
 'REACTION_AVAILABLE':('R2','CONTACT_MODEL_NOT_VALIDATED','A startup/retention и B open/reset: собственные активные контакты'),
}


def dump(name, obj):
    p = HERE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    source_manifest = json.loads((ROOT / 'project/source_manifest.json').read_text())
    expected_hashes = {x['path']: x['sha256'] for x in source_manifest['sources']}
    sources = {}
    for name, (path, pages) in SOURCES.items():
        raw = (ROOT / path).read_bytes(); digest = hashlib.sha256(raw).hexdigest()
        assert digest == expected_hashes[path]
        scales = {page: (1500 if (name, page) in {('E55',14), ('WEIMA',18)} else 1900) for page in pages}
        sources[name] = dict(path=path, commit=BASE, sha256=digest, pages_read=pages,
                             page_numbering='PDF index from cover; ARS17 printed16, WEIMA7 printed6, WEIMA18 printed17',
                             method='pdftotext navigation plus direct visual inspection of rendered listed pages',
                             render_commands=['pdftoppm -f '+str(page)+' -l '+str(page)+' -scale-to '+str(scales[page])+' -png '+path+' OUTPUT' for page in pages])
    dump('source_manifest.json', dict(base_main=BASE, sources=sources,
         scope='Only listed pages inspected in this intake; no claim of full-document reread'))
    standard = ['brochure_boundary','process_medium','kinematics_and_drive','aero_thermo_fluid','geometry_mass','strength_safety_factors']
    registry = dict(schema_version='1.1', project_id='REV', mode='PROJECT', units_policy='SI',
                    domains={x:{} for x in standard})
    facts = []
    for key, source, page, printed, original_unit, value, unit, locator, use in FIELDS:
        unknown = 'Printed kg/cm^2 is not a resolved SI pressure; kgf interpretation is not established.' if value is None else None
        limitations = 'Source declaration only; no REV measurement, no tolerance/uncertainty inferred; independent source review pending.'
        if 'MOISTURE' in key:limitations += ' Wet/dry basis and measurement method UNKNOWN.'
        if 'THROUGHPUT' in key:limitations += ' Up to/material-dependent; minimum and comparable conditions UNKNOWN; no mass-rate calculation.'
        entry = dict(revision=1, name=key, value=value, unit=unit, tolerance=None, uncertainty=None,
                     unknown_reason=unknown, lifecycle='RAW', validity='CURRENT', stale_reason=None,
                     scope='REV_REFERENCE_INTAKE_CANDIDATE_ONLY', meaning=locator+'; '+limitations,
                     provenance=dict(kind='DOCUMENTARY_REFERENCE_CANDIDATE', source_ref=sources[source]['path'],
                                     locator='PDF page '+str(page)+': '+locator, source_sha256=sources[source]['sha256'],
                                     printed_value=printed, printed_unit=original_unit),
                     author=dict(role='R1', session_id=SESSION), author_sessions=[SESSION], verifier=None,
                     depends_on=[], calculation=None, evidence=[sources[source]['path'],
                     'verification/r1_force_inputs_intake/user_direction.json'], baseline_id=None,
                     history=[dict(revision=1, **{'from':None,'to':'RAW'}, actor=SESSION,
                                   reason='Source transcription and exact unit conversion only; user reference policy; no active promotion')])
        registry['domains']['brochure_boundary'][key] = entry
        facts.append(dict(id=key, revision=1, source=source, pdf_page=page, printed_value=printed,
                          printed_unit=original_unit, candidate_value_SI=value, unit=unit, application=use,
                          locator=locator, limitations=limitations))
    p = HERE / 'reference_candidate/params/registry.yaml';p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(registry, sort_keys=False, allow_unicode=True))
    dump('reference_facts.json', dict(scope='Scoped RAW source candidate, not active registry or engineering outputs',
         user_policy='reference_policy.json', source_fields=facts, numerical_machine_models_run=False))
    lines = ['# Численные декларации источников — отдельный RAW-кандидат','',
             'Ревизия каждого ID — 1 в reference_candidate/params/registry.yaml; активный реестр неизменен.',
             'Только перепись источника и точные переводы единиц; независимый review pending.','',
             '| ID кандидата | Источник / PDF | В источнике | SI-кандидат | Применение |','| --- | --- | --- | --- | --- |']
    for f in facts:
        shown = 'UNKNOWN' if f['candidate_value_SI'] is None else str(f['candidate_value_SI'])
        lines.append('| '+f['id']+' | '+f['source']+' / '+str(f['pdf_page'])+' | '+str(f['printed_value'])+' '+f['printed_unit']+' | '+shown+' '+f['unit']+' | '+f['application']+' |')
    lines += ['', 'SOURCE-POWER: объявленный total и перечень мощностей требуют согласования; исправления и новый бюджет не вычислялись.',
              'SOURCE-PRESSURE-UNIT: literal kg/cm² сохранён; SI давление UNKNOWN. Давление гидросистемы и давление на материал различаются.',
              'SOURCE-MOISTURE: BP500 первичен; E55/WEIMA — отдельные material-dependent окна, без объединения или расширения.']
    (HERE / 'reference_values.md').write_text('\n'.join(lines)+'\n')
    supplements = [dict(id=i, source=s, pdf_page=p, evidence=e, relevance=r, limit=l,
                        application='DOCUMENTED_PATTERN_ONLY', REV_parameters_assigned=False)
                   for i,s,p,e,r,l in SUPPLEMENT]
    dump('supplemental_references.json', supplements)
    lines = ['# Релевантные данные других прессов','', '| ID | Документ / PDF | Наблюдение | Применимость / предел |', '| --- | --- | --- | --- |']
    for x in supplements:lines.append('| '+x['id']+' | '+x['source']+' / '+str(x['pdf_page'])+' | '+x['evidence']+' | '+x['relevance']+'; '+x['limit']+' |')
    (HERE / 'supplemental_references.md').write_text('\n'.join(lines)+'\n')
    index = json.loads((ROOT / 'verification/r4_force_geometry/symbolic_20261116/unknown_index.json').read_text())
    grouped = defaultdict(list)
    for x in index:grouped[x['source']['source_id'].split('_',3)[3]].append(x)
    assert set(grouped) == set(GROUPS) and len(index) == 84
    packets = []
    for category, (role, status, output) in GROUPS.items():
        rows = grouped[category]
        packets.append(dict(id='INTAKE-'+category, category=category, status=status,
                            value=None, assigned_owner_session=None, due_at_utc=None,
                            owner_status='NOT_ASSIGNED', due_status='UNKNOWN', proposed_lead_function=role,
                            functional_recipients=sorted({r for x in rows for r in x['functional_data_recipients']}),
                            required_output=output, source_unknowns=rows,
                            interface_row_keys=sorted({r for x in rows for r in x['interface_rows']}),
                            physical_value_known=False, physical_input_received=False,
                            note='Future design/model input; user BP500 policy does not supply missing real geometry/material/contact data.'))
    dump('intake_register.json', dict(scope='Preclaim documentary request draft; no numerical/design execution',
         base=BASE, source_index_sha256=hashlib.sha256((ROOT/'verification/r4_force_geometry/symbolic_20261116/unknown_index.json').read_bytes()).hexdigest(),
         known_user_inputs=['BP500 target/feedstock reference','site adapts to press','other references where relevant'],
         source_unknown_count=84, group_count=len(packets), groups=packets,
         technical_completion_percent=None, calendar_completion_date=None))
    lines=['# Intake — что ещё должно быть разработано/подтверждено','',
           'Все 84 source RAW/null сохранены. Функции ниже — предложения, не назначенные исполнители; сроки UNKNOWN.',
           'Референтная цель и адаптация площадки уже получены от пользователя; готовые чертежи будущего пресса не требуются.','',
           '| Группа | Причина | Предложенная функция | Требуемый будущий выход | Владелец / срок |','| --- | --- | --- | --- | --- |']
    for x in packets:lines.append('| '+x['category']+' | '+x['status']+' | '+x['proposed_lead_function']+' | '+x['required_output']+' | NOT_ASSIGNED / UNKNOWN |')
    (HERE/'intake_register.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(reference_fields=len(facts), supplementary_records=len(supplements), intake_groups=len(packets), source_RAW_null=len(index))))


if __name__ == '__main__':
    main()
