"""Saved negative examples and exact event evidence, synthetic data only."""
from engine import pair,evaluate_phase,boundary,combine_link
from scenes import box


def execute():
    result=[]
    def record(id,evidence,ok): result.append({'id':id,'matches_expected':bool(ok),'evidence':evidence})
    rule={'ordered':['punch','product'],'allowed_time':[0,1],'patch_yz':[[0,1],[0,1]],'direction':'either'}
    stationary=box([-1,0,0],[0,1,1]); touching=box([0,0,0],[1,1,1])
    p=pair(stationary,box([4,0,0],[5,1,1]),[0,1],rule,[0,1]);record('C01-SEPARATED-LINK-ABSENT',p,p['link']=='LINK_ABSENT' and all(x['collision_status']=='CLEAR' for x in p['segments']))
    p=pair(stationary,box([0,0,0],[1,1,1],[1,0,0]),[0,1],rule,[0,1]);record('C01-DETACH',p,p['link']=='LINK_ABSENT' and p['segments'][0]['collision_status']=='ALLOWED_CONTACT' and any(x['collision_status']=='CLEAR' for x in p['segments']))
    p=pair(stationary,touching,[0,1],dict(rule,allowed_time=['1/2',1]),['1/2',1]);record('C01-OUTSIDE-TIME',p,p['segments'][0]['collision_status']=='COLLISION' and p['link']=='LINK_CONFIRMED')
    p=pair(box([-1,0,0],[0,2,1]),box([0,0,0],[1,2,1]),[0,1],rule,[0,1]);record('C01-OUTSIDE-PATCH',p,any(x['collision_status']=='COLLISION' for x in p['segments']))
    bad=box([1,0,0],[0,1,1]);p=pair(stationary,bad,[0,1],rule,[0,1]);record('C01-INVALID-AABB',p,p['input_status']=='INVALID_INPUT')
    p=pair(stationary,touching,[0,1],rule,[-1,1]);record('C01-INVALID-WINDOW',p,p['input_status']=='INVALID_INPUT')
    mystery=box([0,0,0],[1,1,1]);mystery['motion']=None;p=pair(stationary,mystery,[0,1],rule,[0,1]);record('C01-UNKNOWN',p,p['link']=='LINK_INDETERMINATE')
    rotation=box([0,0,0],[1,1,1]);rotation['motion']='rotation';p=pair(stationary,rotation,[0,1],rule,[0,1]);record('C01-UNSUPPORTED',p,p['input_status']=='INDETERMINATE')
    p=pair(box([-3,0,0],[-2,1,1],[6,0,0]),box([0,0,0],[1,1,1]),[0,1]);record('INTERMEDIATE-COLLISION',p,p['segments'][0]['collision_status']=='CLEAR' and p['segments'][-1]['collision_status']=='CLEAR' and any(x['collision_status']=='COLLISION' for x in p['segments']))
    p=pair(box([0,0,0],[1,1,1]),box([0,0,2],[1,1,3]),[0,1]);record('OVERLAPPING-XY-DISJOINT-Z',p,all(x['collision_status']=='CLEAR' for x in p['segments']))
    p=pair(box(['-1/10','-1/10',0],['1/10','1/10',1],[4,0,0]),box(['19/10','-31/10',0],['21/10','-29/10',1],[0,4,0]),[0,1]);record('TRAJECTORIES-DIFFERENT-TIMES',p,all(x['collision_status']=='CLEAR' for x in p['segments']))
    scene={'phase':'B-EJECT','time':[0,1],'registry':['punch','channel_wall','unknown_body'],'bodies':{'punch':box([0,0,0],[1,1,1],[1,0,0]),'channel_wall':box([0,0,0],[1,1,1]),'unknown_body':None}}
    p=evaluate_phase(scene);statuses=[x['collision_status'] for row in p['pairs'] for x in row['segments']];record('COLLISION-AND-UNKNOWN-CHANNEL-WALL',p,'COLLISION' in statuses and 'INDETERMINATE' in statuses and p['expected_pairs']==3)
    previous={'phase':'A','time':[0,1],'registry':['residue_1'],'bodies':{'residue_1':box([0,0,0],[1,1,1])}}
    following={'phase':'B','time':[1,2],'registry':[],'bodies':{}}
    p=boundary(previous,following,[]);record('RESIDUE-DISAPPEARANCE',p,p['status']=='DISCONTINUITY')
    following={'phase':'B','time':[2,3],'registry':['residue_1'],'bodies':previous['bodies']};p=boundary(previous,following,[]);record('TIME-DISCONTINUITY',p,p['status']=='DISCONTINUITY')
    following={'phase':'B','time':[1,2],'registry':['residue_1'],'bodies':{'residue_1':box([2,0,0],[3,1,1])}};p=boundary(previous,following,[]);record('POSITION-DISCONTINUITY',p,p['status']=='DISCONTINUITY')
    moving=box([-1,0,0],[0,1,1],[1,0,0]); ahead=box(['1/2',0,0],['3/2',1,1])
    p=pair(moving,ahead,[0,1],rule,['1/2','1/2']);record('C01-APPROACH-BOUNDARY',p,p['link']=='LINK_CONFIRMED' and p['segments'][0]['collision_status']=='CLEAR' and any(x['collision_status']=='ALLOWED_CONTACT' and x['from']=='1/2' for x in p['segments']))
    nonseparating=dict(rule,direction='nonseparating');p=pair(stationary,box([0,0,0],[1,1,1],[1,0,0]),[0,1],nonseparating,[0,1]);record('C01-FORBIDDEN-DIRECTION',p,p['segments'][0]['collision_status']=='COLLISION')
    p1=pair(stationary,touching,[0,1],rule,[0,1]);p2=pair(stationary,box([0,0,0],[1,1,1],[1,0,0]),[1,2],dict(rule,allowed_time=[1,2]),[1,2]);value=combine_link([{'time':[0,1],'result':p1},{'time':[1,2],'result':p2}],[0,2]);record('C01-PIECEWISE-DETACH',{'first':p1,'second':p2,'combined_link':value},value=='LINK_ABSENT')
    previous={'phase':'B-EJECT','time':[0,1],'registry':['product_B'],'bodies':{'product_B':box([0,0,0],[1,1,1],[1,0,0])}}
    following={'phase':'B-RESET','time':[1,2],'registry':[],'bodies':{}}
    event={'type':'REMOVE','id':'product_B','time':1,'boundary':2,'geometry':box([1,0,0],[2,1,1])}
    p=boundary(previous,following,[event]);record('PREMATURE-REMOVE',p,p['status']=='DISCONTINUITY')
    cube=box([0,0,0],[1,1,1]); previous={'phase':'before','time':[0,1],'registry':['residue_1'],'bodies':{'residue_1':cube}}; following={'phase':'after','time':[1,2],'registry':['product_new'],'bodies':{'product_new':cube}}
    p=boundary(previous,following,[{'type':'CREATE','id':'product_new','time':1}]);record('R5-B01-MISSING-RESIDUE-UNKNOWN-CREATE',p,p['status']=='DISCONTINUITY' and p['unexplained_removed']==['residue_1'] and bool(p['event_uncertainties']))
    same={'phase':'after','time':[1,2],'registry':['residue_1'],'bodies':{'residue_1':cube}}
    p=boundary(previous,same,[{'type':'CREATE','id':'other','time':1}]);record('R5-B02-EXTRA-CREATE',p,p['status']=='INVALID_INPUT')
    edge_rule=dict(rule,patch_yz=[[0,2],[0,1]])
    p=pair(box([-1,0,0],[0,1,1]),box([0,1,0],[1,2,1]),[0,1],edge_rule,[0,1]);record('R5-B03-ZERO-AREA-EDGE',p,p['link']!='LINK_CONFIRMED' and all(x['collision_status']=='COLLISION' for x in p['segments']))
    p=pair(box([-1,0,0],[0,1,1]),box([0,1,1],[1,2,2]),[0,1],edge_rule,[0,1]);record('R5-B03-ZERO-AREA-POINT',p,p['link']!='LINK_CONFIRMED')
    p=pair(box([-1,0,0],[0,1,1]),box([0,'999999/1000000',0],[1,2,1]),[0,1],edge_rule,[0,1]);record('R5-B03-SMALL-POSITIVE-AREA',p,p['link']=='LINK_CONFIRMED')
    previous['time']=[0,'1'];same['time']=['2/2',2];p=boundary(previous,same,[]);record('R5-W01-EQUIVALENT-TIME',p,p['status']=='CONTINUOUS' and p['time_contiguous'])
    empty={'phase':'before','time':[0,1],'registry':[],'bodies':{}};new={'phase':'after','time':[1,2],'registry':['product_new'],'bodies':{'product_new':cube}};ev={'type':'CREATE','id':'product_new','time':1}
    p=boundary(empty,new,[ev,dict(ev,time='2/2')]);record('R5-B02-DUPLICATE-EVENT',p,p['status']=='INVALID_INPUT')
    p=boundary(empty,new,[dict(ev,time=2)]);record('R5-W01-WRONG-EVENT-TIME',p,p['status']=='INVALID_INPUT')
    return result
