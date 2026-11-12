#!/usr/bin/env python3
"""New bounded orchestration. All previously reviewed modules remain frozen.

Does not use the old baseline-preservation harness to validate changed CAD.
"""
import argparse, copy, gzip, hashlib, io, json, os, subprocess, sys, tempfile
from fractions import Fraction as F
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'cad/layout_correction'))
from assess import analyze, checked, NativeWitness, box_at, overlap
from outcomes import evaluate_suite
from verify_cycles import verify_cycles
from layout_common import load, digest, selected, bounds, config
from cad_validation import check_cad_adapter
from inventory import inventory

OUT = ROOT/'cad/build/frame_mount'
INPUT = ROOT/'cad/frame_mount/inputs.assumed.json'
FROZEN = ROOT/'verification/r4_frame_mount/frozen_tool.json'


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2)+'\n')


def packed(path, data):
    with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as f:
        with io.TextIOWrapper(f, encoding='utf-8') as s:
            json.dump(data, s, sort_keys=True, separators=(',', ':'))


def module_service(data, variant):
    initial = checked.bodies(data, variant); current = copy.deepcopy(initial); stages = []; t = F(0)
    for i, sign in enumerate((0, 1, -1, 0)):
        state = copy.deepcopy(current)
        for name in ('cylinder_barrel', 'rod'):
            state[name]['delta'] = ['0', '0', str(sign*config(data, 'service_lift'))]
        interval = [str(t), str(t+config(data, 'phase_duration'))]
        pairs = checked.matrix(state, interval, variant)
        stages.append({'phase': variant+'-SERVICE-cylinder_module-'+str(i), 'state': state, 'time': interval, 'pairs': pairs, 'counts': checked.summarize(pairs)})
        current = checked.advance(state); t += config(data, 'phase_duration')
    continuity = checked.assess_continuity(stages, [])
    restored = all(current[n]['lo'] == initial[n]['lo'] and current[n]['hi'] == initial[n]['hi'] for n in initial)
    return {'variant': variant, 'case': 'service_cylinder_module', 'stages': stages, 'continuity': continuity, 'continuity_status': checked.continuity_status(continuity), 'positions_restored': restored, 'physical_isolation_and_lifting': 'UNKNOWN'}


def joint_pairs():
    rows = []
    def add(a, b, reason): rows.append({'pair': sorted((a, b)), 'reason': reason})
    for rail in ('side_rail_L', 'side_rail_R'):
        for i in range(3): add('crossbar'+str(i), rail, 'transverse member butt to inner rail face; joint shear/moment capacity UNKNOWN')
        add('cylinder_seat_bridge', rail, 'front seat bridge butt into rail; fixed connection hardware UNKNOWN')
    add('crossbar0', 'cylinder_mount_rear', 'rear seat lower face rests on transverse member; fixed joint capacity UNKNOWN')
    add('crossbar2', 'output_support', 'output support rests under transverse member; interface fixing UNKNOWN')
    add('cylinder_seat_bridge', 'cylinder_mount_front', 'front U bottom to bridge upper face')
    for side in 'LR':
        add('cylinder_mount_front', 'cylinder_seat_'+side, 'U bottom/cheek fixed butt; attachment UNKNOWN')
        for i in range(3):
            add('upper_post_'+side+str(i), 'base_'+side, 'upright lower butt to existing base')
            add('upper_post_'+side+str(i), 'side_rail_'+side, 'upright upper butt to existing upper rail')
    for mount in ('cylinder_mount_rear', 'cylinder_mount_front', 'cylinder_seat_L', 'cylinder_seat_R'):
        add('cylinder_barrel', mount, 'conditional axial end-face restraint; paired rear/front planes; radial location, removable fasteners and cylinder interface UNKNOWN')
    return rows


def planar_contact_area(first, second):
    """Native face booleans; solid.common alone does not expose butt faces.

    1e-9 mm is the unchanged native adapter serialization comparison bound,
    not a manufacturing tolerance. Only parallel axis-aligned planar faces.
    """
    area = 0.0
    for a in first.Faces:
        ab = a.optimalBoundingBox(False, False)
        alo, ahi = (ab.XMin, ab.YMin, ab.ZMin), (ab.XMax, ab.YMax, ab.ZMax)
        axes = [i for i in range(3) if abs(ahi[i]-alo[i]) <= 1e-9]
        if len(axes) != 1: continue
        axis = axes[0]
        for b in second.Faces:
            bb = b.optimalBoundingBox(False, False)
            blo, bhi = (bb.XMin, bb.YMin, bb.ZMin), (bb.XMax, bb.YMax, bb.ZMax)
            if abs(bhi[axis]-blo[axis]) <= 1e-9 and abs(blo[axis]-alo[axis]) <= 1e-9:
                area += a.common(b).Area
    return area


def interfaces(data, models):
    native = NativeWitness(models); rows = []
    try:
        for v in 'AB':
            state = checked.bodies(data, v)
            for joint in joint_pairs():
                a, b = joint['pair']; kind, measure, axes = overlap(box_at(state[a], '0', ['0','1']), box_at(state[b], '0', ['0','1']))
                w = native.at(v, [a,b], state, '0', ['0','1'])
                area = planar_contact_area(native.objects[v][a].Shape, native.objects[v][b].Shape)
                okay = kind == 'TOUCH' and measure > 0 and w['common_volume_mm3'] <= 1e-5 and area > 0
                rows.append({'variant': v, **joint, 'nominal_kind': kind, 'nominal_face_area_m2': str(measure), 'native_contact_face_area_mm2': area, 'native': w, 'classification': 'CONDITIONAL_MATING' if okay else 'INDETERMINATE', 'hardware_strength_radial_restraint': 'UNKNOWN'})
                if not okay: raise RuntimeError('interface not established '+str(rows[-1]))
        return rows
    finally: native.close()


def full_interval_evidence(data, before, models, scenes, output):
    """Reuses the reviewed event partition and classifier, never sampling CLEAR.

    Every pair touching a changed/added body is retained, including unknown
    negative controls. Previous targets and entire moving cylinder service
    pairs are explicit subsets. Native witnesses are supplementary only.
    """
    from assess import classify, TARGETS
    changed = set()
    old = {c['id']: c for c in before['components']}
    for c in data['components']:
        if c['id'] not in old or bounds(data,c) != bounds(before,old[c['id']]): changed.add(c['id'])
    target_pairs = {tuple(sorted(p)) for p in TARGETS}
    counts = collections.Counter(); bad = []; old_bad = []; service_bad = []; samples = []; total = 0; targets = 0; selected_count = 0
    native = NativeWitness(models)
    try:
        for scene in scenes:
            for st in scene['stages']:
                for row in st['pairs']:
                    total += 1; pair = row['pair']; is_changed = bool(changed.intersection(pair)); is_target = tuple(sorted(pair)) in target_pairs
                    is_service = scene['case'] in ('service_cylinder_barrel', 'service_rod', 'service_cylinder_module') and bool({'rod','cylinder_barrel'}.intersection(pair))
                    if not (is_changed or is_target or is_service): continue
                    result = classify(row, st['state'], st['time'], scene['variant']); cls = result['class']
                    record = {'variant': scene['variant'], 'case': scene['case'], 'phase': st['phase'], **result}
                    if is_changed: selected_count += 1; counts[cls] += 1
                    if is_target: targets += 1
                    positive = cls in ('PENETRATION','ENVELOPE_INTERSECTION','NATIVE_PENETRATION_WITNESS')
                    # Unsupported product motion is retained as INDETERMINATE;
                    # it is never reclassified to CLEAR or a whole-scene PASS.
                    if positive:
                        if is_changed: bad.append(record)
                        if is_target: old_bad.append(record)
                        if is_service: service_bad.append(record)
                    if (is_changed or is_service) and any(not st['state'][n]['exact_box'] for n in pair) and row['status'] != 'CLEAR':
                        for t in (F(st['time'][0]), sum(map(F,st['time']))/2, F(st['time'][1])):
                            w = native.at(scene['variant'], pair, st['state'], str(t), st['time'])
                            samples.append({'variant': scene['variant'], 'case': scene['case'], 'phase': st['phase'], 'pair': pair, **w})
                            if w.get('common_volume_mm3',0) > 1e-5: bad.append({'native_positive':samples[-1]})
        result = {'method':'reviewed complete rational linear event partition; positive native samples supplemental, not full BRep proof', 'total_all_pair_rows': total, 'changed_body_IDs': sorted(changed), 'changed_body_rows': selected_count, 'changed_body_classes': dict(counts), 'changed_body_positive_overlap_rows': bad, 'previous_target_rows': targets, 'previous_target_positive_overlap_rows': old_bad, 'cylinder_service_positive_overlap_rows': service_bad, 'native_samples': samples, 'whole_press_READY': 'INDETERMINATE'}
        save(output, result)
        if bad or old_bad or service_bad: raise RuntimeError('positive overlap in new group/previous target/cylinder service; see interval_evidence.json')
        return result
    finally: native.close()


import collections


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT); args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    commands = []; suite = None
    def run(command):
        p = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        commands.append({'command':command, 'exit_code':p.returncode, 'stdout':p.stdout, 'stderr':p.stderr})
        if p.returncode: raise RuntimeError('command failed: '+str(command)+'\n'+p.stderr)
    def freeze():
        for path, sha in json.loads(FROZEN.read_text())['sha256'].items():
            if digest(ROOT/path) != sha: raise RuntimeError('reviewed tool changed '+path)
    try:
        freeze(); data = load(INPUT); baseline = load(ROOT/'cad/layout_correction/inputs.assumed.json')
        for v in 'AB':
            assert {c['id'] for c in selected(baseline,v)} <= {c['id'] for c in selected(data,v)}, 'removed body'
            run(['/usr/bin/python3','cad/layout/build_model.py','--inputs',str(INPUT),'--variant',v,'--out',str(out/v)])
        actual_cad = check_cad_adapter(data,out,INPUT); save(out/'native_cad_validation.json',actual_cad)
        run(['/usr/bin/python3','cad/layout/check_layout.py','--inputs',str(INPUT),'--models',str(out),'--out',str(out/'raw_checked_tool')])
        scenes = json.loads(gzip.decompress((out/'raw_checked_tool/all_pairs.json.gz').read_bytes()))
        suite = evaluate_suite(scenes,data); save(out/'strict_cycles.json',suite)
        if suite['status'] != 'PASS': raise RuntimeError('strict eight-case oracle failed')
        save(out/'cycle_assertions.json',verify_cycles(scenes,data))
        extra = [module_service(data,v) for v in 'AB']; packed(out/'work_and_module_service.json.gz',scenes+extra)
        assessment = analyze(data,out,out/'work_and_module_service.json.gz',out,suite)
        services = json.loads(gzip.decompress((out/'service_scenes.json.gz').read_bytes()))
        for s in services:
            assert s['continuity_status']=='CONTINUOUS' and s['positions_restored'], ('service not continuous/restored',s['case'])
        joints = interfaces(data,out); save(out/'interfaces.json',joints)
        interval = full_interval_evidence(data,baseline,out,scenes+services,out/'interval_evidence.json')
        after = inventory(out,out/'inventory')
        # A justified new face contact supplements the frozen raw classifier;
        # original INDETERMINATE/COLLISION evidence is not removed or rewritten.
        by_joint={(r['variant'],tuple(r['pair'])):r for r in joints}
        for row in after['rows']:
            joint=by_joint.get((row['variant'],tuple(row['pair'])))
            if joint and row['classification']!='NATIVE_PENETRATION' and not any(k in row['classes'] for k in ('PENETRATION','ENVELOPE_INTERSECTION','NATIVE_PENETRATION_WITNESS')):
                row['supplemental_interface'] = joint
                row['classification'] = 'CONDITIONAL_MATING'; row['status']='ASSUMED_INTERFACE_ONLY'; row['basis']='explicit interface reason plus native positive face area; frozen raw classes retained, hardware/strength UNKNOWN'
        after['summary']=dict(collections.Counter(r['classification'] for r in after['rows'])); save(out/'inventory/inventory.json',after)
        # Re-render table after supplementary native interface justification.
        table=['# Конечный реестр после изменения','','Все не-CLEAR пары сохранены, в JSON — исходные классы, контексты и нативные свидетельства. Условное сопряжение не подтверждает крепёж и прочность.','','| ID | Вариант | Пара | Класс | Статус |','|---|---|---|---|---|']
        table += [f"| {r['id']} | {r['variant']} | {' / '.join(r['pair'])} | {r['classification']} | {r['status']} |" for r in after['rows']]
        (out/'inventory/inventory.md').write_text('\n'.join(table)+'\n')
        repeat={}
        with tempfile.TemporaryDirectory(prefix='rev-frame-repeat-') as tmp:
            for v in 'AB':
                run(['/usr/bin/python3','cad/layout/build_model.py','--inputs',str(INPUT),'--variant',v,'--out',tmp+'/'+v])
                a=json.loads((out/v/'manifest.json').read_text()); b=json.loads((Path(tmp)/v/'manifest.json').read_text())
                fields=('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes')
                assert all(a[k]==b[k] for k in fields), 'semantic repeat mismatch'
                pngs={p.name:digest(p)==digest(Path(tmp)/v/p.name) for p in (out/v).glob('*.png')}; assert all(pngs.values()),'image repeat mismatch'
                repeat[v]={'semantic':'PASS','images':pngs}
            check_cad_adapter(data,Path(tmp),INPUT)
        freeze()
        report={'execution':{'status':'COMPLETED','exit_code':0},'test_evaluation':{'status':suite['status'],'scope':'eight limited cycle expectations, not whole assembly'},'geometry':{'changed_group_positive_overlap_rows':len(interval['changed_body_positive_overlap_rows']),'previous_target_positive_overlap_rows':len(interval['previous_target_positive_overlap_rows']),'whole_press_READY':'INDETERMINATE'},'review_status':'REQUIRES_INDEPENDENT_R5','input_commit':'17501de','input_sha256':digest(INPUT),'frozen_tool':json.loads(FROZEN.read_text()),'commands':commands,'repeat':repeat,'native_cad':'PASS: actual FCStd/STEP/all QueryVolumes; see native_cad_validation.json','body_inventory':{v:{'before':len(selected(baseline,v)),'after':len(selected(data,v)),'all_original_IDs_retained':True} for v in 'AB'},'remaining_inventory':after['summary'],'source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'cad/frame_mount').glob('*')) if p.is_file()},'raw_metadata_caveat':'hardcoded frozen checker source_commit_inputs/known_native_penetrations/tool_blockers are historical; use current input hash and this run','physical_parameters_and_safety':'UNKNOWN','G1':'OPEN'}
        # Hash only artifacts produced by THIS stage. Later evidence/figure/
        # human report/generation/manifest outputs must not feed back into run.
        owned=[p for directory in ('A','B','raw_checked_tool','inventory') for p in (out/directory).rglob('*') if p.is_file()]
        owned += [out/name for name in ('native_cad_validation.json','strict_cycles.json','cycle_assertions.json','work_and_module_service.json.gz','assessment.json','classifications.jsonl.gz','service_scenes.json.gz','interfaces.json','interval_evidence.json')]
        report['artifacts']={str(p.relative_to(out)):digest(p) for p in sorted(owned)}
        save(out/'run.json',report); print(json.dumps({'execution':report['execution'],'test_evaluation':report['test_evaluation'],'geometry':report['geometry'],'remaining':after['summary']}));return 0
    except Exception as e:
        failure={'execution':{'status':'FAILED','exit_code':1},'error':str(e),'commands':commands,'test_evaluation':suite,'whole_press_READY':'INDETERMINATE'}
        save(out/'failed_run.json',failure); print(json.dumps({'error':str(e)}),file=sys.stderr); return 1


if __name__=='__main__': sys.exit(main())
