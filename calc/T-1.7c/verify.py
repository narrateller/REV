"""Replay the engineering calculations and immutable project gates twice."""
import argparse
from hashlib import sha256
from math import isclose
import subprocess
import sys

import ntsecuritycon
import win32security

from study import HERE, ROOT, read_json, read_yaml, write_json

OUTPUTS=(
    'calc/T-1.7c/results.json','calc/T-1.7c/fea/status.json','design/frame.t17c.yaml',
    'design/slide_gate.t17c.yaml','design/params.t17c.yaml','metrics.json','gates.t17c.json',
)
GATE_ARGS=['ops/gates/calc_gates.py','--params','design/params.t17c.yaml',
           '--criteria','ops/criteria/design_criteria.yaml','--out','gates.t17c.json']


def run(*args):
    subprocess.run([sys.executable,'-B',*args],check=True,cwd=ROOT)


def replay():
    run('calc/T-1.7c/study.py')
    run(*GATE_ARGS)
    run('calc/T-1.7c/generate.py')
    return {name:sha256((ROOT/name).read_bytes()).hexdigest() for name in OUTPUTS}


def physical_tests(result,metrics):
    geom=result['layout']
    assert geom['channel_exit_x_mm']-geom['gate_back_x_mm']==205.
    assert geom['maximum_gate_thickness_preserving_5mm_axial_margin_mm']>=geom['closed_gate_thickness_mm']
    assert geom['minimum_relaxed_tail_clearance_mm']>=5.
    assert geom['gate_working_travel_mm']==75.
    assert [geom['overtravel_nominal_mm'],geom['overtravel_maximum_mm']]==[59.,69.]
    assert geom['main_installed_stroke_mm']==289.
    assert geom['nominal_floor_step_down_mm']>=0.
    assert geom['guide_corner_clearance_in_cast_R20_mm']>0.
    assert geom['side_clearance_per_side_after_max_recovery_mm']>0.
    assert geom['top_clearance_after_max_recovery_at_floor_mm']>0.
    assert not geom['unlined_passage_prevents_yaw_of_40mm_product']
    assert 0.<geom['qualified_lot_max_short_yaw_deg']<10.
    assert result['gate_opening']['opening_force_factor']>=2.
    assert result['mass']['nominal_kg']<=5000.
    for case in ('base','high'):
        lower,upper=[r for r in result['free_channel_cases'] if r['curve']==case]
        assert isclose(upper['transition_friction_N']/lower['transition_friction_N'],.5/.2)
        assert upper['ejection_peak_N']>=lower['ejection_peak_N']
        assert upper['peak_with_inertia_bound_N']<=result['rapid_pair_available_N']
        assert all(c['feasible'] and c['cycle_s']<=6. for c in upper['cycles'])
        assert upper['closed_gate_stack_force_on_dose_N']==0.
    lo,hi=result['pressure_sensitivity']['pressure_bracket_for_6s_MPa']
    assert 0.<lo<hi and hi-lo<.003
    assert abs(metrics['gate_delta_same_power_s'])<=.15
    assert all(row['status']=='PASS' for row in metrics['gates'].values())
    assert set(metrics['gates'])=={'G-PFACE','G-DOSE','G-CYCLE'}


def check_access(paths, *, read_contents):
    regular_users=win32security.CreateWellKnownSid(win32security.WinBuiltinUsersSid)
    failure=[]
    for path in paths:
        if read_contents:
            path.read_bytes()
        security=win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
                                                  win32security.DACL_SECURITY_INFORMATION)
        dacl=security.GetSecurityDescriptorDacl()
        rows=[(header,mask) for header,mask,sid in (dacl.GetAce(i) for i in range(dacl.GetAceCount()))
              if sid==regular_users]
        if not (any(header[0]==win32security.ACCESS_ALLOWED_ACE_TYPE and
                    mask & ntsecuritycon.FILE_GENERIC_READ==ntsecuritycon.FILE_GENERIC_READ for header,mask in rows)
                and all(header[0]!=win32security.ACCESS_DENIED_ACE_TYPE for header,_ in rows)):
            failure.append(str(path.relative_to(ROOT)))
    return failure


def verify(replay_fea_slices=False):
    slice_files=[HERE/'fea'/f'hex_slice_{level}.json' for level in range(3)]
    slice_replay={'status':'NOT_RUN','models':0}
    if replay_fea_slices:
        hashes=[sha256(path.read_bytes()).hexdigest() for path in slice_files]
        run('calc/T-1.7c/fea/contact_hex_slice.py','0','1','2')
        assert hashes==[sha256(path.read_bytes()).hexdigest() for path in slice_files]
        slice_replay={'status':'PASS','models':3,'method':'SHA-256 byte equality','sha256':hashes}
    elif (ROOT/'self_check.json').is_file():
        cached=read_json('self_check.json').get('fea',{}).get('slice_replay',{})
        if cached.get('status')=='PASS' and all(path.is_file() for path in slice_files):
            hashes=[sha256(path.read_bytes()).hexdigest() for path in slice_files]
            if hashes==cached.get('sha256'):
                slice_replay=cached
    first=replay()
    second=replay()
    assert first==second
    result=read_json('calc/T-1.7c/results.json')
    metrics=read_json('metrics.json')
    physical_tests(result,metrics)
    cases=result['free_channel_cases']
    files=[path for path in HERE.rglob('*') if path.is_file()]
    assert not any(path.suffix in ('.pyc','.msh','.frd','.inc','.dat','.sta','.cvg') for path in files)
    total=sum(path.stat().st_size for path in files)
    assert total<=5_000_000
    status_file=ROOT/'self_check.json'
    checked=sorted(set(files+[ROOT/name for name in OUTPUTS]+[ROOT/'report.md',ROOT/'TASK.md']))
    output={
        'task':'T-1.7c','round':2,'result':metrics['status'],'python_version':sys.version.split()[0],
        'gates':{'command':'REV_PYTHON -B '+' '.join(GATE_ARGS),'runs':2,'checks':metrics['gates'],
                 'delta_from_published_s':metrics['gate_delta_published_s'],
                 'delta_from_published_within_0p15_s':abs(metrics['gate_delta_published_s'])<=.15,
                 'delta_from_same_power_s':metrics['gate_delta_same_power_s']},
        'reproducibility':{'runs':2,'status':'PASS','method':'SHA-256 byte equality','sha256':second},
        'physical_tests':{'free_outlet_travel_geometry_and_inventory':'PASS',
                          'stack_friction_scaling_and_rapid_drive':'PASS','pressure_sensitivity_bracket':'PASS',
                          'nominal_mass_and_opening_reserve':'PASS',
                          'max_adjacent_time_step_cycle_difference_s':max(abs(r['cycles'][0]['cycle_s']-r['cycles'][1]['cycle_s'])
                                                                          for r in cases)},
        'fea':{'assembly':metrics['fea'],'paired_full_run_replay_status':'OPEN',
               'slice_replay':slice_replay,'numeric_tolerance':1e-6,
               'execution_record':read_json('calc/T-1.7c/fea/execution.json')},
        'calc_size_bytes':total,
    }
    write_json('self_check.json',output)
    unreadable=check_access(checked+[status_file],read_contents=True)
    git_files=subprocess.check_output(['git','-c','core.quotepath=false','ls-files','--cached','--others',
                                       '--exclude-standard','-z'],cwd=ROOT).decode('utf-8').split('\0')
    project_files=sorted({ROOT/name for name in git_files if name and (ROOT/name).is_file()})
    project_unreadable=check_access(project_files,read_contents=False)
    output['access']={'status':'PASS' if not (unreadable or project_unreadable) else 'FAIL',
                      'deliverable_files_read':len(checked)+1,'project_files_acl_checked':len(project_files),
                      'method':'Python read and Windows BUILTIN Users ACE with FILE_GENERIC_READ',
                      'unreadable_deliverables':unreadable,'project_files_without_ordinary_read_access':project_unreadable}
    write_json('self_check.json',output)
    assert not (unreadable or project_unreadable), (unreadable,project_unreadable)
    print(f'{len(checked)+1} files, {total} calc bytes; hydraulic replay PASS; {metrics["status"]}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fea-slices',action='store_true',help='Repeat the three completed diagnostic slice jobs.')
    verify(parser.parse_args().fea_slices)
