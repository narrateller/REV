"""Render documentary source references and UNKNOWN interfaces. No engineering evaluation.

Run from /workspace/REV with .venv/bin/python. Only this directory's tables are
written; existing source inputs/registries/CAD and earlier evidence are not edited.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = 'f731910273b47f46c6d45114cecd76de6fa8adf9'
AUTH = '80f1028c25d1c4344c0115b7908e02346d895701'
SESSION = '6afb4750-7918-8191-8569-77b5b0c41050'
sys.path.insert(0, str(ROOT / 'scripts'))
from repo_support import flatten  # noqa: E402


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    files = {
        'VAR': 'verification/r4_cycle_interfaces/proposal/force_variants.json',
        'BIND': 'verification/r4_cycle_interfaces/proposal/baseline_bindings.json',
        'REG': 'params/registry.yaml',
        'RAW': 'verification/r3_force_path/analysis/params/registry.yaml',
        'FB': 'verification/r3_force_path/analysis/free_bodies.md',
        'GAPS': 'verification/r3_force_path/input_gaps.md',
        'CI': 'verification/r4_cycle_interfaces/proposal/unknown_inputs.json',
        'STATE': 'verification/r3_force_path/analysis/state_matrix.json',
        'R5': 'verification/r5_force_path_output_review/review.md',
        'CYCLE': 'verification/r4_cycle_interfaces/proposal/interfaces.md',
        'TASK': 'verification/pr48_integration/R4_task_proposal.md',
        'R1': 'decisions/R1-R4-AUDIT-SYMBOLIC-CONTINUATION.md',
    }
    catalog = {}
    for key, path in files.items():
        commit = AUTH if key == 'R1' else BASE
        raw = git('show', commit + ':' + path)
        catalog[key] = {'path': path, 'commit': commit,
                        'git_blob': git('rev-parse', commit + ':' + path).decode().strip(),
                        'sha256': hashlib.sha256(raw).hexdigest()}
    write('source_catalog.json', catalog)
    variants = json.loads((ROOT / files['VAR']).read_text())['variants']
    bindings = json.loads((ROOT / files['BIND']).read_text())['rows']
    scoped = flatten(yaml.safe_load((ROOT / files['RAW']).read_text()))
    states = json.loads((ROOT / files['STATE']).read_text())

    def ref(source, selector, identifier=None, revision=None):
        return {'source': source, 'path': catalog[source]['path'],
                'commit': catalog[source]['commit'], 'selector': selector,
                'source_id': identifier, 'revision': revision,
                'revision_basis': ('registered source revision' if revision is not None else
                                   'no numeric revision in source; pinned commit/blob, not invented revision')}

    formulas = {
        'KIN': {'expression': 'Δx_rod = Δx_crosshead = Δx_carrier = Δx_punch',
                'source': ref('VAR', 'variants[].kinematics'),
                'conditions': 'Унаследованная ASSUMED жёсткая захваченная осевая цепь без изменения передаточного отношения; не доказательство реальных DOF/кинематики.',
                'missing': ['реальные joints/люфты/деформации', 'непрерывные позы/закрепления по всему ходу']},
        'AXIAL': {'expression': 'N = −F_x',
                  'source': ref('FB', 'Два именованных идеальных нагрузочных случая'),
                  'conditions': 'Только идеальная последовательная квазистатическая цепь S_WORK/S_RETURN; полные source нагрузки, не реальные F(q,t); guide/channel повторно не добавлять, V2 не делить пополам.',
                  'missing': ['места приложения фазовых F(q,t)', 'масса/инерция/трение/новые сопротивления', 'существование захваченных связей']},
        'MOMENT': {'expression': 'r × F = (0, e_z·F_x, −e_y·F_x)',
                   'source': ref('FB', 'Эксцентриситет и направляющие'),
                   'conditions': 'Осевое F_x и смещение (e_y,e_z); обе плоскости. Это символ исходного источника, не вычисленный момент. V1 также имеет UNKNOWN несоосность.',
                   'missing': ['e_y(q)', 'e_z(q)', 'F(q,t)', 'локальные оси каждого звена/закрепления']},
        'GUIDE': {'expression': 'R1 = F_x·e_y/a',
                  'companion_expression': 'R0 = −F_x·e_y/a',
                  'source': ref('FB', 'Эксцентриситет и направляющие'),
                  'conditions': 'Только выделенная идеальная пара направляющих с шагом a, без прочей поперечной нагрузки; не распределение по реальным кареткам/болтам. Общий многоопорный случай UNKNOWN.',
                  'missing': ['шаг/ориентации/контактные стороны опор', 'прочие силы/преднатяг', 'совместность деформаций и жёсткости']},
        'ROD_NOMINAL': {'expression': 'N/(pi*d²/4)',
                        'source': ref('FB', 'Устойчивость и напряжения'),
                        'conditions': 'Только номинальное цельное круглое сечение исходного штока; не сечение носителя/портала, не учтены резьба/выточки/изгиб/концентрации/усталость/допуски.',
                        'missing': ['реальное сечение/материал/дефекты штока', 'изгиб/местные усилия/критерии']},
        'SECTION': {'expression': 'N/A, M/W',
                    'source': ref('FB', 'Устойчивость и напряжения'),
                    'conditions': 'В источнике это UNKNOWN-компоненты носителя; совместный расчёт/допускаемое напряжение не определены. A/I_y/I_z/W_y/W_z/J носителя и портала не выводятся из d штока.',
                    'missing': ['раздельные сечения/главные оси звеньев', 'материалы/E/состояние/критерии', 'локальные N/Q/M и контакты']},
        'EULER': {'expression': 'Pcr = pi²·E·I/(K·L_free(q))²',
                  'source': ref('FB', 'Устойчивость и напряжения'),
                  'conditions': 'Только применимый упругий стройный стержень с обоснованными закреплениями. Обе главные плоскости, дефекты/внецентренность/второй порядок и местная устойчивость отдельно. Ни Pcr, ни capacity/margin не вычислены.',
                  'missing': ['E', 'I_y/I_z', 'K/закрепления', 'L_free_rod(q) и L_free_carrier(q)', 'дефекты/стройность/критерии/реальные фазовые силы']},
    }
    write('symbolic_dependencies.json', formulas)

    # These are documentary row keys, not engineering parameter IDs or new assumptions.
    definitions = [
        ('datum_motion', 'Базы камеры/ось пуансона → осевая цепь',
         'Источник объявляет +x к выходу, +y к стороне цилиндра V2, +z вверх; O — задняя плоскость камеры/ось. Source strokes остаются неизменными.',
         'KIN', ['E_Y', 'E_Z'],
         ['chamber.width', 'chamber.height', 'product.length', 'chamber.length', 'material.occupied_length', 'stroke.approach', 'stroke.work', 'stroke.eject', 'stroke.return'],
         ['фактическая привязка O/локальных осей', 'начальная поза x_P0', 'траектории полных/частичных и промежуточных поз', 'e_y(q), e_z(q)'],
         ['R4', 'R3'], 'Сверить базы/знаки и непрерывность всех поз, не приравнивать PF к P0.',
         'Желаемая осевая передача из исходной гипотезы; реальные разрешённые/запрещённые DOF UNKNOWN.'),
        ('cylinder_frame', 'Корпус цилиндра → монтаж → рама',
         'Именованная ветвь замыкания силы; исходный bore_min/rod не выбирает серийное изделие или крепление.',
         'AXIAL', ['FRAME_STIFFNESS'], ['cylinder.bore_min', 'cylinder.rod_diameter'],
         ['паспорт/COTS revision и локальный источник', 'геометрия монтажных интерфейсов/портов', 'шарнир/жёсткая опора и DOF', 'допустимая боковая нагрузка', 'контакт/жёсткость/направление реакции'],
         ['R3', 'R4', 'R6', 'R5'], 'Получить проверенные COTS interfaces; проверить передачу обоих знаков и опирание.',
         'Тип опоры/DOF/контактные стороны UNKNOWN; реакция корпуса условно противоположна осевому спросу, обратный режим отдельно.'),
        ('rod_grip', 'Шток → захваченный joint',
         'В S_WORK/S_RETURN требуется двусторонний захват; односторонний толкатель не передаёт растяжение.',
         'AXIAL', ['JOINT_RESISTANCE', 'JOINT_MOMENT_RESISTANCE'], ['cylinder.rod_diameter', 'load.work_peak', 'load.return_required'],
         ['резьба/палец/болты/сварка и геометрия группы', 'контактные стороны/люфт/преднатяг', 'материал/допуски', 'локальные N/Q/M и боковая нагрузка'],
         ['R3', 'R4', 'R6', 'R5'], 'Проследить оба знака нагрузки через каждый joint; не делить усилие по крепежу поровну.',
         'Требуется захват work/return; фактическая реализация, контакт/DOF UNKNOWN.'),
        ('grip_transfer', 'Захват → траверса или портал',
         'Передаётся полный исходный осевой спрос; моментная ветвь требует собственных плеч/связей.',
         'MOMENT', ['E_Y', 'E_Z', 'JOINT_MOMENT_RESISTANCE'], ['load.work_peak', 'load.return_required'],
         ['оси и точки приложения', 'e_y(q), e_z(q)', 'геометрия двусторонних joints', 'локальные главные оси/сечения и податливости'],
         ['R4', 'R3', 'R5', 'R6'], 'Проверить замыкание пространственного момента и обратных моментов по обоим направлениям.',
         'Обе контактные стороны work/return необходимы; реальные вращательные/поступательные DOF UNKNOWN.'),
        ('transfer_carrier', 'Траверса/портал → отдельный направляемый носитель',
         'Носитель — самостоятельное звено, не гидравлический шток; исходная гипотеза связывает осевые перемещения.',
         'KIN', ['CARRIER_FREE_LENGTH_MAX', 'ROD_FREE_LENGTH_MAX', 'END_FACTOR'], ['stroke.work', 'stroke.return'],
         ['раздельные L_free_rod(q) и L_free_carrier(q)', 'координаты/активные участки опор во всех позах', 'тип/DOF joints', 'промежуточные/частичные позы'],
         ['R4', 'R3', 'R5'], 'Задать непрерывные символические области полного хода; maxima RAW IDs не задают функции по q.',
         'Только унаследованная жёсткая захваченная связь; реальная непрерывность/ограничения DOF UNKNOWN.'),
        ('carrier_punch', 'Носитель → joint → пуансон → камера',
         'Топологически пуансон отделён от штока; известны только происхождение source сечения камеры и заданного спроса.',
         'AXIAL', ['CARRIER_AREA', 'CARRIER_I', 'JOINT_RESISTANCE'], ['chamber.width', 'chamber.height', 'load.work_peak', 'load.return_required'],
         ['сечение перехода/стыка и допуски', 'геометрия захвата обоих знаков', 'активные контакты/зазоры камеры', 'локальные N/Q/M', 'материал/состояние'],
         ['R4', 'R3', 'R6', 'R5'], 'Отделить номинальную равномерную тягу S_WORK от реальной эпюры материала/локального контакта.',
         'Тип стыка и фактические DOF/контактные стороны UNKNOWN; обратный ход требует отдельного захвата.'),
        ('carrier_guides', 'Носитель → направляющие',
         'Источник выделяет идеальную моментную пару; это не полная реакция всех реальных направляющих.',
         'GUIDE', ['GUIDE_SPAN', 'GUIDE_PRELOAD', 'FRICTION_FORCE', 'E_Y', 'E_Z'], ['load.work_peak', 'load.return_required'],
         ['число/координаты/направления опор', 'шаг a и обе плоскости', 'контактные стороны/люфт/преднатяг', 'вес/инерция/трение', 'совместность и жёсткости'],
         ['R4', 'R3', 'R5'], 'Проверить знак/смену контакта; многоопорная система требует совместности, не равного распределения.',
         'Желаемое осевое движение не задаёт фактических поперечных/вращательных DOF; всё опирание UNKNOWN.'),
        ('guides_frame', 'Направляющие/опоры → крепления → рама',
         'Нагрузки на раму противоположны силам на движущем теле только в выделенной идеальной паре.',
         'GUIDE', ['SUPPORT_RESISTANCE', 'FRAME_STIFFNESS', 'JOINT_RESISTANCE'], ['load.work_peak', 'load.return_required'],
         ['геометрия групп опор/крепежа', 'материалы/контакт/преднатяг', 'жёсткость и начальные дефекты', 'опорные условия обеих плоскостей'],
         ['R4', 'R6', 'R3', 'R5'], 'Связать опоры с рамой по контактам и обоим знакам; срез/отрыв/смятие и совместность NOT_RUN.',
         'Крепления/DOF/контактные стороны UNKNOWN; формула пары не доказывает несущую способность.'),
        ('material_reaction', 'Пуансон/материал → реакционный узел A или B',
         'Существует только условно обозначенная реакционная ветвь; фактическая доступность реакции UNKNOWN.',
         'AXIAL', ['REACTION_AVAILABLE', 'FRICTION_FORCE'], ['load.work_peak', 'material.occupied_length'],
         ['фазовые F(q,t) и места приложения', 'наличие/стороны активного контакта', 'остаточная сила/пружинение/трение', 'условия удержания материала'],
         ['R2', 'R3', 'R4', 'R5'], 'Для каждой фазы подтвердить собственный контакт; source peak не назначать всем состояниям.',
         'Work и return не обязаны иметь один и тот же контакт с обратным знаком; фактическое замыкание UNKNOWN.'),
        ('reaction_frame', 'Реакционный узел → замок/опоры → рама',
         'Рама должна замыкать реакционную ветвь только при существующем контакте/удержании.',
         'MOMENT', ['SUPPORT_RESISTANCE', 'FRAME_STIFFNESS', 'JOINT_MOMENT_RESISTANCE'], ['load.work_peak', 'load.return_required'],
         ['координаты/ориентации реакционных опор', 'контактные стороны/направления', 'joints/люфт/преднатяг', 'сечения/материал/жёсткость рамы', 'фазовые связи'],
         ['R4', 'R3', 'R6', 'R5', 'R2'], 'Отделить замыкание силы от прочности/устойчивости и отдельно проверить возврат/снятие реакции.',
         'Фиксация/освобождение DOF и контактов UNKNOWN; общий силовой контур — требование, не доказанный механизм.'),
        ('sections_stability', 'Шток / носитель / траверса-портал / рама — раздельные сечения',
         'Source d относится только к штоку; scalar RAW CARRIER_I/W и MAX длины не определяют главные плоскости или функции хода.',
         'EULER', ['CARRIER_AREA', 'CARRIER_I', 'CARRIER_W', 'CARRIER_J', 'ELASTIC_MODULUS', 'ALLOWABLE_STRESS', 'END_FACTOR', 'CARRIER_FREE_LENGTH_MAX', 'ROD_FREE_LENGTH_MAX'], ['cylinder.rod_diameter'],
         ['раздельные A/I_y/I_z/W_y/W_z/J каждого звена', 'материал/E/дефекты/состояние', 'закрепления K и L_free(q) обоих звеньев', 'локальные N/Q/M, стройность, критерии и второй порядок'],
         ['R4', 'R6', 'R5', 'R1', 'R3'], 'Определить применимость, главные оси и критерии до численной оценки; capacity/margins UNKNOWN.',
         'Геометрия сечений/материалы/DOF опирания UNKNOWN. Номинальная формула штока не переносится на носитель/портал.'),
        ('envelopes_service', 'Шток/траверса/портал/носитель ↔ камера, подача, обслуживание',
         'Источник задаёт только невычисленное envelope-требование и маршрут обслуживания.',
         None, ['E_Y', 'E_Z', 'CARRIER_FREE_LENGTH_MAX', 'ROD_FREE_LENGTH_MAX'], ['stroke.approach', 'stroke.work', 'stroke.eject', 'stroke.return', 'chamber.width', 'chamber.height'],
         ['полные swept volumes и базы', 'rear/side clearance', 'подача/камера/выдача/демонтажные траектории', 'люфты/допуски/сервисные пространства'],
         ['R4', 'R3', 'R6', 'R5'], 'Проверить полные/частичные/промежуточные/сервисные позы и обе плоскости; фактический collision/sweep NOT_RUN.',
         'Контактные/неконтактные стороны и ограничения движения UNKNOWN; envelope-требование не collision CLEAR.'),
        ('receiver_cycle', 'Выход/приёмник ↔ возврат, refill/reset и READY',
         'Известны только исходные ссылки fixed-budget главной оси и документальные требования к приёму/остаткам/восстановлению.',
         None, ['MOVING_MASS', 'ACCELERATION', 'FRICTION_FORCE', 'REACTION_AVAILABLE'],
         ['product.length', 'stroke.eject', 'stroke.return', 'phase.approach.time', 'phase.approach.speed', 'phase.work.time', 'phase.work.speed', 'phase.eject.time', 'phase.eject.speed', 'phase.return.time', 'phase.return.speed', 'time.cycle_budget'],
         ['реальная выходная граница/приёмник/остатки', 'контакты возврата и удержания', 'фазовые нагрузки/паузы/ресурсы', 'массы/ускорения/потери/аварии', 'условия сброса и повторного старта'],
         ['R1', 'R2', 'R3', 'R4', 'R5'], 'Сопоставить все исходные состояния; возврат оси не доказывает READY, fixed-budget не время всего цикла.',
         'Движения/контакт с продуктом и удержание в каждой фазе UNKNOWN; совместимость/аварийные DOF NOT_RUN.'),
    ]
    ci_groups = {
        'datum_motion': ['CI-X_P0', 'CI-X_REFILL_PUNCH', 'CI-X_COLUMN_GATHER', 'CI-X_B_GATHER'],
        'cylinder_frame': ['CI-CYLINDER_EXTERNAL_MOUNTS'],
        'rod_grip': ['CI-CYLINDER_EXTERNAL_MOUNTS'],
        'grip_transfer': ['CI-LATERAL_OFFSET_E'],
        'transfer_carrier': ['CI-CARRIER_LENGTH'],
        'carrier_punch': ['CI-CARRIER_SECTION'],
        'carrier_guides': ['CI-GUIDE_SPAN'],
        'guides_frame': ['CI-GUIDE_SPAN'],
        'material_reaction': ['CI-A_REACTION', 'CI-B_OPEN_RESET'],
        'reaction_frame': ['CI-A_REACTION', 'CI-B_OPEN_RESET'],
        'sections_stability': ['CI-CARRIER_SECTION', 'CI-CARRIER_LENGTH'],
        'envelopes_service': ['CI-REAR_CLEARANCE', 'CI-LATERAL_OFFSET_E', 'CI-DOSER_STROKE_Y',
                              'CI-GATE_STROKE_Y', 'CI-SERVICE_LIFT_MASS_ACCESS'],
        'receiver_cycle': ['CI-EXIT_PLANE_AND_RECEIVER', 'CI-AUX_RESOURCES'],
    }
    rows = []
    for variant in variants:
        vid = variant['id']
        family, option = vid.split('-')
        selected = {b['proposed_cad_field']: b for b in bindings if b['scenario'] == 'BASE_' + family}
        raw_prefix = 'R3F_' + family + '_' + option + '_'
        for key, nodes, known, formula, suffixes, fields, missing, recipients, next_check, connection in definitions:
            if key == 'grip_transfer':
                nodes = ('Захват → внешняя задняя траверса V1' if option == 'V1'
                         else 'Захват → портальная траверса V2')
            elif key == 'transfer_carrier':
                nodes = ('Задняя траверса V1 → отдельный направляемый носитель' if option == 'V1'
                         else 'Портал V2 → отдельный направляемый носитель')
            elif key == 'material_reaction':
                nodes = ('Пуансон/материал → зажим/канал/удерживаемый столб A (наличие UNKNOWN)' if family == 'A'
                         else 'Пуансон/материал → закрытый упор B (контакт UNKNOWN)')
            elif key == 'reaction_frame':
                nodes = ('Зажим/канал/реакционный узел A → связи рамы' if family == 'A'
                         else 'Упор B → замок/опоры → рама')
            elif key == 'receiver_cycle':
                nodes = ('Выход/приёмник → удержание/возврат/refill A' if family == 'A'
                         else 'Выход/приёмник → возврат/close/relock/reset B')
            refs = [ref('VAR', 'variants[id=' + vid + ']', vid), ref('FB', 'named force loop and limitations'),
                    ref('GAPS', 'missing input groups'), ref('R5', 'Отдельный вердикт для R4 и обязательные входы')]
            raw_ids = [raw_prefix + s for s in suffixes]
            refs += [ref('RAW', 'domains.*.' + rid, rid, scoped[rid]['revision']) for rid in raw_ids]
            refs += [ref('BIND', 'rows[scenario=BASE_' + family + ',proposed_cad_field=' + f + ']',
                         selected[f]['parameter_id'], selected[f]['revision']) for f in fields]
            refs += [ref('REG', 'domains.*.' + selected[f]['parameter_id'],
                         selected[f]['parameter_id'], selected[f]['revision']) for f in fields]
            ci_ids = [x for x in ci_groups[key] if x != ('CI-B_OPEN_RESET' if family == 'A' else 'CI-A_REACTION')]
            if key == 'datum_motion':
                foreign_gather = 'CI-X_B_GATHER' if family == 'A' else 'CI-X_COLUMN_GATHER'
                ci_ids = [x for x in ci_ids if x != foreign_gather]
            refs += [ref('CI', 'unknowns[id=' + x + ']', x) for x in ci_ids]
            if key in ('datum_motion', 'receiver_cycle'):
                refs.append(ref('CYCLE', 'bases / A startup / B open-reset / partial return'))
            specific = ('V1: задняя компоновка/длинный отдельный носитель; e_y/e_z(q) UNKNOWN, не нули.'
                        if option == 'V1' else
                        'V2: боковая компоновка с порталом; e_y/e_z(q), обе плоскости/местный изгиб/кручение UNKNOWN; полную силу не делить.')
            reaction = ('A: startup без столба не имеет доказанной реакции; зажим/канал/столб, retention/refill и обратное сопротивление требуют своих контактов.'
                        if family == 'A' else
                        'B: только закрытый контакт упора/замка условно реакционен; unload/unlock/open/reset и возврат открытого узла требуют собственных условий/остаточных нагрузок.')
            symbolic = ([formula] if formula else [])
            if key == 'sections_stability':
                symbolic += ['SECTION', 'ROD_NOMINAL']
            row = {'row_key': vid + '/' + key, 'variant': vid, 'interface': nodes,
                   'node_axes': 'Объявленные +x/+y/+z исходной схемы; локальные базы и ориентации узлов UNKNOWN.',
                   'connection_DOF_contact_sides': connection,
                   'bidirectional_work_return': 'Обязательны соответствующие связи work/return; фактические контакты и способность передачи обоих знаков UNKNOWN.',
                   'known_source_scope': known, 'variant_specific_conditions': specific,
                   'reaction_phase_conditions': reaction, 'source_references': refs,
                   'symbolic_dependency_refs': symbolic,
                   'unresolved_function_symbols': ['e_y(q)', 'e_z(q)', 'L_free_rod(q)', 'L_free_carrier(q)'],
                   'unknown_arguments': [{'argument': x, 'status': 'UNKNOWN', 'value': None} for x in missing],
                   'functional_data_recipients': recipients, 'next_check': next_check,
                   'actual_geometry': 'UNKNOWN', 'physical_evaluation': 'NOT_RUN',
                   'source_raw_ids': raw_ids, 'source_binding_fields': fields}
            row['source_calculation_references'] = [
                {'parameter_id': selected[f]['parameter_id'], 'revision': selected[f]['revision'],
                 'engineering_sha256': selected[f]['engineering_sha256'],
                 'path': selected[f]['source'], 'commit': BASE}
                for f in fields]
            if key == 'envelopes_service':
                row['inherited_unevaluated_constraint'] = variant['envelope_requirement']
                row['inherited_service_requirement'] = variant['service']
            rows.append(row)
    write('interfaces.json', {'scope': 'DOCUMENTARY_SYMBOLIC_ONLY; no new engineering values/scenarios',
          'author_sessions': [SESSION], 'authority_C': AUTH, 'audited_main': BASE,
          'no_new_quantitative_assumptions': True,
          'source_id_note': 'RAW IDs remain scoped RAW/null; CI/document/variant selectors have no registered revision, so commit/blob is used. No new parameter IDs.',
          'rows': rows})
    unknown_index = []
    for identifier, parameter in scoped.items():
        if not identifier.startswith('R3F_') or parameter['lifecycle'] != 'RAW':
            continue
        linked = [r for r in rows if identifier in r['source_raw_ids']]
        unknown_index.append({'source': ref('RAW', 'domains.*.' + identifier,
                                           identifier, parameter['revision']),
                              'status': 'UNKNOWN', 'source_lifecycle': 'RAW', 'value': None,
                              'source_unknown_reason': parameter['unknown_reason'],
                              'interface_rows': [r['row_key'] for r in linked],
                              'functional_data_recipients': sorted({x for r in linked
                                                                   for x in r['functional_data_recipients']}),
                              'note': 'Source index only; not a new registry or quantitative assumption.'})
    write('unknown_index.json', unknown_index)

    mapped = []
    for state in states:
        phase = state['state']
        vid = state['variant']
        family = vid.split('-')[0]
        interfaces = ['datum_motion', 'cylinder_frame', 'rod_grip', 'grip_transfer',
                      'transfer_carrier', 'carrier_punch', 'carrier_guides', 'guides_frame',
                      'material_reaction', 'reaction_frame', 'sections_stability', 'envelopes_service']
        if phase in ('eject', 'eject_open', 'return_full', 'return_full_open', 'refill',
                     'ready', 'jam_emergency', 'close_relock_reset'):
            interfaces += ['receiver_cycle']
        if phase in ('startup_empty', 'gather_partial', 'refill'):
            requirement = ('A startup/partial/refill: сначала источник реакции и сохранение/удержание материала; нельзя предположить существующий столб.' if family == 'A' else
                           'B gather: закрытый упор/замок и сохранение partial inventory; частичный возврат не полный исходный stroke.')
        elif phase in ('hold_unload', 'unlock', 'stop_open'):
            requirement = ('A hold/unload/retention: фазовые контакты/нагрузки/пружинение UNKNOWN; порядок ослабления зажима не задан.' if family == 'A' else
                           'B unload → unlock → open: остаточная нагрузка и разгрузка/контакт/удержание отдельно UNKNOWN; низкое давление/положение не разрешение.')
        elif phase == 'close_relock_reset':
            requirement = 'B close/relock/reset: приём/остатки, collision, механическое замыкание и отдельное свидетельство RESET_CURRENT; команда reset не результат.'
        elif phase in ('eject', 'eject_open', 'return_full', 'return_full_open'):
            requirement = 'Выдача/возврат: контакт/сопротивление/удержание, приёмник/остатки и двусторонняя цепь отдельно; возврат не рабочая реакция с обратным знаком.'
        elif phase == 'jam_emergency':
            requirement = 'Заедание/авария: свои контакты, торможение, удержание/остаточные нагрузки и адресное восстановление; source peak не аварийный спектр.'
        elif phase == 'ready':
            requirement = 'READY не следует из позы оси/таймера: текущие material/receiver/geometry/resource и сохранённые отказы; physical READY NO-GO.'
        else:
            requirement = 'Подход/рабочая фаза: собственные F(q,t), активные контакты и L_free(q)/e(q) во всех внутренних позах; source WORK_PEAK лишь именованный тест спроса.'
        mapped.append({'source_state': state,
                       'source_reference': ref('STATE', 'variant=' + vid + ';state=' + phase),
                       'interface_row_keys': [vid + '/' + x for x in interfaces],
                       'contact_and_load_requirement': requirement,
                       'missing_arguments': ['фазовые F(q,t) и приложения', 'активные контактные стороны/опоры',
                                             'e_y/e_z(q), L_free_rod/carrier(q), частичные и промежуточные позы',
                                             'масса/ускорение/трение/остаточная нагрузка/ресурсы'],
                       'functional_data_recipients': ['R2', 'R3', 'R4', 'R5', 'R6', 'R1'],
                       'review_next': 'Сначала получить фазовые входы/контакты; затем независимая проверка применимости, не решать состояние из source_reference.',
                       'actual_solution': 'NOT_RUN', 'actual_force': None,
                       'actual_moment': None, 'actual_capacity_margin': None})
    write('state_dependencies.json', {'scope': 'Exact source states + documentary dependencies only; not a solver', 'rows': mapped})

    # Readable tables use source catalog aliases; full commit/path/selector/ID/revision
    # is also repeated in every machine-readable reference in interfaces.json.
    md = '# Символическая таблица интерфейсов четырёх вариантов\n\n'
    md += ('WARNING / DOCUMENTARY_SYMBOLIC_ONLY. Числа не подставляются; новые размеры, материалы/E, '
           'диапазоны, допуски, силы, сечения или количественные ASSUMED не назначены. '
           'Все actual geometry UNKNOWN / physical evaluation NOT_RUN. '
           'Известно только происхождение и условная топология, а не фактические связи.\n\n'
           'Базы/оси: исходные +x к выходу, +y к стороне цилиндра V2, +z вверх; '
           'абсолютные O, локальные оси/контакты/DOF UNKNOWN. q обозначает только '
           'полный исходный рабочий/обратный ход, частичные и промежуточные позы, '
           'без новых численных диапазонов. L_free_rod(q) и L_free_carrier(q) раздельны; '
           'MAX RAW ID не задаёт их функций или совпадение максимумов с пиком силы. '
           'Один scalar CARRIER_I/W не определяет I_y/I_z/W_y/W_z, а d штока '
           'не определяет сечение носителя/портала.\n\n')
    md += '## Точные источники\n\n| Alias | Файл | Commit |\n|---|---|---|\n'
    for key, source in catalog.items():
        md += '| ' + key + ' | ' + source['path'] + ' | `' + source['commit'] + '` |\n'
    md += ('\nID@revision в таблице — только существующая запись source. VAR/FB/GAPS/R5/CYCLE/STATE '
           'без numeric revision закреплены указанным commit/blob, revision не выдумывается. '
           'Все точные selectors/blobs/SHA256 и полные ссылки каждой строки — source_catalog.json/interfaces.json.\n\n')
    for variant in variants:
        vid = variant['id']
        md += '## ' + vid + ' — ' + variant['title'] + '\n\n'
        md += '| Интерфейс / оси, связь, DOF и стороны | Источники ID@revision (commit по alias выше) | Известное | UNKNOWN / аргументы | Зависимость и применимость | Адресаты / следующая проверка |\n|---|---|---|---|---|---|\n'
        for row in (x for x in rows if x['variant'] == vid):
            identities = '; '.join(dict.fromkeys(r['source'] + ':' + (r['source_id'] + ('@' + str(r['revision']) if r['revision'] is not None else '')
                                      if r['source_id'] else r['selector']) for r in row['source_references']))
            symbolic = '; '.join(row['symbolic_dependency_refs']) or 'Неподдержанная зависимость UNKNOWN'
            if 'inherited_unevaluated_constraint' in row:
                symbolic += '; исходное невычисленное требование: ' + row['inherited_unevaluated_constraint']
            cells = [row['row_key'] + ': ' + row['interface'] + '. ' + row['node_axes']
                     + ' ' + row['connection_DOF_contact_sides'] + ' ' + row['bidirectional_work_return'],
                     identities, row['known_source_scope'], '; '.join(x['argument'] for x in row['unknown_arguments']),
                     symbolic + '. ' + row['variant_specific_conditions'] + ' ' + row['reaction_phase_conditions'],
                     '/'.join(row['functional_data_recipients']) + ': ' + row['next_check']]
            md += '| ' + ' | '.join(c.replace('|', '\\|').replace('\n', ' ') for c in cells) + ' |\n'
    md += ('\n## Условия всех символических записей\n\nФормулы ниже только процитированы из источников. '
           'Записи e_y/e_z(q) и L_free_rod/carrier(q) — перечень необходимых UNKNOWN функций, не новые определённые зависимости.\n\n')
    for name, f in formulas.items():
        md += '### ' + name + '\n\n`' + f['expression'] + '`'
        if 'companion_expression' in f:
            md += '; `' + f['companion_expression'] + '`'
        md += '. Источник: ' + f['source']['source'] + ', ' + f['source']['selector'] + '.\n\n' + f['conditions']
        md += ' Недостаёт: ' + '; '.join(f['missing']) + '. Все оценки NOT_RUN.\n\n'
    md += ('Адресаты — функциональные получатели запроса данных, не назначения чужих claims/сроков. '
           'Реальные неизвестные не повышаются в зрелости и не получают нулевые значения. '
           'Независимый OUTPUT-review этого C пока NOT_RUN; запрос на exact C хранится следующим H.\n')
    (HERE / 'interfaces.md').write_text(md)
    md = ('# Сопоставление исходных состояний с интерфейсами\n\n'
          'Все 42 source строки сохранены в state_dependencies.json без изменения исходных полей. '
          'Ни одна строка не решена; F/M/reactions/capacity/margins UNKNOWN/NOT_RUN. '
          'Source_reference WORK_PEAK/RETURN_REQUIRED — именованный тест спроса, не сила фазы. '
          'Для всех строк нужны фазовые аргументы и проверка из JSON; адресаты функциональные, не claims.\n\n'
          '| Вариант / source state | Исходная reference | Интерфейсы (полные row keys в JSON) | Требуемый контакт/нагрузка | Статус |\n|---|---|---|---|---|\n')
    for row in mapped:
        s = row['source_state']
        md += '| ' + s['variant'] + ' / ' + s['state'] + ' | ' + str(s['source_reference']) + ' | ' + ', '.join(x.split('/')[1] for x in row['interface_row_keys']) + ' | ' + row['contact_and_load_requirement'] + ' | UNKNOWN / NOT_RUN |\n'
    (HERE / 'state_dependencies.md').write_text(md)
    print('Rendered documentary rows:', len(rows), '; source states:', len(mapped), '; no engineering values assigned')


if __name__ == '__main__':
    main()
