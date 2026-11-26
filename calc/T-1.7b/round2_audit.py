"""Repeat round-2 outputs, verify gates, and check the submitted Windows archive."""
import argparse
import ast
from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import yaml

from audit import compare
from frame_analytic import ROOT
from frame_fea import FEA, HERE, write_json
from round2 import assemble
from round2_report import render
from round2_screens import gate_geometry, opening
from study import read_json

PYTHON = (sys.executable, '-B')
GATES = ('G-PFACE','G-DOSE','G-CYCLE')
OUTPUTS = ('results.json','design/frame.t17b.yaml','design/slide_gate.t17b.yaml','metrics.json')


def run(*args):
    return subprocess.run([*PYTHON,*map(str,args)],cwd=ROOT,check=True)


def check_acl():
    result = subprocess.run(['icacls.exe','.','/T','/C'],cwd=ROOT,capture_output=True)
    acl = result.stdout.decode('oem',errors='replace')
    denials = re.findall(r'\(DENY\)\(([^()]*)\)',acl,flags=re.IGNORECASE)
    read_denied = [entry for entry in denials if set(entry.upper().split(',')) & {'R','RX','RD','GR','GA','F'}]
    checked = re.search(r'processed (\d+) files',acl)
    return {'status':'PASS' if result.returncode==0 and not read_denied else 'FAIL',
            'command':'icacls . /T /C', 'objects_checked':int(checked[1]) if checked else None,
            'deny_read_data_count':len(read_denied),'other_deny_ace_count':len(denials)-len(read_denied),
            'other_deny_scope':'.git sandbox metadata if present; write/delete/read-control flags',
            'unprivileged_access_basis':'No deny ACE covering ReadData and inherited Users read access. Normal file opens tested for all submitted files.'}


def archive_checks():
    files = sorted(path for path in HERE.rglob('*') if path.is_file())
    size_B = sum(path.stat().st_size for path in files)
    for path in files:
        with path.open('rb') as f:
            assert f.read(1), path
    for path in HERE.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    for path in FEA.glob('*.inp'):
        data = path.read_text(encoding='ascii').upper()
        assert '*NODE\n' not in data and '*ELEMENT,' not in data, path
    unwanted = {'.msh','.frd','.cvg','.dat','.sta','.pyc','.12d'}
    assert all(path.suffix.lower() not in unwanted for path in files), 'Remove temporary solve outputs'
    assert size_B<=5_000_000
    return {'status':'PASS','calc_bytes':size_B,'file_count':len(files),
            'method':'Parse Python, open calculation and deliverable files, inspect decks for embedded mesh, audit size.'}


def compare_outputs(first, second):
    parsed = yaml.safe_load
    raw = [(first/x).read_bytes()==(second/x).read_bytes() for x in OUTPUTS]
    numeric = [compare(parsed((first/x).read_text(encoding='utf-8')),parsed((second/x).read_text(encoding='utf-8')))
               for x in OUTPUTS]
    return {'status':'PASS' if all(raw) and all(numeric) else 'FAIL','absolute_numeric_tolerance':1e-6,
            'files':{label:{'byte_identical':x,'numeric_equal':y} for label,x,y in zip(OUTPUTS,raw,numeric,strict=True)}}


def check_scope():
    p = subprocess.run(['git','-c','core.quotepath=false','status','--porcelain=v1','-uall'],
                       cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
    allowed = {'TASK.md','design/frame.t17b.yaml','design/slide_gate.t17b.yaml',
               'gates.t17b.json','metrics.json','report.md','self_check.json'}
    paths = [row[3:] for row in p.stdout.splitlines() if row]
    other = [name for name in paths if name not in allowed and not name.startswith('calc/T-1.7b/')]
    return {'status':'PASS' if not other else 'FAIL','out_of_scope_changes':other,
            'initial_user_file':'TASK.md, present in worktree before round 2'}


def audit(replay_level):
    gate_args = ('--params','design/params.t14b.yaml','--criteria','ops/criteria/design_criteria.yaml','--out','gates.t17b.json')
    run(ROOT/'ops/gates/calc_gates.py',*gate_args)
    gate_report = read_json(ROOT/'gates.t17b.json')
    gates = {q['id']:{'status':q['status'],'value':q['value'],'unit':q['unit']}
             for q in gate_report['gates'] if q['id'] in GATES}
    assert set(gates)==set(GATES) and all(q['status']=='PASS' for q in gates.values())
    geo = gate_geometry()
    previous = read_json(HERE/'round1_results.json')
    side_mass_kg = previous['B']['integral_geometry_and_mass']['moving_mass_delta_kg']
    opening_drag_N = opening(45.)['extra_opening_drag_N']
    cases = {'cycle_comparison_r2.json':geo['local_blade_envelope_mass_delta_kg'],
             'cycle_comparison_r2_side.json':side_mass_kg}
    cycle_match = {}
    checks = [read_json(p) for p in sorted(FEA.glob('r2_replay_check_*.json'))]
    fea_replay = {'status':('PASS' if all(q['status']=='PASS' for q in checks) else 'FAIL') if checks else 'NOT_RUN',
                  'cases':[q['case'] for q in checks],'absolute_numeric_tolerance':1e-6}
    with TemporaryDirectory(prefix='r2_audit_',dir=HERE) as name:
        tmp = Path(name)
        first,second = tmp/'first',tmp/'second'
        for folder in (first,second):
            (folder/'design').mkdir(parents=True)
        assemble(first,first/'results.json')
        if replay_level is not None:
            stem = f'r2_seat_crown_{replay_level}.json'
            old = read_json(FEA/stem)
            command = [HERE/'round2_contact.py',replay_level]
            run(*command)
            new = read_json(FEA/stem)
            fea_replay = {'status':'PASS' if compare(old,new) else 'FAIL','cases':[stem],
                          'absolute_numeric_tolerance':1e-6}
        for file,mass_delta_kg in cases.items():
            test_path = tmp/file
            run(HERE/'cycle/compare.py',mass_delta_kg,'--opening-drag-N',opening_drag_N,'--out',test_path)
            cycle_match[file] = compare(read_json(HERE/file),read_json(test_path))
        assemble(second,second/'results.json')
        repeated = compare_outputs(first,second)
    result = assemble()
    report = render(result,previous['machine_mass'])
    (ROOT/'report.md').write_text(report,encoding='utf-8',newline='\n')
    for name in ('design/frame.t17b.yaml','design/slide_gate.t17b.yaml','gates.t17b.json','metrics.json','report.md'):
        assert (ROOT/name).read_bytes()
    assert result['B']['max_cycle_delta_s']<=.05
    assert geo['tail_clearance_over_local_insert_mm']<0. and geo['drop_bay_with_local_insert_mm']<190.
    for row in result['B']['short_span_FEA']:
        for load in row['loads'].values():
            assert abs(load['axial_reaction_N']+load['force_N'])/load['force_N']<=.003
    record = {
        'task':'T-1.7b','round':2,'engineering_status':result['result_status'],
        'tools':{'python':sys.version.split()[0],'gmsh':'4.15.0','calculix':'2.22'},
        'gates':gates,'gate_input':'design/params.t14b.yaml','gate_criteria_sha256':gate_report['criteria_sha256'],
        'regeneration':repeated,'cycle_repeat':{'status':'PASS' if all(cycle_match.values()) else 'FAIL','cases':cycle_match},
        'contact_replay':fea_replay,'contact_runs':len(result['B']['short_span_FEA']),
        'solver_commands':['python -B calc/T-1.7b/round2_contact.py 0 1 2','python -B calc/T-1.7b/round2_audit.py'],
        'contact_mesh_convergence':result['B']['short_span_convergence']['status'],
        'force_balance':{'status':'PASS' if result['B']['short_span_FEA'] else 'OPEN','relative_tolerance':.003},
        'geometry':{'audit':'PASS','candidate_acceptance':'FAIL','method':'Check the tail against the fixed lower strip in the actual axial stack.'},
        'archive':archive_checks(),'acl':check_acl(),'scope':check_scope(),
        'delivered_results_sha256':sha256((HERE/'results.json').read_bytes()).hexdigest(),
        'open':['No qualified gate support geometry. Actual insert/cast R20, C-CLR-01 and assembly fatigue proof remain open.',
                'ZSF flange and cylinder cover require G-FEA and measured transients.',
                'Cycle sensitivity assumes free discharge; opening block is reproducible geometrical interference.'],
    }
    write_json(ROOT/'self_check.json',record)
    assert all(record[k]['status']=='PASS' for k in ('regeneration','cycle_repeat','acl','scope','archive'))
    assert fea_replay['status']!='FAIL'


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay-level',type=int,choices=(0,1,2))
    audit(parser.parse_args().replay_level)
