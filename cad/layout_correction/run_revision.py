#!/usr/bin/env python3
"""NEW orchestration for geometry rev4. Does not patch the reviewed tool.

The original run_all is a frozen-baseline preservation harness; revised
geometry instead uses its checked public build/check entrypoints with inputs.
"""
import gzip,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from assess import analyze,ROOT,checked,NativeWitness
from layout_common import load,digest,selected,bounds

OUT=ROOT/'cad/build/layout_correction'
INPUT=ROOT/'cad/layout_correction/inputs.assumed.json'
FROZEN=ROOT/'verification/r4_layout_correction/frozen_tool.json'


def main():
    OUT.mkdir(parents=True,exist_ok=True);commands=[]
    def run(args):
        p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True);commands.append({'command':args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        if p.returncode:raise RuntimeError('command failed: '+' '.join(args)+'\n'+p.stderr)
    try:
        frozen=json.loads(FROZEN.read_text())
        for path,expected in frozen['sha256'].items():
            if digest(ROOT/path)!=expected:raise RuntimeError('checked tool changed '+path)
        data=load(INPUT);baseline=load(ROOT/'cad/layout/conditional_inputs.assumed.json')
        inventory={v:{'all_original_IDs_retained':{c['id'] for c in selected(baseline,v)}.issubset({c['id'] for c in selected(data,v)}),'before_count':len(selected(baseline,v)),'after_count':len(selected(data,v))} for v in 'AB'}
        if not all(x['all_original_IDs_retained'] for x in inventory.values()):raise RuntimeError('a baseline body was removed')
        run(['/usr/bin/python3','-m','unittest','discover','-s','cad/layout','-p','test_*.py'])
        run(['/usr/bin/python3','-m','unittest','discover','-s','models/rev_linked_scene','-p','test_*.py'])
        run(['/usr/bin/python3','-m','unittest','discover','-s','models/kinematic_press','-p','test_*.py'])
        run(['/usr/bin/python3','-m','unittest','discover','-s','cad/layout_correction','-p','test_*.py'])
        for v in 'AB':run(['/usr/bin/python3','cad/layout/build_model.py','--inputs',str(INPUT),'--variant',v,'--out',str(OUT/v)])
        run(['/usr/bin/python3','cad/layout/check_layout.py','--inputs',str(INPUT),'--models',str(OUT),'--out',str(OUT/'raw_checked_tool')])
        repeat={}
        with tempfile.TemporaryDirectory(prefix='rev-geometry-repeat-') as tmp:
            for v in 'AB':
                run(['/usr/bin/python3','cad/layout/build_model.py','--inputs',str(INPUT),'--variant',v,'--out',tmp+'/'+v])
                first=json.loads((OUT/v/'manifest.json').read_text());second=json.loads((Path(tmp)/v/'manifest.json').read_text());okay=all(first[k]==second[k] for k in ('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes'))
                repeat[v]='PASS' if okay else 'FAIL'
                if not okay:raise RuntimeError('semantic repeat failed '+v)
        result=analyze(data,OUT,OUT/'raw_checked_tool/all_pairs.json.gz',OUT)
        raw=json.loads((OUT/'raw_checked_tool/report.json').read_text());expected={'sufficient':('GEOMETRY_SUFFICIENT','NO_COLLISION'),'short':('SHORT_STROKE','NO_COLLISION'),'collision':('GEOMETRY_SUFFICIENT','COLLISION'),'unknown':('INDETERMINATE','INDETERMINATE')}
        outcomes=[]
        for c in raw['scenarios']:
            okay=(c['geometry'],c['path_collision'])==expected[c['case']];outcomes.append({'variant':c['variant'],'case':c['case'],'matches':okay,'geometry':c['geometry'],'path_collision':c['path_collision'],'path_ready':c['path_ready']})
            if not okay:raise RuntimeError('limited ejection regression '+c['variant']+'/'+c['case'])
        if any(s['target_penetration_rows'] for s in result['scenes']):raise RuntimeError('target penetration still present')
        for s in result['scenes']:
            if s['case'].startswith('service_') and (s['continuity_status']!='CONTINUOUS' or not s['positions_restored']):raise RuntimeError('service not continuous/restored')
            if s['case'] in ('service_gate','service_lock','service_end_stop','service_portal') and s['service_moving_penetrations']:raise RuntimeError('new functional service path penetrates solid '+str(s))
        for v,f in result['function_witnesses'].items():
            if not f['open_gate_clears_aperture'] or not f['closed_gate_covers_aperture']:raise RuntimeError('feed/closure lost '+v)
        if not all(x['positive_area_contact'] for x in result['function_witnesses']['B']['conditional_reaction_chain']):raise RuntimeError('conditional reaction chain disconnected')
        # Same old native counterexample times, new native geometry. The full
        # stroke claim comes from exact event regions, not these samples.
        scenes=json.loads(gzip.decompress((OUT/'raw_checked_tool/all_pairs.json.gz').read_bytes()));nw=NativeWitness(OUT);comparisons=[]
        try:
            old=json.loads((ROOT/'verification/r5_layout_output_review/evidence/dynamic_probe.json').read_text())
            for row in old:
                if set(row['pair']) not in ({'inlet_gate','pocket_R'},{'lock','guard_right'},{'lock','stop_support'},{'end_stop','guard_right'},{'end_stop','stop_support'}):continue
                scene=next(s for s in scenes if s['variant']==row['variant'] and s['case']=='sufficient');stage=next(st for st in scene['stages'] if st['phase']==row['phase']);after=nw.at(row['variant'],row['pair'],stage['state'],row['sample_time'],stage['time'])
                comparisons.append({'before_R5':row,'after_native':after})
                if after.get('common_volume_mm3',0)>1e-5:raise RuntimeError('native counterexample still penetrates')
        finally:nw.close()
        run(['/usr/bin/python3','cad/layout_correction/figures.py',str(OUT)])
        (OUT/'before_after_native.json').write_text(json.dumps(comparisons,indent=2)+'\n')
        changes=[]
        for v in 'AB':
            old={c['id']:c for c in selected(baseline,v)}
            for c in selected(data,v):
                before=None if c['id'] not in old else [[str(x) for x in a] for a in bounds(baseline,old[c['id']])];after=[[str(x) for x in a] for a in bounds(data,c)]
                if before!=after:changes.append({'variant':v,'id':c['id'],'before_bounds_m':before,'after_bounds_m':after})
        (OUT/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
        for path,expected_sha in frozen['sha256'].items():
            if digest(ROOT/path)!=expected_sha:raise RuntimeError('checked tool changed during run')
        artifacts={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name not in ('run.json','assessment.md','failed_run.json') and p.suffix not in ('.FCBak','.FCStd1')}
        sources=[INPUT,FROZEN,Path(__file__),Path(__file__).with_name('assess.py'),Path(__file__).with_name('test_assess.py'),Path(__file__).with_name('figures.py')]
        report={'status':'TARGET_GEOMETRIC_PENETRATIONS_REMOVED','new_orchestration_and_analysis':'REQUIRES_INDEPENDENT_REVIEW','baseline_review':'214b055f04d5b061a68dfd744afb6c956ac9a9d1','checked_tool':frozen,'input_sha256':digest(INPUT),'source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sources},'commands':commands,'inventory':inventory,'repeat':repeat,'limited_outcomes':outcomes,'target_positive_volume_rows':0,'whole_assembly_READY':'INDETERMINATE','physical_performance_and_safety':'UNKNOWN','artifacts':artifacts,'original_raw_metadata':'hardcoded source_commit_inputs/known_native_penetrations/tool_blockers are historical; current input hash and this manifest are authoritative for this iteration'}
        (OUT/'run.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: target strict penetrations removed over operating/return/service paths; remaining assembly interferences/UNKNOWN retained.')
    except Exception as e:
        (OUT/'failed_run.json').write_text(json.dumps({'error':str(e),'commands':commands},indent=2)+'\n');raise

if __name__=='__main__':main()
