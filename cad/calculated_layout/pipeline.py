"""Generation and read-only evidence verification are separate explicit commands."""
import argparse,collections,gc,gzip,subprocess,tempfile,itertools
from bridge import *
from scenes import make_scenes,assess_scenes

def fingerprint(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def source_check():
    m=json.loads((AUDIT/'input_manifest.json').read_text())
    for p,r in m['sources'].items():
        if p!='ISSUES_AND_TASKS.md':assert digest(ROOT/p)==r['sha256'],'accepted source changed '+p
    for p,h in m['prior_publication_manifest_80_files'].items():assert digest(ROOT/p)==h,'prior publication changed '+p
    for v in VARS:assert load(input_path(v))==make_input(v),'registered bridge input stale '+v
    return {'accepted_input_files':len(m['sources'])-1,'old_publication_files':len(m['prior_publication_manifest_80_files']),'44_bindings':'UNCHANGED','old_tool_and_geometry':'UNCHANGED'}

def native_command(v,out,build=False):
    cmd=['/usr/bin/python3','-B',str(SOURCE/'native.py'),'--variant',v,'--out',str(out)]+(['--build'] if build else [])
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    payload=next((json.loads(x[len('RESULT_JSON:'):]) for x in p.stdout.splitlines() if x.startswith('RESULT_JSON:')),None)
    if p.returncode:raise RuntimeError(json.dumps({'argv':cmd,'exit_code':p.returncode,'result':payload,'stderr':p.stderr[-4000:]}))
    return {'argv':cmd,'exit_code':p.returncode,'result':payload}

def catalog(out):
    paths=[p for folder in (SOURCE,Path(out)) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='publication_manifest.json']
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):p for p in paths}

def seal(out):save(Path(out)/'publication_manifest.json',{'schema':1,'scope':'calculation-linked research source/native CAD/all scene evidence; no physical acceptance','sha256':{n:digest(p) for n,p in sorted(catalog(out).items())}})

def check_manifest(out):
    m=json.loads((Path(out)/'publication_manifest.json').read_text());paths=catalog(out)
    assert m['schema']==1 and set(m['sha256'])==set(paths),'publication file set differs'
    for n,p in paths.items():assert digest(p)==m['sha256'][n],'publication file changed '+n
    return len(paths)

def compute(v,out,write=False):
    data=load(input_path(v));evaluator=Evaluator(data,out)
    try:
        if not write:
            class PlanOnly:plan_only=True
            expected=make_scenes(data,v,PlanOnly());saved=read_packed(Path(out)/v/'scenes.json.gz')
            projection=lambda ss:[{'variant':s['variant'],'case':s['case'],'stages':[{k:st[k] for k in ('phase','state','time')} for st in s['stages']]} for s in ss]
            assert projection(expected)==projection(saved),'saved mandatory path/registry/time/method differs from source plan '+v
        scenes=make_scenes(data,v,evaluator)
        if write:packed(Path(out)/v/'scenes.json.gz',scenes)
        else:assert scenes==read_packed(Path(out)/v/'scenes.json.gz'),'saved phases/poses/time/matrices differ from current sources '+v
        with tempfile.TemporaryDirectory(prefix='rev-cl-pairs-') as temp:
            rows=Path(out)/v/'pair_checks.jsonl.gz' if write else Path(temp)/'pairs.gz'
            report=assess_scenes(data,v,scenes,evaluator,rows)
            if not write:
                with gzip.open(rows,'rb') as a,gzip.open(Path(out)/v/'pair_checks.jsonl.gz','rb') as b:
                    for x,y in itertools.zip_longest(a,b):assert x==y,'saved pair classification/proof differs '+v
        report['scene_state_evidence_sha256']=fingerprint(scenes)
        if write:save(Path(out)/v/'results.json',report)
        else:assert report==json.loads((Path(out)/v/'results.json').read_text()),'saved report differs from fresh whole interval calculation '+v
        return report
    finally:evaluator.close()

def summarize(reports):
    return {'artifact_execution':'COMPLETED','mode':'fixed-budget','variants':{v:{'all_pair_rows':r['all_pair_rows'],'scene_geometric_counts':dict(collections.Counter(s['geometric_scene_outcome'] for s in r['scene_results'])),'actual_output_cases':[{k:s.get(k) for k in ('case','nominal_axial_geometry','actual_output_geometry','required_link','continuity_status','nominal_return','READY','overall_cycle_outcome','limited_cycle_success','test_expectation_match')} for s in r['scene_results'] if not s['case'].startswith('service_')],'remaining_issue_pairs':len(r['issues'])} for v,r in reports.items()},'physical_feasibility':'INDETERMINATE','B_open_permission':'INDETERMINATE','L_path_physical_feasibility':'INDETERMINATE','whole_press_READY':'INDETERMINATE','architecture_approved':False,'specification_approved':False,'physical_tests':'NOT_RUN','G1':'OPEN'}

def mapping(out):
    lines=['# Фактическая связь CAD с R3 — BASE_A/BASE_B fixed-budget','','CALCULATED наследует ASSUMED. Нативный Sources содержит полный точный JSON, числовые ячейки FreeCAD нормализованы к 15 значащим цифрам; отдельные вычисления Fraction не являются физическим допуском. Все 44 принятых строки применены в указанной роли, не все являются размерами.','','| Параметр CAD / роль | Сценарий и точный источник | Значение SI / статус | Прежнее значение / различие | Затронутые узлы |','|---|---|---|---|---|'];rows=[]
    old=load(BASELINE)
    for v in VARS:
        d=load(input_path(v));g=d['exact_geometry']
        oldvals={'chamber.width':'0.4 m','chamber.height':'0.4 m','chamber.length':'1.1 m','product.length':'0.5 m','cylinder.bore_min':'UNKNOWN; old outer barrel diameter 0.44 m is not bore','cylinder.rod_diameter':'0.14 m','stroke.return':str(config(old,'travel_'+v))+' m','material.occupied_length':'UNKNOWN / not modelled'}
        for r in d['source_bindings']:
            field=r['proposed_cad_field'];role='geometry/trajectory' if field.startswith(('chamber.','product.','material.','stroke.','cylinder.')) else 'load interface only, no mount design' if field.startswith('load.') else 'fixed-budget trajectory timing, not real speed approval'
            native='Sources.src_'+r['parameter_id'];before=oldvals.get(field,'not separately represented; old synthetic phase duration 1 s and combined press/output stroke')
            row={**r,'cad_application':'APPLIED_RESEARCH_ONLY','native_source_target':native,'role':role,'previous':before,'physical_truth':'UNKNOWN'};rows.append(row)
            lines.append(f"| {field} / {native} / {role} | {r['scenario']} / {r['source']} / {r['parameter_id']}@{r['revision']} | {r['value']} {r['unit']} / {r['lifecycle']} from ASSUMED | {before} | {r['affected_nodes']} |")
        save(Path(out)/v/'parameter_changes.json',{'scenario':'BASE_'+v,'changes':d['parameter_changes'],'rounding_audit':d['source_rounding_audit'],'recipe':d['bridge_recipe'],'real_REV':d['real_REV']})
    save(Path(out)/'source_application.json',{'accepted_rows':44,'applied_rows':len(rows),'rows':rows});(Path(out)/'parameter_mapping.md').write_text('\n'.join(lines)+'\n')
    changes=['# Все изменённые локальные CAD параметры','','Новые постоянные ID зарегистрированы до CAD. Неизменённые параметры сохраняют прежний ASSUMED источник; список всех значений находится в inputs.BASE_A/B.json. Полный JSON parameter_changes.json включает зависимости и выражения.','','| Вариант / CAD ID | Было SI | Стало SI | Статус / причина | Узлы |','|---|---|---|---|---|']
    for v in VARS:
        d=load(input_path(v))
        for r in d['parameter_changes']:changes.append(f"| {v} / {r['cad_parameter_id']} | {r['old_value']} {r['unit']} | {r['new_value']} {r['unit']} | {r['status']} / {r['reason']} | {', '.join(r['affected_nodes']) or 'trajectory/configuration'} |")
    (Path(out)/'all_parameter_changes.md').write_text('\n'.join(changes)+'\n')

def report_text(out,reports,summary):
    lines=['# Расчётно связанная исследовательская компоновка REV A/B','','**Не утверждённая конструкция. G1 OPEN.** BASE_A/BASE_B fixed-budget из PR #39. Command execution / artifact consistency / test expectation / scene geometry / physical feasibility разделены. Фактические сцены не становятся пригодными при зелёном CLI или совпадении отрицательного теста.','','## Выдача и возврат','','| Вариант / случай | Граница R3 | Фактический выход CAD | Link WORK/EJECT | Непрерывность | Возврат инструментов | READY | Геометрия всей сцены |','|---|---|---|---|---|---|---|---|']
    for v,r in reports.items():
        for s in r['scene_results']:
            if s['case'].startswith('service_'):continue
            lines.append(f"| {v}/{s['case']} | {s['nominal_axial_geometry']} | {s['actual_output_geometry']} | {s['required_links']} | {s['continuity_status']} | {s['nominal_return']} | {s['READY']} | {s['geometric_scene_outcome']} |")
    lines+=['','Расчёт R3 проверяет выдачу за chamber_end + clearance. Прежние выходные плоскости CAD перенесены вместе с камерой: канал A сохраняет длину, B сохраняет выходной отступ. При заданном ходе оболочка не проходит фактический выход. Поэтому REMOVE отсутствует, изделие остаётся в сцене, восстановление рабочего READY не подтверждено. Движения возврата/закрытия — диагностические пробы, не разрешение выполнять их на прессе. Возврат инструмента не является полным циклом.','', 'Жёсткий product с самого начала является surrogate готового брикета. Отдельный DoseEnvelope показывает занимаемый дозой объём; уплотнение/деформация/переход сырьё→продукт не реализованы и остаются INDETERMINATE. Нулевые проектные зазоры на нагруженной грани — гипотеза R3, не допуск/подтверждённое сопряжение.','', '## Сервисы — весь заявленный путь и все пары','','| Вариант / путь | Геометрия всей сцены | Service path | Непрерывность | Возврат | Ограниченный успех | Физика |','|---|---|---|---|---|---|---|']
    for v,r in reports.items():
        for s in r['scene_results']:
            if not s['case'].startswith('service_'):continue
            q=s['fresh_service_semantics'];lines.append(f"| {v}/{s['case']} | {s['geometric_scene_outcome']} | {s['overall_service_outcome']} | {q['continuity_status']} | {q['nominal_return']} | {s['limited_geometry_success']} | INDETERMINATE |")
    lines+=['','Прежние шесть native BLOCKED прямого UP и ограниченный L-путь сохранены в старом пакете без изменения. Новые статусы выше рассчитаны заново, не наследуются из акта прежней геометрии. Физическая выполнимость L-пути INDETERMINATE в обоих пакетах. Полные прежние и новые проблемы перечислены в remaining_issues.json/md и native_interfaces.json.','', '## Предел готовности','','Камера/продукт/осевые ходы/минимальный bore/шток и новая циклограмма связаны с точными расчётными источниками. Рама, опоры, внешний корпус цилиндра, габариты станции и крепления сохраняют исследовательские предположения; преобразованные стыки требуют проверки/данных. Потерянное сопряжение или пересечение остаются видимыми, не выдаются за силовой путь. Истинные COTS/фланцы/порты/массы/риггинг/нагрузки/прочность/безопасность UNKNOWN. Открытие B INDETERMINATE независимо от результатов условного перемещения.','', 'Нет утверждения архитектуры/ТЗ/оборудования или приёмки пресса. Физические испытания NOT_RUN. Whole press READY INDETERMINATE; независимый OUTPUT review NOT_RUN. Все размеры ASSUMED либо CALCULATED из ASSUMED, без новых VERIFIED/LOCKED.','', '## Файлы и метод','','Сохранены все неупорядоченные пары на каждом участке и замкнутый интервал движения: A/scenes.json.gz, B/scenes.json.gz, pair_checks.jsonl.gz и results.json. Exact boxes/linear translations — прежний frozen engine/strict affine inequalities. Для криволинейной формы отсутствие positive-volume на bounds доказывает разделение; перекрытие оболочек остаётся INDETERMINATE, positive native samples лишь свидетельствуют отдельное проникновение. Вращение/гибкие связи/неописанное условие не дают CLEAR. Все QueryVolumes проверяются в сохранённом native CAD до/после recompute.','', 'Таблицы parameter_mapping.md / source_application.json — все 44 привязки; all_parameter_changes.md и */parameter_changes.json — все изменения, formulas/provenance и округление. Генерация отдельно от readonly verifier, команды в cad/calculated_layout/README.md.']
    (Path(out)/'report.md').write_text('\n'.join(lines)+'\n')

def remaining(out,reports):
    legacy=json.loads((ROOT/'cad/build/feed_power/inventory/inventory.json').read_text())
    result={'historical_previous_remaining':legacy,'new':{v:r['issues'] for v,r in reports.items()},'physical_and_interfaces':'INDETERMINATE; see native_interfaces.json; old issues never silently closed','G1':'OPEN'}
    save(Path(out)/'remaining_issues.json',result)
    lines=['# Конечный перечень геометрических проблем новой итерации','','Исторический список сохранён в remaining_issues.json, не переписан новым расчётом. Допустимые условные сопряжения отдельно в native_interfaces.json; они не подтверждают крепления.','','| Вариант | Пара | Классификация | Наблюдаемые классы | Случаи |','|---|---|---|---|---|']
    for v,r in reports.items():
        for x in r['issues']:lines.append(f"| {v} | {' / '.join(x['pair'])} | {x['classification']} | {', '.join(x['classes'])} | {', '.join(x['cases'])} |")
    lines+=['','Показаны все non-CLEAR/non-allowed-touch пары полного набора. Положительная коллизия блокирует успех; UNKNOWN не закрывается отсутствием sampled native collision. Потерянные стыки/выход/реальная физика перечислены дополнительно в report.md/native_interfaces.json.'];(Path(out)/'remaining_issues.md').write_text('\n'.join(lines)+'\n')

def generate(out,reuse_native=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);sources=source_check();commands=[]
    for v in VARS:
        if not reuse_native:commands.append(native_command(v,out,True))
        commands.append(native_command(v,out))
    reports={}
    for v in VARS:
        reports[v]=compute(v,out,True);gc.collect()
    summary=summarize(reports);save(out/'results.json',summary);mapping(out);remaining(out,reports);report_text(out,reports,summary)
    from views import present,interfaces
    present(out,reports);interfaces(out)
    save(out/'generation.json',{'execution':{'status':'COMPLETED','exit_code':0},'native_commands':commands,'source_check':sources,'sources_sha256':{str(p.relative_to(ROOT)):digest(p) for p in SOURCE.glob('*.py')},'source_snapshots':{v:{'input_sha256':digest(input_path(v)),'registry_snapshot_references':list({json.loads((ROOT/f'verification/{scope}/results/BASE_{v}.json').read_text())['registry_snapshot'] for scope in ('r3_parametric_sizing','r3_power_reconcile')})} for v in VARS},'scene_and_physical_results':summary})
    seal(out);return {'artifact_generation':'COMPLETED','scene_and_physical_results':summary}

def verify(out,require_clear=False):
    sources=source_check();n=check_manifest(out);native=[native_command(v,out) for v in VARS];reports={}
    for v in VARS:reports[v]=compute(v,out);gc.collect()
    summary=summarize(reports);assert summary==json.loads((Path(out)/'results.json').read_text()),'aggregate report stale'
    with tempfile.TemporaryDirectory(prefix='rev-cl-display-') as tmp:
        temp=Path(tmp);mapping(temp);remaining(temp,reports);report_text(temp,reports,summary)
        for p in temp.rglob('*'):
            if p.is_file():assert p.read_bytes()==(Path(out)/p.relative_to(temp)).read_bytes(),'saved table/report stale '+str(p.relative_to(temp))
    from views import interfaces
    assert interfaces(out,False)==json.loads((Path(out)/'native_interfaces.json').read_text()),'saved interface evidence stale'
    okay=not require_clear # whole-machine/physical assumptions are unresolved
    return {'artifact_verification':'CONSISTENT','checked_files':n,'source_check':sources,'native':native,'command_execution':'COMPLETED','requires_clear':require_clear,'require_clear_satisfied':okay,'scene_and_physical_results':summary},0 if okay else 2

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['generate','verify']);parser.add_argument('--reuse-native',action='store_true');parser.add_argument('--out',type=Path,default=OUT);parser.add_argument('--require-clear',action='store_true');args=parser.parse_args()
    try:
        if args.action=='generate':result=generate(args.out,args.reuse_native);code=0
        else:result,code=verify(args.out,args.require_clear)
        print(json.dumps(result,ensure_ascii=False));return code
    except Exception as exc:print(json.dumps({'command_execution':'FAILED','artifact_verification':'FAILED','scene_outcome':'NOT_CONFIRMED','reason':str(exc),'physical_feasibility':'INDETERMINATE','G1':'OPEN'},ensure_ascii=False));return 1
if __name__=='__main__':sys.exit(main())
