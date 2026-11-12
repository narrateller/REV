"""New report and native before/after projections, no collision inference."""
import argparse,html,subprocess,os
from common import *
from service_semantics import *


def figures(data,current):
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
                            scene=next(s for s in current if s['variant']=='A' and s['case']=='service_fp_doser_retract_lift')
                            for st in scene['stages']:
                                positions=[box_at(st['state']['doser_slide'],t,st['time']) for t in st['time']]
                                if any(p is None for p in positions):continue
                                ends=[]
                                for low,high in positions:
                                    rect((float(low[1]),float(low[2])),(float(high[1]),float(high[2])),'#276bb3',True)
                                    ends.append(point(float((low[1]+high[1])/2),float((low[2]+high[2])/2)))
                                a,b=ends;svg.append(f'<polyline points="{a[0]},{a[1]} {b[0]},{b[1]}" fill="none" stroke="#276bb3" stroke-width="3" stroke-dasharray="6,5"/>')
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
    parser=argparse.ArgumentParser();parser.add_argument('--report-only',action='store_true');args=parser.parse_args()
    data=load(INPUT);current=read_packed(OUT/'service_scenes.json.gz');evaluator=Evaluator(data,OUT)
    try:semantics=evaluate_services(data,current,evaluator)
    finally:evaluator.close()
    save(OUT/'service_report.json',semantics)
    if not args.report_only:figures(data,current)
    before_after=json.loads((OUT/'before_after_native.json').read_text());interfaces=json.loads((OUT/'interfaces.json').read_text())
    lines=['# Дозатор и гидростанция — фактический сервисный исход','','R4 self-check, независимый RECHECK NOT_RUN. Расчёт выполнен заново из текущих service state/time, всех обязательных пар, состава движения и declared plan. Команда/тестовое ожидание/пригодность пути — разные результаты. Физическая выполнимость всегда INDETERMINATE, G1 OPEN.','',f"Выполнение расчёта: {semantics['calculation_execution']}; совпадение с обязательными ожиданиями: {semantics['test_evaluation']}. Геометрические исходы: {semantics['geometric_path_counts']}; общие сервисные исходы: {semantics['overall_service_counts']}.",'','Подтверждённая коллизия блокирует успех даже вместе с unknown. Неподдержанный/неизвестный обязательный метод, участок, пара или boundary не дают подтверждённого геометрического пути. Ни совпадение отрицательного теста, ни exit 0 не означают физическую пригодность.','', '## Текущие сервисные сцены','', '| Вариант | Сцена | Геометрия | Метод | План | Continuity / return | Общий сервис | Физика | Ожидание теста |','|---|---|---|---|---|---|---|---|---|']
    for r in semantics['service_scenes']:
        lines.append(f"| {r['variant']} | {r['case']} | {r['geometric_path_outcome']} | {r['method_status']} | {r['plan_status']} | {r['continuity_status']} / {r['nominal_return']} | {r['overall_service_outcome']} | {r['physical_feasibility']} | {r['matches_test_expectation']} |")
    lines += ['', 'Все stage/pair digests, ошибки/неизвестности метода/плана/непрерывности/возврата и current collision intervals — service_report.json. Это свежий расчёт, не копия сохранённого assessment.','', '## Доказанные коллизии текущих сервисных путей','', '| Вариант | Сцена | Фаза | Пара | Нормированный интервал положительного перекрытия |','|---|---|---|---|---|']
    for r in semantics['service_scenes']:
        for w in r['proven_collisions']:lines.append(f"| {r['variant']} | {r['case']} | {w['phase']} | {' / '.join(w['pair'])} | {w.get('normalized_boundary_values')} |")
    lines += ['', '## Сохранённая геометрия и before/after исходного CAD','', 'Эта таблица относится к сохранённым native моделям исходной компоновки, а не автоматически к произвольному изменённому сервисному пути. Подменённая траектория оценивается таблицами выше. Actual FCStd/STEP/QueryVolumes и соответствие всех сохранённых доказательств обязан проверить отдельный readonly verifier. Геометрические изображения показывают исходную компоновку и сами не подтверждают текущую траекторию.','', '| Вариант | Пара | Native до, мм³ | Native после, мм³ | Область |','|---|---|---:|---:|---|']
    for r in before_after:lines.append(f"| {r['variant']} | {' / '.join(r['pair'])} | {r['before']['common_volume_mm3']:.9g} | {r['after']['common_volume_mm3']:.9g} | {r['disposition']} |")
    lines += ['', 'В проверенном исходном CAD 14 static проникновений устранены; 6 native legacy-UP пар BLOCKED сохранены. Нельзя объявить эти шесть устранёнными по успешному тестовому ожиданию. Полный геометрический diff/ID@revision: changes.json и cad/feed_power/change_plan.json. Нативные модели A/B, STEP, PNG/SVG/PDF и before/after виды сохранены.','', f"{len(interfaces)} условных nominal interfaces не подтверждают реальные болты/швы/фланцы, радиальную фиксацию, tank wall или несущую способность. Путь сырья/номинальное окно и рабочие ходы сохраняются в исходном CAD; реальные подача/сырьё/физика UNKNOWN.",'', 'Конечный baseline inventory — inventory/inventory.json/md, исходные классы/контексты не удаляются. Достоверность current classifications, interval_rows, assessment и их соответствие текущим сценам проверяются пересчётом, не только внешним manifest hash.','', '**Весь пресс не принят, READY INDETERMINATE.** Архитектура/ТЗ не утверждены, размеры ASSUMED, реальные параметры UNKNOWN, физические испытания NOT_RUN, G1 OPEN.','', '## Команды','', '```bash','/usr/bin/python3 -B cad/feed_power/service_semantics.py','/usr/bin/python3 -B cad/feed_power/generate.py --reanalyze','/usr/bin/python3 -B cad/feed_power/verify_output.py','/usr/bin/python3 -B cad/feed_power/verify_output.py','```','', 'Reanalysis — явная генерация новых derived результатов из сохранённых poses, без изменения CAD. Полный build: generate.py без --reanalyze. Verifier ничего не исправляет/не пишет, только JSON stdout/exit. Перед воспроизведением сохранять исходный C.']
    (OUT/'assessment.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'execution':'COMPLETED','test_evaluation':semantics['test_evaluation'],'service_geometric_outcomes':semantics['geometric_path_counts'],'service_overall_outcomes':semantics['overall_service_counts'],'physical_feasibility':'INDETERMINATE'}));return 0 if semantics['test_evaluation']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
