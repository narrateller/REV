"""Render/check only the new documentary tables from their traceable JSON inputs."""
import argparse,json
from pathlib import Path
from fractions import Fraction
HERE=Path(__file__).resolve().parent

def load(name):return json.loads((HERE/name).read_text())
def fmt(x):return format(float(Fraction(str(x))),'.6g')

def documents():
    ledger=load('sources.json');claims=ledger['claims'];rows=load('cycle_table.json');issues=load('r4_backlog.json');cad=load('cad_evidence.json')
    s='# Источники: прочитанные области и предел переноса\n\nPDF-страница считается от начала файла; печатная указана отдельно. Локальный SHA не удостоверяет актуальную редакцию/подлинность изготовителя. OCR ARS — навигация; существенные страницы/flowchart прочитаны визуально. Необследованные приложения/страницы не считаются прочитанными по оглавлению.\n\n'
    for code,e in ledger['sources'].items():
        s+=f"- **{code}** `{e['path']}`; SHA-256 `{e['sha256']}`. {e['identity_and_scope']}. Содержательно: PDF {e['substantive_read_pages']}; визуально: {e['visually_read_pages']}. Остальное — навигация/NOT_READ.\n"
    s+='\n| ID | PDF / раздел / схема | Решение / короткая source-цитата или подписи | Условия и что не переносится |\n|---|---|---|---|\n'
    for id,e in claims.items():
        s+=f"| {id} | {e['source']}, PDF {','.join(map(str,e['pages']))}; {e['locator']} | {e['described_solution']} «{e['short_quote']}» | {e['applicability']} {e['not_proven_for_REV']} |\n"
    s+='\nЧисла/уставки/размеры источников не приняты как проектные входы. Source-only короткий retract ARS не является числом разгрузки REV. Квалифицированная процедура старта пустого канала A в прочитанных разделах WEIMA/PRODECO не установлена: UNKNOWN, не утверждение отсутствия любых инструкций изготовителя. Для принципиальных схем цитата из нескольких подписей соединяется «/», не выдаётся за одну строку текста.\n'
    out={'source_ledger.md':s}
    s='''# Единая сквозная таблица рабочего цикла REV A/B

Проверка документальная; новый независимый review NOT_RUN. Страницы/схемы и условия каждого source ID — [source_ledger.md](source_ledger.md), машинные данные — sources.json. Расчёт PR #39 строго C c115f75fd900525d9ddc89d85e097ac5a0f00bc1; CAD строго C 3591a5f92f78b1edea07d3fc5354fd0a99090798. Этот CAD-кандидат здесь не принимается/не интегрируется.

REV-переходы — ASSUMED функциональные предложения; критерии с недостающими данными UNKNOWN. BLOCKED_IN_DECLARED_CAD_MODEL сохраняет отрицательный результат текущей surrogate-сцены, не доказывает невозможность всех будущих архитектур. Native witnesses — опубликованные данные автора R4; независимый native/BRep replay NOT_RUN. Координатные сопоставления, ID и цепочки проверяет verify_trace.py.

Параметры приведены как существующий условный контекст, не свойство отсутствующего датчика/дозатора. Нативные CAD-local config IDs и статусы — cad_evidence.json#/variants/A или B/config. В таблице Δ — записанное перемещение начала фазы, m; времена — выписка источника, s. Полные start lo/hi, delta, exact_box, time и permission каждой фазы/узла — cad_evidence.json#/variants/A или B/phases. Числа CAD здесь не новые проектные назначения; отображение округлено, исходные Fraction строки сохранены. Отсутствие движения в UNLOAD не доказывает отсутствия возможного гидравлического сброса — схема UNKNOWN.

Ни один переход не получает физический PASS. G1 OPEN; полный реальный цикл и B opening INDETERMINATE; архитектура/ТЗ/оборудование не утверждены, физических испытаний нет.

| Строка / стадия / статус | Страница/схема → решение и условия | REV-гипотеза | Расчётный параметр / явный пробел | CAD положение/ход на точном C | Требуемое подтверждение → имеющееся evidence | Оставшийся пробел / исправление |
|---|---|---|---|---|---|---|
'''
    for row in rows:
        v=row['variant'];evidence=cad['variants'][v];cite=[]
        for id in row['sources']:
            e=claims[id];cite.append(f"{id}: {e['source']} PDF {','.join(map(str,e['pages']))}, {e['locator']}: {e['described_solution']} Условие: {e['applicability']}")
        refs=[]
        for ref in row['parameters']:
            value='UNKNOWN' if ref['value'] is None else format(ref['value'],'.8g')+' '+ref['unit']
            refs.append(value+' ['+ref['id']+'@'+str(ref['revision'])+']')
        poses=[]
        for phase in row['cad']['phases']:
            st=evidence['phases'][phase];moves=[]
            for body in st['moving_bodies']:
                if body in st['bodies']:
                    delta=st['bodies'][body]['delta'];moves.append(body+' Δ=('+','.join(fmt(x) for x in delta)+') m')
            poses.append(phase+': '+('; '.join(moves) if moves else 'нет записанного движения'))
        if row['stage']=='startup':
            st=evidence['phases'][v+'-READY'];prod=st['bodies']['product_'+v]
            poses.append('исходный product X=['+fmt(prod['lo'][0])+','+fmt(prod['hi'][0])+'] m уже присутствует')
        if row['stage']=='eject':
            summary=evidence['summary'];poses.append('rear='+fmt(summary['product_rear_after_eject'])+' m; R3 plane='+fmt(summary['r3_nominal_exit'])+' m; actual CAD exit='+fmt(summary['actual_CAD_exit'])+' m')
        if row['stage']=='resources':
            summary=evidence['summary'];poses=['CAD fixed-budget interval=['+','.join(fmt(t) for t in summary['fixed_budget_interval'])+'] s; registered budget='+fmt(summary['registered_fixed_budget_cycle'])+' s; full diagnostic='+fmt(summary['full_diagnostic_duration'])+' s (не реальный T)']
        s+='| '+row['id']+' '+row['label']+' / '+row['status']+' | '+'; '.join(cite)+' Для REV: '+row['conditions']+' | ASSUMED: '+row['rev_hypothesis']+' | '+'; '.join(refs)+'; '+row['parameter_role']+' | '+'; '.join(poses)+' | '+row['transition_required']+' Имеется: '+row['evidence']+' | '+row['gap']+' Backlog: '+', '.join(row['backlog'])+' |\n'
    s+='''
## Ключевые пределы интерпретации

Числа расчёта не менялись. Fixed-budget — согласование main-axis при явно выбранных непроверенных caps и увеличенных временах; fixed-times — другой, неутверждённый ресурс. Из новых стадий нельзя получить бесплатную одновременность/нулевую мощность пауз/реальную производительность.

SHORT_STROKE: текущий product surrogate не достигает actual CAD exit. Для A до изменения хода решить, выходит тот же вновь созданный объект или старый сегмент стационарного столба. Сохранённый столб может быть допустимым остатком, но в текущем тесте не реализован; это не позволяет скрыть отрицательный исход. В B product не должен оставаться в зоне закрытия упора: RESET этому противоречит.

Новые длительности по диагностике не назначены как реальная циклограмма. Изменение хода/передачи/нагрузки — отдельная ревизия R3 после согласования, вне этой задачи. Источники поддерживают постановку условий, а не утверждают механизм REV. [Приоритеты R4](r4_priorities.md), r4_backlog.json, [защита/метод](README.md).
'''
    out['cycle_table.md']=s
    s='''# Приоритеты исправлений R4 до очередной перестройки

Все пункты OPEN / предложения, не выполненные изменения CAD. P0 означает блокирование корректной цепочки текущей модели, не класс функциональной безопасности. Сначала материальный/переходный контракт, затем геометрия/силовой путь, затем временные/ресурсные границы и READY. Архитектура/ТЗ не утверждаются.

| ID / приоритет | Причина / затронутые строки | Конкретное изменение до перестройки | Проверяемый критерий закрытия | Зависимости / владелец |
|---|---|---|---|---|
'''
    for i in issues:
        s+='| '+i['id']+' / '+i['priority']+' '+i['title']+' | '+i['cause']+' Строки '+','.join(i['rows'])+'; источники '+','.join(i['sources'])+' | '+i['required_change']+' | '+i['acceptance']+' | '+(', '.join(i['depends_on']) or 'нет')+'; '+i['owner']+' |\n'
    s+='''
Зависимости применяются к соответствующему варианту: CYC-04(A) не требует выбора B, а CYC-05/07(B) не блокируют отдельную проверку A. Порядок: CYC-01 → CYC-02/03 → CYC-04(A) и CYC-05(B) → CYC-06 → CYC-07(B) → CYC-08 → CYC-09. Не нужно подтверждать всю физику, чтобы оформить условные интерфейсные предложения; недостающие данные не становятся готовыми размерами/разрешениями.

До соответствующего согласования не выполнять общий rebuild ради зелёного отчёта. Геометрические варианты/пересчёт выполняются отдельной будущей задачей с точными входами и независимой проверкой. Здесь нет изменений расчёта/CAD, физических испытаний, инструкции запуска существующей машины, приёмки архитектуры/ТЗ или закрытия G1.
'''
    out['r4_priorities.md']=s
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--render',action='store_true');args=p.parse_args()
    for name,text in documents().items():
        if args.render:(HERE/name).write_text(text)
        elif (HERE/name).read_text()!=text:raise ValueError('document differs from JSON '+name)
    print('Three documentary tables '+('rendered' if args.render else 'match JSON sources/parameter/pose references; no writes'))
