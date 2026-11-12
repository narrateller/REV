"""Check that this tool-only iteration preserves the reviewed geometry/evidence."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
from layout_common import ROOT,digest


def canonical_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--models',required=True);p.add_argument('--out',required=True);a=p.parse_args();models=Path(a.models)
    baseline_path=ROOT/'verification/r4_layout_tool_fix/geometry_baseline.json';base=json.loads(baseline_path.read_text())
    immutable={path:digest(ROOT/path)==expected for path,expected in base['immutable_files'].items()}
    images={path:digest(models/path)==expected for path,expected in base['images'].items()}
    manifests={v:canonical_hash(json.loads((models/v/'manifest.json').read_text())['objects'])==base['manifest_objects'][v] for v in 'AB'}
    scenes=json.loads(gzip.decompress((models/'checks/all_pairs.json.gz').read_bytes()));canonical=[{k:r[k] for k in ('variant','case','stages')} for r in scenes]
    matrix=canonical_hash(canonical)==base['all_phase_states_and_pair_evidence_sha256']
    original=ROOT/'verification/r5_layout_output_review/evidence';checks=models/'checks'
    static=json.loads((checks/'native_static_recheck.json').read_text());old_static=json.loads((original/'cad_probe.json').read_text());static_match={};positives={}
    for v in 'AB':
        rows=static[v]['static_brep_cases'];old=old_static[v]['static_brep_cases']
        static_match[v]=len(rows)==len(old) and all(x['pair']==y['pair'] and x['adapter']==y['adapter'] and math.isclose(x['common_volume_mm3'],y['common_volume_mm3'],rel_tol=1e-9,abs_tol=1e-5) for x,y in zip(rows,old))
        positives[v]=sum(r['common_volume_mm3']>0 for r in rows)
    dynamic=json.loads((checks/'native_dynamic_recheck.json').read_text());old_dynamic=json.loads((original/'dynamic_probe.json').read_text())
    dynamic_match=len(dynamic)==len(old_dynamic) and all(all(x[k]==y[k] for k in ('variant','phase','pair','sample_time')) and math.isclose(x['common_volume_mm3'],y['common_volume_mm3'],rel_tol=1e-9,abs_tol=1e-5) for x,y in zip(dynamic,old_dynamic))
    query_path=ROOT/'verification/r4_query_volume_fix/query_geometry_baseline.json';query_base=json.loads(query_path.read_text())
    current=json.loads((checks/'report.json').read_text())['cad_adapter']
    query_match={v:current[v]['query_volumes']==query_base['query_records'][v] for v in 'AB'}
    okay=all(immutable.values()) and all(images.values()) and all(manifests.values()) and matrix and all(static_match.values()) and dynamic_match and all(query_match.values())
    report={'status':'PASS' if okay else 'FAIL','baseline_commit':base['source_commit'],'baseline_sha256':digest(baseline_path),'immutable_files':immutable,'PNG_images_identical':images,'manifest_geometry_identical':manifests,'all_phase_states_and_pair_evidence_identical':matrix,'phase_pair_rows':sum(len(st['pairs']) for r in scenes for st in r['stages']),'native_static_recheck_matches_R5':static_match,'static_positive_common_volume_counts':positives,'native_dynamic_recheck_matches_R5':dynamic_match,'query_geometry_identical_to_5449fb9':query_match,'whole_assembly':'unchanged assumed interferences, READY INDETERMINATE; no correction of geometry claimed','files':{str(p.relative_to(ROOT)):digest(p) for p in (baseline_path,query_path,checks/'native_static_recheck.json',checks/'native_dynamic_recheck.json')}}
    Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print('geometry/phase matrix and native R5 penetrations preserved: '+report['status']);return 0 if okay else 1


if __name__=='__main__':raise SystemExit(main())
