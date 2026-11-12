"""Independent Decimal arithmetic from visually checked brochure numbers.
Checks arithmetic/provenance only; does not validate material law/equipment.
Usage: .venv/bin/python -B arithmetic_check.py ROOT OUTPUT_JSON
"""
import hashlib,json,math,subprocess,sys
from decimal import Decimal as D,localcontext
from pathlib import Path
import yaml
R=Path(sys.argv[1]).resolve();p=yaml.safe_load((R/'params/registry.yaml').read_text());P={k:v for domain in p['domains'].values() for k,v in domain.items()}
with localcontext() as ctx:
 ctx.prec=50;pi=D('3.1415926535897932384626433832795028841971693993751')
 area=D('150')*D('60')*D('0.001')**2;volume_min=area*D('40')*D('0.001');volume_max=area*D('110')*D('0.001')
 rate=D(600)/D(3600);massrate=rate*D('0.83');sigma=D(1700)*D('9.80665')/D('0.0001');force=sigma*area;bore=(D(4)*force/(pi*D('30000000'))).sqrt();flow=D(30000)/D(30000000)
 values={'BP500_D_AREA':area,'BP500_D_VOL_MIN':volume_min,'BP500_D_VOL_MAX':volume_max,'BP500_D_MASS_RATE':massrate,'BP500_D_INTERVAL':1/rate,'REV_D_FACE_AREA':area,'REV_D_FACE_FORCE':force,'REV_D_IDEAL_BORE':bore,'BP500_D_IDEAL_FLOW':flow}
 output={k:{'Decimal_result':str(v),'stored_value':P[k]['value'],'unit':P[k]['unit'],'float_arithmetic_agrees':math.isclose(float(v),P[k]['value'],rel_tol=5e-15,abs_tol=1e-18),'scope':P[k]['scope'],'lifecycle':P[k]['lifecycle']} for k,v in values.items()}
 for k,v in output.items():assert v['float_arithmetic_agrees'] and v['lifecycle']=='CALCULATED',k
 assert D(str(P['REV_ASSUMED_SIGMA']['value']))==sigma
 assert all(P[k]['lifecycle']=='ASSUMED' and P[k]['scope']=='REV_RESEARCH_SCENARIO_ONLY' for k in ('REV_ASSUMED_WIDTH','REV_ASSUMED_HEIGHT','REV_ASSUMED_LENGTH','REV_ASSUMED_SIGMA','REV_ASSUMED_OIL_PRESSURE'))
 # Check every saved result's snapshot, immediate dependencies, code/PDF hashes.
 def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
 manifests={}
 for k in values:
  f=R/P[k]['calculation']['output'];m=json.loads(f.read_text());checks={'registry_snapshot_matches':sha(R/m['registry_snapshot'])==m['registry_sha256']==sha(R/'params/registry.yaml'),'script_matches':m['script_sha256']==sha(R/'scripts/bp500_basis.py'),'code_files_match':all(sha(R/a['path'])==a['sha256'] for a in m['code_files']),'PDF_matches':all(sha(R/a['path'])==a['sha256'] for a in m['artifacts']),'inputs_match_registry':all(a['value']==P[a['id']]['value'] and a['unit']==P[a['id']]['unit'] and a['revision']==P[a['id']]['revision'] for a in m['inputs']),'output_matches_registry':m['outputs'][0]['value']==P[k]['value'] and m['outputs'][0]['unit']==P[k]['unit']}
  assert all(checks.values()),(k,checks);manifests[k]=checks
 result={'checked_C':'4fd6f32b4df3186a805ac7e654be6c4c9e1c6a50','source_units':'PDF p.4: 150x60x40..110 mm, 600 units/h and 0.83 kg, literal 1700 kg/cm2; PDF p.3: 300 bar, 30 kW','conditional_sigma_Pa':str(sigma),'conditional_massrate_kg_h':str(massrate*D(3600)),'conditional_ideal_flow_L_min':str(flow*D(60000)),'reference_installed_power_sum_kW':str(D(30)+D('2.6')+D('1.5')),'stated_reference_total_kW':'34.2','source_power_discrepancy_kW':str(D('34.2')-(D(30)+D('2.6')+D('1.5'))),'outputs':output,'saved_manifests':manifests,'UNKNOWN_values':{k:None for k,v in P.items() if k.startswith('REV_') and v['value'] is None},'physical_validation':False,'equipment_selection':False,'range_approval':False}
Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('PASS: 9 conditional arithmetic results and saved dependencies; physical assumptions NOT validated')
