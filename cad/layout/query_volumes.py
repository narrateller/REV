"""Canonical query-volume definitions, derived from fixed research inputs.

These volumes are query geometry, never material solids in STEP or pair matrices.
The manifest is an observation and does not define their expected registry.
"""
from layout_common import selected,bounds,config

QUERY_SOURCES={'CylinderRemoval':'cylinder_barrel','DoserRemoval':'doser_slide'}


def expected_queries(data,variant):
    components={c['id']:c for c in selected(data,variant)};result={}
    lift=config(data,'service_lift')
    if lift<=0:raise ValueError('query extraction extent must be positive')
    for name,source in QUERY_SOURCES.items():
        c=components[source];lo,hi=bounds(data,c);size=[b-a for a,b in zip(lo,hi)];size[2]+=lift
        refs=list(c['position'])+list(c['size'] if c['kind']=='box' else [c['radius'],c['length']])+[data['config']['service_lift']]
        result[name]={'source':source,'role':'QUERY_NOT_SOLID','kind':'box','lo_m':lo,'size_m':size,'parameter_ids':refs}
    return result
