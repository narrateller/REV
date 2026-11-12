"""Scientific envelope views and separately classified native interfaces."""
from bridge import *

def present(out,reports):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    old=load(BASELINE)
    for v in VARS:
        data=load(input_path(v));fig,axes=plt.subplots(2,1,figsize=(15,8),sharex=True)
        for ax,d,title in [(axes[0],old,'Previous ASSUMED geometry'),(axes[1],data,'BASE_'+v+' fixed-budget / R3 linked research')]:
            for c in selected(d,v):
                if not (c['id'].startswith(('chamber_','channel_','pocket_','rod','punch','product_','end_stop','lock'))):continue
                lo,hi=bounds(d,c);color='#dd6c40' if c['id'] in ('rod','punch') else '#ba8954' if c['id'].startswith('product') else '#59a2b3'
                ax.add_patch(Rectangle((float(lo[0]),float(lo[2])),float(hi[0]-lo[0]),float(hi[2]-lo[2]),facecolor=color,edgecolor='#334455',alpha=.5))
            ax.set_ylim(-.4,.75);ax.set_xlim(-1,2.5);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(title);ax.set_ylabel('Z, m')
        axes[1].axvline(float(F(data['r3_nominal_exit'])),color='#bb4040',linestyle='--',label='R3 nominal output plane')
        axes[1].axvline(float(config(data,'exit_'+v)),color='#604080',linestyle=':',label='Preserved actual CAD output plane');axes[1].legend(fontsize=8);axes[1].set_xlabel('X, m')
        fig.suptitle('Research bounding-envelope section; native section_y0.svg and FCStd are separate. NOT REV construction.');fig.tight_layout()
        for suffix in ('svg','png','pdf'):fig.savefig(Path(out)/v/('sizing_before_after.'+suffix),dpi=140)
        plt.close(fig)
        fig,ax=plt.subplots(figsize=(14,6));scene=next(s for s in read_packed(Path(out)/v/'scenes.json.gz') if s['case']=='sufficient')
        for n,col in [('punch','#df663d'),('product_'+v,'#a87a41'),('rod','#406d9a')]:
            tx=[];xx=[]
            for st in scene['stages']:
                b=st['state'][n];tx.extend(map(float,map(F,st['time'])));xx.extend([float(F(b['lo'][0])),float(F(b['lo'][0])+F(b['delta'][0]))])
            ax.plot(tx,xx,label=n,color=col)
        ax.axhline(float(F(data['r3_nominal_exit'])),ls='--',label='R3 nominal exit');ax.axhline(float(config(data,'exit_'+v)),ls=':',label='Actual CAD exit');ax.grid(alpha=.2);ax.legend();ax.set_xlabel('Diagnostic time, s; feed/reset intervals remain ASSUMED');ax.set_ylabel('Rear X, m');ax.set_title('BASE_'+v+' fixed-budget: full diagnostic stroke and return; no REMOVE / READY not confirmed')
        fig.tight_layout()
        for suffix in ('svg','png','pdf'):fig.savefig(Path(out)/v/('motion.'+suffix),dpi=140)
        plt.close(fig)

def interfaces(out,write=True):
    from assess import POLICY,overlap
    from run import planar_contact_area
    from common import joint_pairs
    pairs=set(POLICY)|{tuple(sorted(r['pair'])) for r in joint_pairs()}
    pairs|={tuple(sorted(p)) for p in [('rod','punch'),('chamber_bottom','crossbar1'),('chamber_bottom','side_rail_L'),('chamber_bottom','side_rail_R')]}
    old=load(BASELINE);before=NativeWitness(ROOT/'cad/build/feed_power');after=NativeWitness(out);rows=[]
    try:
        for v in VARS:
            d=load(input_path(v));initial=checked.bodies(d,v);oldstate=checked.bodies(old,v)
            for pair in sorted(pairs):
                if not set(pair)<=set(initial):continue
                a=before.at(v,pair,oldstate,'0',['0','1']);b=after.at(v,pair,initial,'0',['0','1']);left=before.objects[v];right=after.objects[v]
                area_old=planar_contact_area(*(left[n].Shape for n in pair));area_new=planar_contact_area(*(right[n].Shape for n in pair))
                status='NATIVE_PENETRATION' if b['common_volume_mm3']>1e-5 else 'ALLOWED_CONDITIONAL_MATING' if area_new>0 else 'INDETERMINATE_LOST_INTERFACE' if area_old>0 else 'INDETERMINATE'
                rows.append({'variant':v,'pair':pair,'before_native':a,'after_native':b,'before_face_area_mm2':area_old,'after_face_area_mm2':area_new,'classification':status,'physical_fixing':'UNKNOWN','reason':'conditional prior mating/force topology; absence of positive area does not confirm a new load path'})
        result=json.loads(json.dumps({'interfaces':rows,'physical_force_path':'INDETERMINATE','COTS':'NOT_APPROVED','G1':'OPEN'}))
        if write:save(Path(out)/'native_interfaces.json',result)
        return result
    finally:before.close();after.close()
