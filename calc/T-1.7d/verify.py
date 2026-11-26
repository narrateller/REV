"""Replay design generation, gate inputs and record numerical evidence."""
from hashlib import sha256
import subprocess
import sys

from round2 import main as build
from study import FEA, HERE, ROOT, read_json, read_yaml, write_json
from evaluate import configure, periodic_run

GENERATED = (
    'calc/T-1.7d/results.json', 'metrics.json', 'design/frame.t17d.yaml',
    'design/slide_gate.t17d.yaml', 'design/cylinders.t17d.yaml', 'design/params.t17d.yaml', 'report.md',
)


def digest():
    return {name:sha256((ROOT/name).read_bytes()).hexdigest() for name in GENERATED}


def numeric_error(first, second):
    if isinstance(first,dict):
        assert first.keys()==second.keys()
        return max((numeric_error(value,second[key]) for key,value in first.items()),default=0.)
    if isinstance(first,list):
        return max((numeric_error(a,b) for a,b in zip(first,second,strict=True)),default=0.)
    if isinstance(first,(float,int)) and not isinstance(first,bool):
        return abs(first-second)
    assert first==second, (first,second)
    return 0.


def verified_replay():
    first=FEA/'r2_aligned_node54_replay_a_0.json'
    second=FEA/'r2_aligned_node54_replay_b_0.json'
    if not (first.is_file() and second.is_file()):
        return {'status':'NOT_RECORDED','scope':'54/100 mm, coupled, mesh 7.5 mm'}
    error=numeric_error(read_json(first),read_json(second))
    answer=dict(status='PASS' if error<=1.e-6 else 'FAIL',
                max_absolute_difference=error,tolerance=1.e-6,
                scope='54/100 mm, zero, 1.70 MN and 1.94 MN, coupled at h=7.5 mm, single solver thread')
    multi_a=FEA/'r2_aligned_node54_0.json'
    multi_b=FEA/'r2_aligned_node54_replay_0.json'
    if multi_a.is_file() and multi_b.is_file():
        answer['four_threads_diagnostic_max_absolute_difference']=numeric_error(read_json(multi_a),read_json(multi_b))
    return answer


def run_tests():
    command=[sys.executable,'-B','-m','pytest','-p','no:cacheprovider','tests/ops/test_calc_gates.py']
    run=subprocess.run(command,cwd=ROOT,check=True,capture_output=True,text=True)
    print(run.stdout,flush=True)
    return dict(status='PASS',command='REV_PYTHON '+ ' '.join(command[1:]),
                summary=next(line.strip(' =') for line in run.stdout.splitlines()[::-1] if 'passed' in line).split(' in ')[0])


def cycle_time_step_check(trial):
    dt_s=.0003125
    results={}
    for profile in ('realistic','pessimistic'):
        _, (model, main, settings, _, _)=configure(
            trial['geometry'],trial['moving_mass_kg'],profile=profile,
            gate_bore_mm=trial['gate_bore_mm'],rapid_mass_increment_kg=trial['rapid_mass_increment_kg'],
            **trial['cycle_settings'])
        run=periodic_run(model,main,90.,.64,settings,dt_s)
        assert run['feasible'] and run['cycle_s']<=6.
        results[profile]=dict(cycle_s=run['cycle_s'],
                              change_s=run['cycle_s']-trial['cycle'][profile]['cycle_s'])
    return dict(status='PASS',dt_s=dt_s,results=results)


def main():
    build()
    original=digest()
    build()
    assert original==digest(), 'Repeat generation changed an output'

    command=[sys.executable,'-B','ops/gates/calc_gates.py','--params','design/params.t17d.yaml',
             '--criteria','ops/criteria/design_criteria.yaml','--out','gates.t17d.json']
    subprocess.run(command,cwd=ROOT,check=True)
    gates=read_json('gates.t17d.json')
    result=read_json('calc/T-1.7d/results.json')
    trial=result['working_trial']
    compact={row['id']:{k:row[k] for k in ('status','value')} for row in gates['gates']}
    assert compact==result['gates']
    assert all(r['status']=='PASS' for r in compact.values())
    params=read_yaml('design/params.t17d.yaml')
    assert params['drive']['peak_kW']==36.
    assert all(not ph.get('group') for ph in params['cycle'] if ph.get('press') or ph['actuator']=='none')

    g=trial['geometry']
    assert g['channel_exit_x_mm']-g['gate_back_x_mm']==205.
    assert g['minimum_relaxed_tail_clearance_after_allowance_mm']>=5.
    assert g['punch_face_nominal_eject_end_x_mm']==205.+g['overtravel_nominal_mm']
    assert g['punch_face_maximum_eject_end_x_mm']==205.+g['overtravel_maximum_mm']
    assert g['main_installed_stroke_mm']-g['punch_face_maximum_eject_end_x_mm']==15.
    assert g['guide_corner_clearance_in_cast_R20_mm']>0.
    opening=trial['opening'][str(trial['gate_bore_mm'])]
    assert opening['safety_factor']>=2. and opening['acceleration_m_s2']==40.
    assert trial['mass']['nominal_kg']<5000.
    cycle=trial['cycle']
    assert cycle['gate_cycle_s']<=5.95
    assert cycle['realistic']['feasible'] and cycle['realistic']['cycle_s']<=6.
    assert cycle['pessimistic']['feasible'] and cycle['pessimistic']['cycle_s']<=6.
    assert abs(sum(cycle['gate_minus_reference_by_block_s'].values())-cycle['difference_gate_reference_s'])<1.e-8
    for profile in ('realistic','pessimistic'):
        run=cycle[profile]
        assert run['motion_events']['gate_close']['start_s']>=run['motion_events']['return']['gate_clear_s']
        assert run['peak_lp_deficit_L']<=params['drive']['accumulator']['usable_oil_L']+1.e-9
        assert abs(run['net_lp_oil_balance_L'])<1.e-5
        assert run['min_lp_gas_bar']>=38.-1.e-9
    assert max(trial['hydraulic']['cushion']['ideal_peak_screen_bar'].values())<315.
    for entry in result['fea'].get('r2_aligned_node54',{}).get('files',[]):
        if not entry.endswith('_failure.json'):
            solved=read_json(FEA/entry)
            for name in ('static','fatigue'):
                assert solved['loads'][name]['axial_balance_relative']<.005

    finer_time_step=cycle_time_step_check(trial)
    tests=run_tests()
    files=[f for f in HERE.rglob('*') if f.is_file()]
    deliverables=[ROOT/p for p in (*GENERATED,'gates.t17d.json')]
    for path in files+deliverables:
        path.read_bytes()
    size_bytes=sum(f.stat().st_size for f in files)
    largest_bytes=max(p.stat().st_size for p in files if FEA in p.parents)
    assert size_bytes<=5_000_000
    assert largest_bytes<=1_000_000
    assert not any(p.suffix in ('.msh','.frd','.pyc') for p in files)
    write_json('self_check.json',dict(
        task='T-1.7d',round=2,gates=compact,gate_command='REV_PYTHON '+' '.join(command[1:]),
        tests=tests,reference_time_step_check=finer_time_step,geometry_and_actuation='PASS_CALCULATION',cycle_phase_accounting='PASS',
        cycle_R2_and_pessimistic_limits='PASS',machine_nominal_mass='PASS',
        double_generation=dict(status='PASS',sha256=original), FEA_replay=verified_replay(),
        FEA_acceptance=result['acceptance'],numerical_attempts=result['fea']['r2_aligned_node54']['files'],
        package=dict(status='PASS',files=len(files),calc_bytes=size_bytes,largest_FEA_file_bytes=largest_bytes,
                     readable_with_workspace_account=True,read_permission_basis='Inherited builtin Users RX')))
    print(f'{len(files)} files, {size_bytes} bytes, largest FEA artifact {largest_bytes} bytes.',flush=True)


if __name__=='__main__':
    main()
