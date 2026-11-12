"""Explicit author calculation of additional nominal native interface conditions."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'cad/calculated_layout'))
from bridge import *
from run import planar_contact_area

def main():
    old=load(BASELINE);before=NativeWitness(ROOT/'cad/build/feed_power');after=NativeWitness(OUT);rows=[];params={}
    try:
        for v in VARS:
            d=load(input_path(v));a=checked.bodies(old,v);b=checked.bodies(d,v)
            pairs=[('rod','punch'),('cylinder_mount_rear','cylinder_barrel')]
            pairs += [('clamp_L','channel_left'),('clamp_R','channel_right'),('clamp_L','clamp_mount'),('clamp_R','clamp_mount'),('channel_bottom','chamber_bottom')] if v=='A' else [('end_stop','lock'),('lock','stop_support'),('lock','stop_support_L')]
            for pair in pairs:
                x=before.at(v,pair,a,'0',['0','1']);y=after.at(v,pair,b,'0',['0','1']);oldarea=planar_contact_area(*(before.objects[v][n].Shape for n in pair));newarea=planar_contact_area(*(after.objects[v][n].Shape for n in pair))
                status='NATIVE_PENETRATION' if y['common_volume_mm3']>1e-5 else 'ALLOWED_CONDITIONAL_MATING' if newarea>0 else 'INDETERMINATE_LOST_INTERFACE' if oldarea>0 else 'INDETERMINATE'
                row={'variant':v,'pair':pair,'before_native':x,'after_native':y,'before_contact_area_mm2':oldarea,'after_contact_area_mm2':newarea,'classification':status,'physical_load_transfer_and_clamp_stroke':'UNKNOWN'}
                if status=='INDETERMINATE_LOST_INTERFACE':
                    pid='R4CL_'+v+'_'+pair[0].upper()+'_GAP';row['gap_parameter']=pid
                    params[pid]={'revision':1,'value':y['distance_mm']/1000,'unit':'m','lifecycle':'CALCULATED','scope':'ASSUMED_RESEARCH_ONLY_NOT_REV','formula':'native distToShape(initial synthetic solids) / 1000','source_parameters':{c['id']:c for c in selected(d,v) if c['id'] in pair},'input_sha256':digest(input_path(v)),'tolerance':None,'uncertainty':None,'physical_truth':'UNKNOWN'}
                rows.append(row)
    finally:before.close();after.close()
    save(AUDIT/'functional_interfaces.json',{'rows':rows,'parameters':params,'calculation':{'script_sha256':digest(Path(__file__)),'native_models':{str(p.relative_to(ROOT)):digest(p) for folder in (ROOT/'cad/build/feed_power',OUT) for p in folder.glob('*/layout_*.FCStd')}},'scope':'additional functional topology, not a proof of physical force closure','G1':'OPEN'})
    print(len(rows),'functional interfaces;',len(params),'registered conditional gap outputs')
if __name__=='__main__':main()
