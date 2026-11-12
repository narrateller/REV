"""New report and native before/after projections, no collision inference."""
import html,subprocess,os
from common import *


def figures(data):
    before=NativeWitness(ROOT/'cad/build/frame_mount');after=NativeWitness(OUT)
    specs=[('doser_mount_before_after','Doser / hopper / pocket interfaces',(0,2),(-.05,.2,.85,1.0),['pocket_rear','pocket_front','doser_floor_rear','doser_floor_front','doser_rear','doser_front','hopper_floor_rear','hopper_floor_front','doser_slide']),('doser_service_before_after','Doser extraction / old straight UP remains BLOCKED',(1,2),(-.7,.2,1.35,2.15),['hopper_R','hopper_floor_right','receiving_rim_right','doser_slide','doser_tray_inner','doser_tray_outer']),('powerpack_before_after','Powerpack / end-face motor mounts and tank supports',(0,2),(-3.0,-1.5,-1.45,.0),['hydraulic_tank','pump_motor','motor_mount_rear','motor_mount_front','tank_arm_0','tank_arm_1','tank_mount_0','tank_mount_1'])]
    files=[]
    try:
        for filename,title,axes,limits,names in specs:
            svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000"><rect width="100%" height="100%" fill="#fafaf7"/>',f'<text x="35" y="40" font-size="25" font-family="sans-serif">{html.escape(title)}</text>','<text x="35" y="72" font-size="17" font-family="sans-serif">ASSUMED native profiles / metres / no REV hardware, strength or safety validation</text>']
            for panel,(label,native) in enumerate([('BEFORE / a5d5bad',before),('AFTER / rev8',after)]):
                left=50+panel*790;top=145;width=690;height=600;x0,y0,x1,y1=limits;scale=min(width/(x1-x0),height/(y1-y0));ox=left+(width-(x1-x0)*scale)/2;oy=top+(height-(y1-y0)*scale)/2
                def point(x,y):return ox+(x-x0)*scale,oy+(y1-y)*scale
                def rect(lo,hi,color,dash=False):
                    x,y=point(lo[0],hi[1]);w=(hi[0]-lo[0])*scale;h=(hi[1]-lo[1])*scale;xx,yy=max(x,left),max(y,top);xr,yr=min(x+w,left+width),min(y+h,top+height)
                    if xr>xx and yr>yy:svg.append(f'<rect x="{xx}" y="{yy}" width="{xr-xx}" height="{yr-yy}" fill="{color}" fill-opacity="{0.06 if dash else 0.35}" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="7,5"' if dash else '')+'/>')
                svg += [f'<text x="{left}" y="115" font-size="22" font-family="sans-serif">{label}</text>',f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="white" stroke="#bbb"/>']
                for name in names:
                    obj=native.objects['A'].get(name)
                    if obj is None:continue
                    b=obj.Shape.optimalBoundingBox(False,False);lo=(b.XMin/1000,b.YMin/1000,b.ZMin/1000);hi=(b.XMax/1000,b.YMax/1000,b.ZMax/1000);i,j=axes
                    color='#d88b26' if name=='doser_slide' else '#437ca5' if name in ('pump_motor','hydraulic_tank') else '#688e63' if name.startswith('hopper') else '#b95347'
                    rect((lo[i],lo[j]),(hi[i],hi[j]),color)
                    if name=='doser_slide' and axes==(1,2):
                        lift=float(config(data,'service_lift'));side=float(config(data,'doser_service_y'))
                        rect((lo[i],lo[j]+lift),(hi[i],hi[j]+lift),'#ba3c36',True)
                        if panel:
                            rect((lo[i]+side,lo[j]),(hi[i]+side,hi[j]),'#276bb3',True);rect((lo[i]+side,lo[j]+lift),(hi[i]+side,hi[j]+lift),'#276bb3',True)
                            a=point((lo[i]+hi[i])/2,(lo[j]+hi[j])/2);b=point((lo[i]+hi[i])/2+side,(lo[j]+hi[j])/2);c=point((lo[i]+hi[i])/2+side,(lo[j]+hi[j])/2+lift)
                            svg.append(f'<polyline points="{a[0]},{a[1]} {b[0]},{b[1]} {c[0]},{c[1]}" fill="none" stroke="#276bb3" stroke-width="3" stroke-dasharray="6,5"/>')
                for k,name in enumerate(names):svg.append(f'<text x="{left+(k//6)*345}" y="{780+(k%6)*22}" font-family="monospace" font-size="13">{name}</text>')
            svg += ['<text x="35" y="940" font-size="17" font-family="sans-serif">Projection overlap is not solid penetration. Doser red ghost: blocked old UP; blue: proposed side/UP and reverse.</text>','<text x="35" y="975" font-size="17" font-family="sans-serif">Full interval/native evidence separate. Real actuator, fasteners, tank wall, rigging and safety UNKNOWN; G1 OPEN.</text>','</svg>']
            path=OUT/(filename+'.svg');path.write_text('\n'.join(svg));files.append(path)
    finally:before.close();after.close()
    code='''from PySide2 import QtSvg,QtGui,QtCore
from pathlib import Path
import sys
app=QtGui.QGuiApplication([])
for f in sys.argv[1:]:
 r=QtSvg.QSvgRenderer(f);assert r.isValid()
 i=QtGui.QImage(1600,1000,QtGui.QImage.Format_ARGB32);i.fill(QtCore.Qt.white);p=QtGui.QPainter(i);r.render(p);p.end();assert i.save(str(Path(f).with_suffix('.png')))
'''
    subprocess.run(['/usr/bin/python3','-B','-c',code,*map(str,files)],env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},check=True)


def main():
    data=load(INPUT);assessment=json.loads((OUT/'assessment.json').read_text());evidence=json.loads((OUT/'interval_evidence.json').read_text());before_after=json.loads((OUT/'before_after_native.json').read_text());inv=json.loads((OUT/'inventory/inventory.json').read_text());generation=json.loads((OUT/'generation.json').read_text());joints=json.loads((OUT/'interfaces.json').read_text())
    figures(data)
    old=load(ROOT/'cad/frame_mount/inputs.assumed.json');oldmap={c['id']:c for c in old['components']};changes=[]
    for c in data['components']:
        prior=None if c['id'] not in oldmap else [[str(x) for x in side] for side in bounds(old,oldmap[c['id']])];after=[[str(x) for x in side] for side in bounds(data,c)]
        if prior!=after:changes.append({'id':c['id'],'before_bounds_m':prior,'after_bounds_m':after,'parameter_ID_revisions':{r:data['parameters'][r] for field in ('position','size') for r in c.get(field,[])}})
    save(OUT/'changes.json',changes)
    lines=['# Дозатор и гидростанция A/B — ограниченная исследовательская коррекция','','R4 self-check, новый независимый OUTPUT review NOT_RUN. База a5d5bad6dd8928045512bca16836fd1d2544b7ca, RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430. Все размеры ASSUMED, реальные параметры UNKNOWN, G1 OPEN.','','## Изменения и причины','','Pocket collar поднятия не требует: его верхняя грань опущена до существующей нижней плоскости дозирующего кольца. Стенки дозатора укорочены до нижней плоскости hopper floor, расширены вдоль Y для поддержки извлечённого ползуна. Кольцо нормализовано до точных общих номинальных рёбер. Рабочий doser_slide, его ось и ход не менялись. Изменения до/после и ID@revision — changes.json/change_plan.json.','','Outboard tray и guide разбиты вокруг прежнего вертикального коридора gate_service_cap; непрерывные боковины обходят этот коридор и поддерживают обе секции. Это условные геометрические связи: реальные крепёж, опора длинной консоли, жёсткость/зазоры и привод UNKNOWN. Наличие опорной поверхности не подтверждает её силовую способность.','','Motor поднят над tank, сохраняет ось X/радиус/длину, опирается условными торцевыми гранями на две плиты. Плиты стоят на верхней грани tank. Tank смещён от ограждения, его низ связан через две опорные балки/кронштейна с base_R. Реальная конструкция стенки tank, фланцы, крепёж, масса и несущая способность UNKNOWN.','','## Каждая из 20 прежних пар','','| Вариант | Пара | Native до, мм³ | Native после в том же состоянии, мм³ | Решение |','|---|---|---:|---:|---|']
    for r in before_after:lines.append(f"| {r['variant']} | {' / '.join(r['pair'])} | {r['before']['common_volume_mm3']:.9g} | {r['after']['common_volume_mm3']:.9g} | {r['disposition']} |")
    lines += ['', '**14 статических native проникновений устранены. Шесть проникновений на старом straight-UP сервисе остаются доказанными и BLOCKED.** Они не переименованы в INDETERMINATE и не исключены из матриц. Для дозатора предложена другая исследовательская последовательность на существующей оси Y: retract → lift → lower → return. Старый подъём через неподвижный hopper остаётся обязательным отрицательным контрпримером. Реальный дополнительный ход привода, условия отсоединения и безопасный подъём UNKNOWN, поэтому фактическая реализуемость нового сервиса INDETERMINATE.', '', '## Сервис и регрессия', '', 'Motor извлекается/возвращается отдельно; powerpack поднимается вместе с tank/двумя motor plates; отдельный tank извлекается после подъёма и парковки motor/plates по Y, затем все тела возвращаются. Ни одно тело не удаляется lifecycle-событием. Никакого вывода о безопасном подъёме или реальной расстыковке нет.', '', f"Все пары каждого этапа сохранены: {evidence['all_pair_rows']} строк. Точный affine interval solver проверил {evidence['audited_critical_rows']} критических строк; {evidence['previous_target_rows']} прежних gate/portal target строк без положительного объёма. Все положительные критические строки относятся только к трём прежним doser/hopper парам A/B на явно BLOCKED прямом подъёме. Неизвестные control движения остаются INDETERMINATE.", '', '| Вариант | Сервис | Continuity / return | Конфликтные строки движущихся тел |', '|---|---|---|---:|']
    for s in assessment['scenes']:
        if s['case'].startswith('service_'):lines.append(f"| {s['variant']} | {s['case']} | {s['continuity_status']} / {s['positions_restored']} | {len(s['service_moving_penetrations'])} |")
    lines += ['', f"В новых 8 сервисах нет положительного перекрытия движущихся тел на полном ходе/возврате. Возврат координат сам по себе не исправляет старый blocked UP. Общие виды/STEP/FCStd A/B и три native profile before/after представлены рядом. Проекции разных плоскостей не самостоятельное доказательство коллизии.", '', '## Сопряжения, сырьё и предел', '', f"{len(joints)} условных номинальных интерфейсов: positive-area native face intersection и нулевой solid common; interfaces.json содержит причины. Это не утверждение физической посадки, крепежа или силовой способности. Frozen classifier не получил новых разрешающих исключений; непредписанные касания сохраняют INDETERMINATE в его полном потоке.", '', 'Вход после имеющихся дробления/просева, throat hopper → дозатор → pocket → прежнее окно gate/chamber и выход пресса сохраняются. Целевое номинальное central aperture сохранено; точные legacy дробные границы колец нормализованы и показаны в changes.json. Фактическое общее положительное окно и его точные границы пересчитываются в verifier JSON. Рабочие doser/punch/gate/lock/stop ходы не менялись. Реальные подача/включения/влажность/трение/зависание/герметичность/производительность UNKNOWN; присутствие ползуна в окне и транспорт сырья физически не моделируются.', '', 'Конечный реестр — inventory/inventory.md/json, все non-CLEAR пары с контекстами. Оставшиеся native пары:', '', '| Вариант | Пара | Статус |', '|---|---|---|']
    for r in inv['rows']:
        if r['classification']=='NATIVE_PENETRATION':lines.append(f"| {r['variant']} | {' / '.join(r['pair'])} | BLOCKED legacy UP; реальная альтернативная service feasibility INDETERMINATE |")
    lines += ['', 'Остальные контакты отдельно: условные сопряжения (interfaces.json), conservative envelope intersections и INDETERMINATE — inventory/classes. Нативные положительные объёмы не объявляются допустимыми сопряжениями. Восемь cycle ожиданий проверены прежним strict oracle и verify_cycles; это прежнее ограниченное path-подмножество, не весь пресс.', '', f"Все {generation['frozen_modules']} прежних Python-модуля неизменны. Новые адаптация/оркестрация/проверки cad/feed_power требуют отдельного R5 review. Исторические hardcoded metadata frozen checker не являются provenance новой редакции; актуальны inputs SHA/generation/publication manifest.", '', '**Весь пресс не принят, READY INDETERMINATE.** Реальные размеры/нагрузки/крепления/сырьё/безопасность UNKNOWN, архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 OPEN.', '', '## Воспроизведение', '', '```bash','git lfs pull','/usr/bin/python3 -B cad/feed_power/generate.py','/usr/bin/python3 -B cad/feed_power/verify_output.py','/usr/bin/python3 -B cad/feed_power/verify_output.py','```', '', 'Генерация — явная запись; verifier только читает сохранённый пакет и печатает JSON/exit. Перед повторением сохранить исходный C. Stdout сохранять вне проверяемого каталога. FreeCAD 1.0.0/Part, Python 3.13.5, PIL/reportlab/PySide2.QtSvg.']
    (OUT/'assessment.md').write_text('\n'.join(lines)+'\n');print('Native before/after views and report generated')


if __name__=='__main__':main()
