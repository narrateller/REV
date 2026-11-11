import sys,json,gzip,subprocess
from pathlib import Path
from fractions import Fraction as F
root=Path(sys.argv[1]);base=json.loads(subprocess.check_output(['git','show','de377f012da08f34796b2e59aee663ba0b2b3d2b:cad/layout/conditional_inputs.assumed.json'],cwd=root));new=json.loads((root/'cad/layout_correction/inputs.assumed.json').read_text());scenes=json.load(gzip.open(root/'cad/build/layout_correction/raw_checked_tool/all_pairs.json.gz','rt'));out={}
def cfg(d,k):return d['parameters'][d['config'][k]]['value']
for v in 'AB':
 s=next(s for s in scenes if s['variant']==v and s['case']=='sufficient');initial=s['stages'][0]['state'];closed=next(st for st in s['stages'] if st['phase'] in ('A-PRESS-OUT','B-PRESS'))['state'];g=closed['inlet_gate'];x=[F(initial['chamber_top_rear']['hi'][0]),F(initial['chamber_top_front']['lo'][0])];y=[F(initial['chamber_left']['hi'][1]),F(initial['chamber_right']['lo'][1])]
 r={'working_strokes_unchanged':{k:F(cfg(base,k))==F(cfg(new,k)) for k in ('doser_fill_y','gate_isolate_y','travel_'+v,'short_'+v)+ (('open_lock_y','open_stop_y') if v=='B' else ())},'open_gate_clear_xy':F(initial['inlet_gate']['lo'][1])>=y[1],'closed_gate_cover_xy':F(g['lo'][0])<=x[0] and F(g['hi'][0])>=x[1] and F(g['lo'][1])<=y[0] and F(g['hi'][1])>=y[1],'gate_inside_split_wall_slot_z':F(closed['pocket_R_lower']['hi'][2])<F(g['lo'][2])<F(g['hi'][2])<F(closed['pocket_R']['lo'][2]),'ready_return_phase_present':s['stages'][-1]['phase'].endswith('READY-RETURNED'),'link':s['required_link'],'path_transition':s['path_transition'],'path_ready':s['path_ready'],'reaction_contacts':[]}
 if v=='B':
  for a,b in [('end_stop','lock'),('lock','stop_support'),('lock','stop_support_L'),('stop_support','stop_support_bridge'),('stop_support_L','stop_support_bridge'),('stop_support_bridge','side_rail_L'),('stop_support_bridge','side_rail_R')]:
   widths=[min(F(initial[a]['hi'][i]),F(initial[b]['hi'][i]))-max(F(initial[a]['lo'][i]),F(initial[b]['lo'][i])) for i in range(3)];zero=[i for i,w in enumerate(widths) if w==0];area=F(1)
   for w in widths:
    if w:area*=w
   assert len(zero)==1 and all(w>=0 for w in widths) and area>0
   r['reaction_contacts'].append({'pair':[a,b],'axis':zero[0],'positive_face_area_m2':str(area)})
 assert all(r['working_strokes_unchanged'].values()) and r['open_gate_clear_xy'] and r['closed_gate_cover_xy'] and r['gate_inside_split_wall_slot_z'] and r['ready_return_phase_present'] and r['link']=='LINK_CONFIRMED'
 out[v]=r
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print(out)
