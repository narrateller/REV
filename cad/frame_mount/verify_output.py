"""Read-only self-check of published geometry and reports. Requires R5 review.

No manifest, input, CAD, report or evidence is written on success or failure.
Emit a deterministic JSON result on stdout; use generate.py explicitly to build.
"""
import collections,gzip,json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
from publication import verify_manifest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'cad/layout_correction'))
sys.path.insert(0,str(ROOT/'cad/layout'))
from layout_common import load,digest
from cad_validation import check_cad_adapter
from outcomes import evaluate_suite
from verify_cycles import verify_cycles


def main():
    out=ROOT/'cad/build/frame_mount';verification=ROOT/'verification/r4_frame_mount'
    def read(p):return json.loads(Path(p).read_text())
    report={'scope':'R4 self-check; independent R5 NOT_RUN','whole_press_READY':'INDETERMINATE','G1':'OPEN'}
    try:
        publication=verify_manifest(ROOT)
        data=load(ROOT/'cad/frame_mount/inputs.assumed.json')
        run=read(out/'run.json');proof=read(out/'geometry_evidence.json');assessment=read(out/'assessment.json');inventory=read(out/'inventory/inventory.json');interval=read(out/'interval_evidence.json')
        assert run['execution']=={'status':'COMPLETED','exit_code':0} and run['test_evaluation']['status']=='PASS'
        assert run['input_sha256']==digest(ROOT/'cad/frame_mount/inputs.assumed.json')
        for p,sha in run['source_hashes'].items():assert digest(ROOT/p)==sha,('source',p)
        for p,sha in run['artifacts'].items():assert digest(out/p)==sha,('artifact',p)
        frozen=read(verification/'frozen_tool.json')
        for p,sha in frozen['sha256'].items():
            assert digest(ROOT/p)==sha,('reviewed tool',p)
            original=subprocess.check_output(['git','show',frozen['reference_commit']+':'+p],cwd=ROOT)
            assert original==(ROOT/p).read_bytes(),('git reviewed tool',p)
        scenes=json.loads(gzip.decompress((out/'raw_checked_tool/all_pairs.json.gz').read_bytes()))
        suite=evaluate_suite(scenes,data);assert suite['status']=='PASS'
        assert verify_cycles(scenes,data)==read(out/'cycle_assertions.json')
        assert suite==read(out/'strict_cycles.json')
        assert sum(bool(r['limited_cycle_success']) for r in suite['scene_results'])==2
        actual_cad=check_cad_adapter(data,out,ROOT/'cad/frame_mount/inputs.assumed.json')
        assert actual_cad==read(out/'native_cad_validation.json')
        assert all(v['query_geometry_match'] and v['query_count']==2 for v in actual_cad.values())
        assert not interval['changed_body_positive_overlap_rows'] and not interval['previous_target_positive_overlap_rows'] and not interval['cylinder_service_positive_overlap_rows']
        assert proof['coverage_rows']==interval['total_all_pair_rows'] and not proof['coverage_errors']
        assert proof['changed_group_counts'].get('POSITIVE_BOUND_OVERLAP',0)==0
        assert proof['previous_target_counts']=={'NO_POSITIVE_VOLUME_ON_INTERVAL':proof['previous_target_rows']}
        assert proof['cylinder_service_counts']=={'NO_POSITIVE_VOLUME_ON_INTERVAL':proof['cylinder_service_rows']}
        assert len(proof['before_after_native'])==18 and all(r['before']['common_volume_mm3']>1e-5 and r['after']['common_volume_mm3']<=1e-5 for r in proof['before_after_native'])
        assert len(proof['service_sequences'])==14
        assert all(s['continuity']=='CONTINUOUS' and s['return']=='RESTORED_GEOMETRY' for s in proof['service_sequences'])
        joints=read(out/'interfaces.json');assert len(joints)==58
        assert all(r['native_contact_face_area_mm2']>0 and r['native']['common_volume_mm3']<=1e-5 for r in joints)
        positive={'PENETRATION','ENVELOPE_INTERSECTION','NATIVE_PENETRATION_WITNESS'}
        controls={tuple(sorted(p)):0 for p in [('guard_right','pump_motor'),('output_support','stop_support_bridge')]}
        # Preserve all critical newly introduced gate/portal bodies from rev6.
        prior_new={'gate_service_cap','gate_house_front','gate_house_rear','gate_house_top','pocket_R_lower','stop_support_L','stop_support_bridge'}
        total=0;all_nonclear=set()
        with gzip.open(out/'classifications.jsonl.gz','rt') as stream:
            for line in stream:
                row=json.loads(line);total+=1;pair=tuple(row['pair'])
                if row['class']!='CLEAR':all_nonclear.add((row['variant'],pair))
                if pair in controls:
                    controls[pair]+=1;assert row['class'] in ('CLEAR','ALLOWED_SYNTHETIC_TOUCH'),('regression control',row)
                if prior_new.intersection(pair):assert row['class'] not in positive,('rev6 body regression',row)
        assert total==proof['coverage_rows'] and all(controls.values())
        assert all_nonclear=={(r['variant'],tuple(r['pair'])) for r in inventory['rows']},'finite inventory missing/extra pair'
        assert dict(collections.Counter(r['classification'] for r in inventory['rows']))==inventory['summary']
        remaining=[r for r in inventory['rows'] if r['classification']=='NATIVE_PENETRATION']
        assert len(remaining)==20,'remaining known penetrations unexpectedly disappeared'
        assert all(r['status']=='OPEN' and not r['control_context'] for r in remaining)
        assert all(s['target_penetration_rows']==0 for s in assessment['scenes'])
        assert assessment['whole_assembly_READY']=='INDETERMINATE'
        assert all(f['open_gate_clears_aperture'] and f['closed_gate_covers_aperture'] for f in assessment['function_witnesses'].values())
        assert all(r['positive_area_contact'] for r in assessment['function_witnesses']['B']['conditional_reaction_chain'])
        figure=read(out/'figure_manifest.json')
        for p,sha in figure['sha256'].items():assert digest(out/p)==sha,('figure',p)
        for document in (figure,proof):
            for p,sha in document['sources'].items():assert digest(ROOT/p)==sha,('provenance',p)
        manifest=read(verification/'input_manifest.json')
        for p,sha in manifest['inputs_sha256'].items():assert digest(ROOT/p)==sha,('input manifest',p)
        assert digest(ROOT/'params/registry.yaml')==digest(verification/'registry_snapshot.yaml')
        protected=['cad/layout','cad/layout_correction','models','params','drives','cad/build/layout_correction','cad/build/research_layout','verification/r4_layout_correction','verification/r4_analysis_fix','verification/r5_layout_new_recheck','verification/r5_layout_correction_review','verification/r5_layout_output_review']
        p=subprocess.run(['git','diff','--exit-code','04efe5703e339112b7d007665b9f3672f0572d37','--',*protected],cwd=ROOT,capture_output=True,text=True)
        assert p.returncode==0,('historical code/geometry/review changed',p.stdout[:1000])
        report.update({'status':'PASS','execution':{'status':'COMPLETED','exit_code':0},'test_evaluation':{'status':'PASS'},'reviewed_modules_unchanged':len(frozen['sha256']),'native_CAD':{v:{'solids':r['solid_count'],'queries':r['query_count'],'status':r['status']} for v,r in actual_cad.items()},'all_pair_rows':total,'finite_inventory_rows':len(inventory['rows']),'changed_group_rows':proof['changed_group_rows'],'changed_group_counts':proof['changed_group_counts'],'target_regression_rows':proof['previous_target_rows'],'cylinder_service_rows':proof['cylinder_service_rows'],'full_service_sequences':len(proof['service_sequences']),'native_before_after_pairs':len(proof['before_after_native']),'native_interfaces':len(joints),'remaining_native_penetration_pairs':len(remaining),'design_counterexample_controls':[{'pair':list(p),'full_interval_rows':n} for p,n in controls.items()],'historical_code_CAD_reviews_probes':'UNCHANGED from 04efe57','commands':['/usr/bin/python3 cad/frame_mount/run.py','/usr/bin/python3 cad/frame_mount/geometry_evidence.py','/usr/bin/python3 cad/frame_mount/figures.py','/usr/bin/python3 cad/frame_mount/report.py','/usr/bin/python3 cad/frame_mount/verify_output.py']})
        report['publication']=publication
        report['commands']=['/usr/bin/python3 cad/frame_mount/generate.py','/usr/bin/python3 cad/frame_mount/verify_output.py']
        print(json.dumps(report,indent=2));return 0
    except Exception as e:
        reason=str(e) or repr(e)
        report.update({'status':'FAIL','execution':{'status':'COMPLETED','exit_code':1},'reason':reason})
        print(json.dumps(report,indent=2));print('SELF-CHECK FAILED: '+reason,file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
