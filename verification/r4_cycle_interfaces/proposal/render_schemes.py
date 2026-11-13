#!/usr/bin/env python3
"""Explicit documentary export. No CAD, solver, registry update or verifier side effects."""
from pathlib import Path
import argparse, csv, io, json, hashlib
from html import escape as e
HERE=Path(__file__).resolve().parent

def read(n):return json.loads((HERE/n).read_text())

def svg_start(title,subtitle):
 return ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1100" role="img">',f'<title>{e(title)}</title>', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#37536b"/></marker></defs>', '<rect width="1600" height="1100" fill="#f7fafc"/>', '<style>text{font-family:DejaVu Sans,sans-serif;fill:#172f43} .t{font-size:19px} .h{font-size:24px;font-weight:bold} .s{font-size:17px} .line{stroke:#37536b;stroke-width:3;fill:none;marker-end:url(#arrow)} .dash{stroke-dasharray:9 6}</style>',f'<text x="50" y="52" class="h">{e(title)}</text>',f'<text x="50" y="86" class="t">{e(subtitle)}</text>']
def txt(s,x,y,lines,cls='t',step=28):
 for i,line in enumerate(lines):s.append(f'<text x="{x}" y="{y+i*step}" class="{cls}">{e(line)}</text>')
def box(s,x,y,w,h,label,fill='#e5eff7',dash=False):
 s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#37536b" stroke-width="2"'+(' stroke-dasharray="9 6"' if dash else '')+'/>');txt(s,x+12,y+30,label,'s',25)
def line(s,x1,y1,x2,y2,dash=False):s.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="line'+(' dash' if dash else '')+'"/>')
def footer(s):
 txt(s,50,1010,['ASSUMED: символическая топология. UNKNOWN: реальные размеры, силы, свойства, допуски, ресурсы.', 'Пиксели — оформление, не инженерные координаты. Native geometry NOT_RUN; физический READY NO-GO.', 'W02 OPEN / NOT_IMPLEMENTED. Архитектура и ТЗ не утверждены. G1 OPEN. Физические испытания NOT_RUN.'],'s',28)
 return '\n'.join(s+['</svg>'])+'\n'
def interface(v):
 s=svg_start(f'{v} / CYC-02 — интерфейсы подачи, затвора и пуансона','BASE_'+v+' fixed-budget • NTS без масштаба • условия действия в permissions.json, не программа управления')
 # Functional material interfaces
 boxes=[(50,150,245,110,['Существующая линия','Дробление / просев','Включения: на линии']), (340,150,235,110,['Приём → бункер','Транспорт / буфер','UNKNOWN']), (620,150,245,110,['Дозатор D0 ↔ D1','ASSUMED ползун +y','S_D UNKNOWN']), (910,150,225,110,['Стык / затвор','G0 ↔ G1; по y','S_G UNKNOWN']), (1180,150,370,110,['Камера / пуансон +x', 'A: канал + зажим + столб' if v=='A' else 'B: закрытая камера + упор/замок','Выход → приём UNKNOWN'])]
 for x,y,w,h,l in boxes:box(s,x,y,w,h,l,'#fff0da')
 for x1,x2 in [(295,340),(575,620),(865,910),(1135,1180)]:line(s,x1,205,x2,205)
 # Coordinates + sequence lanes
 box(s,50,310,420,260,['Базы и положения','O: задняя плоскость камеры','+x → выход; +y поперёк; +z вверх','D/G: свои базы, offsets UNKNOWN','P0 = x_P0 UNKNOWN','P1 = P0 + S_approach','P2 = P1 + S_work','P3 = P2 + S_eject'],'#e5eff7')
 txt(s,515,340,['Порядок подачи (каждая стрелка — полный путь и guards)'],'h')
 for x,l in [(515,['P0/PF','FEED_CLEAR']), (770,['G0: OPEN','D0 → D1 → D0']), (1025,['Доза учтена','G0 → G1']), (1280,['G1 подтверждён','P: подход/работа'])]:box(s,x,375,235,90,l,'#e2f2ec')
 for a,b in [(750,770),(1005,1025),(1260,1280)]:line(s,a,420,b,420)
 txt(s,515,505,['Закрытие G до завершения переноса дозы не разрешено.', 'Поза D/G/P ≠ доказательство материала, изоляции или READY.'],step=32)
 box(s,50,615,730,300,(['A empty → startup → column → steady','GATHER → partial RETURN → REFILL: тот же столб','PG_A/PF/число наборов UNKNOWN; реакция обязательна','COLUMN_CRITERION отдельно, не счётчик ходов','Steady: COMPACT → SEGMENT → EJECT','Остаток сохранён; зажим/реакция UNKNOWN','CROSS → RECEIVE, только затем допустим REMOVE','Возврат P3 → P0 по source S_return; READY отдельно'] if v=='A' else ['B load → repeated gather или single','GATHER → partial RETURN → REFILL: тот же batch','PG_B/PF/вместимость/удержание UNKNOWN','SELECT → COMPACT → UNLOAD → UNLOCK → OPEN','Открытие B INDETERMINATE, не из конца хода','EJECT → CROSS → RECEIVE → RETURN','STOP-CLOSE → RELOCK → RESET с остатками','B_RESET_CONFIRMED отдельно; P0 ≠ READY']),'#e2f2ec')
 box(s,825,615,725,300,['Условия каждого движения','START родителя + текущие инварианты + свои guards','Свидетельства: subject / operation / epoch / revisions','Изменение материала/позы/ресурса делает guards устаревшими','Доказанный отказ → BLOCKED, даже при другом UNKNOWN','Иначе обязательный UNKNOWN → INDETERMINATE','Recovery: свои guards, новый ID, без общего READY','Нельзя снять чужой fault или забыть rejected ID'],'#fff0da')
 return footer(s)
def force(v,opt,rec):
 s=svg_start(f'{v} / {opt} / CYC-03 — {rec["title"]}', 'ASSUMED вариант без выбора • условный вид сверху, +x вправо / +y вверх • размеры UNKNOWN • не CAD')
 # forbidden envelope and feed extension above
 box(s,940,190,480,340,['Запрещённый штоку объём','КАМЕРА + ПОДАЧА (sweep)','Рабочее сечение сохранено'],'#fde6e5',True)
 box(s,1030,310,230,95,['Материал / камера','Свойства UNKNOWN'],'#d9efeb')
 box(s,1280,310,200,95,(['A реакция:','канал / зажим','столб UNKNOWN'] if v=='A' else ['B реакция:','упор / замок','unload UNKNOWN']),'#fff0da',True)
 # frame bottom load loop and base anchor
 s.append('<path d="M160,520 L160,570 L1460,570 L1460,420" stroke="#677d91" fill="none" stroke-width="13"/>')
 txt(s,400,605,['Силовые связи / опоры рамы → реакционный узел; размеры и прочность UNKNOWN'],'t')
 box(s,95,480,150,58,['Опора цилиндра'],'#c8d6e4')
 if opt=='V1':
  box(s,95,310,235,95,['Цилиндр: source D','Один, крепления','COTS UNKNOWN'],'#cfe1f5');box(s,330,343,210,28,[''], '#edbb7f')
  txt(s,335,300,['Шток: source d'],'s')
  box(s,540,285,65,170,['T'],'#d5e8fb')
  txt(s,485,250,['T: захваченная траверса'],'s')
  box(s,605,345,340,30,[''],'#d5bce5');txt(s,640,325,['Новый носитель'],'s')
  line(s,565,455,565,505,True);txt(s,280,647,['Требование: весь rod + T остаются сзади камеры во всём ходе.'],'t')
 else:
  box(s,95,155,235,95,['Цилиндр: source D','Один, без деления F','COTS UNKNOWN'],'#cfe1f5');box(s,330,188,210,28,[''],'#edbb7f')
  txt(s,350,145,['Шток: source d'],'s')
  box(s,540,155,65,300,['T'],'#d5e8fb');txt(s,635,215,['Портальная траверса T','вне feed sweep','Момент F·e: UNKNOWN'],'t')
  box(s,605,345,340,30,[''],'#d5bce5');txt(s,640,325,['Новый носитель'],'s')
  s.append('<path d="M160,250 L160,480" stroke="#677d91" stroke-width="13"/>')
  line(s,480,210,480,350,True);txt(s,400,280,['e ?'],'t')
  txt(s,280,647,['Требование: весь rod вынесен по y; вся T остаётся сзади feed/chamber.'],'t')
 # central guides/punch and displacement arrows
 box(s,720,380,185,42,['Направляющие'],'#c8d6e4');s.append('<path d="M810,422 L810,570" stroke="#677d91" stroke-width="7" stroke-dasharray="6 5"/>');box(s,955,325,45,75,['P'],'#f4b772')
 line(s,690,455,945,455);txt(s,695,485,['+x: те же S_approach/work/eject'],'s')
 line(s,945,535,690,535);txt(s,695,525,['Возврат: тот же S_return'],'s')
 # interface break marks don't claim physical contact proof
 txt(s,50,700,['Контур: основание цилиндра → рама → реакция → материал → P → носитель → T → шток → цилиндр.'],'t')
 box(s,50,735,730,205,['До: прямой source шток входил в камеру/подачу.','После: изменена только предлагаемая топология, не BRep.','D/d/F/камера/ходы не уменьшены; все 44 source binding.','Носитель — новая силовая деталь, не переименованный шток.','Двусторонние joints, устойчивость и потери → R3.','Нативные пары/прочность: NOT_RUN / INDETERMINATE.'],'#e5eff7')
 box(s,825,735,725,205,['Доступы и последующая проверка','Извлечение цилиндра/штока/носителя и снятие T с опорой.','CylinderRemoval / DoserRemoval / новые QueryVolumes.','Направляющие, крепления, порты, ограждения, сервис по L.','Старые BLOCKED/SHORT_STROKE/unknown не закрыты.','B opening и физическая выполнимость L INDETERMINATE.'],'#fff0da')
 return footer(s)
def generate(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 result={}
 for v in ['A','B']:result[f'interface_{v}.svg']=interface(v)
 for rec in read('force_variants.json')['variants']:result[f'force_{rec["id"]}.svg']=force(rec['variant'],rec['option'],rec)
 acts=read('permissions.json')['actions']
 columns=['id','variant','mode','material_from','material_to','poses','predecessors','entry_guards','completion_guards','extra_entry_guards','extra_completion_guards','contract_ref','source_rows','evidence_scope','resources','continuity','mandatory_checks','exit_receipt','recovery','check_ids','source_bindings','permission_actual','physical_permission']
 buf=io.StringIO(newline='');w=csv.writer(buf,lineterminator='\n');w.writerow(columns)
 for a in acts:w.writerow([json.dumps(a[k],ensure_ascii=False,sort_keys=True) if isinstance(a[k],(list,dict)) else a[k] for k in columns])
 result['positions_permissions.csv']=buf.getvalue()
 md=['# Положения и разрешения — документальная таблица','', 'Полные entry/completion, источники, scope/epoch/evidence, ресурсы и пары — permissions.json и positions_permissions.csv. Все actual INDETERMINATE, physical permission NO_GO. Guard-перечни исходных действий перенесены полностью из проверенного C; подстадии связывают START родителя, текущие инварианты и свои guards; предварительные движения имеют собственные условия. UNKNOWN не ноль.','', '| Действие / mode | Материал до → после | D / G / P | Предшественники | Дополнительные entry / completion |','|---|---|---|---|---|']
 for a in acts:
  ps=a['poses'];md.append('| '+a['id']+' / '+', '.join(a['mode'])+' | '+', '.join(a['material_from'])+' → '+a['material_to']+' | '+ps['doser']+' / '+ps['gate']+' / '+ps['punch']+' | '+a['predecessors']+' | '+', '.join(a['extra_entry_guards'])+' / '+', '.join(a['extra_completion_guards'])+' |')
 result['positions_permissions.md']='\n'.join(md)+'\n'
 for n,t in result.items():(out/n).write_text(t)
 manifest={'scope':'Document exports only, no CAD evidence','sources_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['render_schemes.py','force_variants.json','permissions.json','poses.json','mechanical_guards.json','baseline_bindings.json','verification_plan.json','unknown_inputs.json']},'exports_sha256':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in sorted(result)}}
 (out/'exports_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 return sorted(result)+['exports_manifest.json']
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output-dir',required=True,help='Explicit generation target, no CAD rebuild');a=ap.parse_args()
 print(json.dumps({'execution_status':'COMPLETED','generated':generate(a.output_dir),'geometry_outcome':'NOT_RUN','physical_READY':'NO_GO'},ensure_ascii=False))
