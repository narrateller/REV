"""Make coincident interface triangulations before splitting the bodies for contact."""
import numpy as np

import contact as base
import frame_fea as fea
from frame_geometry import Geo, rounded_box


def assembly_geo(trial, level, cut_x_mm, cut_y_mm):
    thickness_mm = trial['thickness_mm']
    travel_mm = trial['travel_mm']
    closed_y_mm = 2.-travel_mm
    rear_mm = thickness_mm+55.
    h, bulk = ((7.5, 30.), (5.8, 27.), (4.6, 24.), (3.6, 24.), (3.0, 24.), (2.6, 24.))[level]
    geo = Geo()
    rounded_box(geo, 0., -18.-(travel_mm-75.)/2, 130., (212.+travel_mm-75.)/2,
                5., 0., thickness_mm, 0., 'blade')
    rounded_box(geo, 0., closed_y_mm, 79., 32.5, 3., -1.,thickness_mm+2.,0.,'window')
    geo.cut('blade',['window'],'blade_cut')
    rounded_box(geo, 0., 0., 170., 90., 12., thickness_mm,55.,0.,'seat')
    rounded_box(geo, 0., 2., 79., 32.5, 3., thickness_mm-1.,57.,0.,'throat')
    geo.cut('seat',['throat'],'seat_cut')
    geo.emit(f'Box(90000) = {{-{cut_x_mm},-{cut_y_mm},{thickness_mm},{2*cut_x_mm},{2*cut_y_mm},205}};')
    rounded_box(geo,0.,0.,170.,90.,12.,thickness_mm-1.,56.,0.,'pocket')
    rounded_box(geo,0.,0.,88.,37.,20.,thickness_mm-1.,207.,0.,'passage')
    geo.cut('90000',['pocket','passage'],'cast_cut')
    geo.emit('assembly[] = BooleanFragments { Volume{blade_cut[],seat_cut[]}; Delete; }'
             ' { Volume{cast_cut[]}; Delete; };')
    geo.lines += base.mesh_settings(h, bulk, 89., f'Min(Abs(z-{thickness_mm}),Abs(z-{rear_mm}))*.85')
    return '\n'.join(geo.lines)+'\n'


def face_keys(faces):
    return {tuple(row) for row in np.sort(faces[:, :3],axis=1)}


def common_faces(faces, opposite):
    return faces[[tuple(key) in opposite for key in np.sort(faces[:,:3],axis=1)]]


def mesh(work, trial, level, cut_x_mm, cut_y_mm, archive):
    from submodel import eased

    thickness_mm=trial['thickness_mm']
    travel_mm=trial['travel_mm']
    z_joint=thickness_mm+55.
    geo=work/'assembly.geo'
    geo.write_text(assembly_geo(trial,level,cut_x_mm,cut_y_mm),encoding='ascii',newline='\n')
    if archive is not None:
        archive.write_bytes(geo.read_bytes())
    fea.run_tool([fea.BIN/'gmsh.exe',geo.name,'-3','-order','2','-format','msh2',
                  '-o','assembly.msh','-nt','1','-nopopup'],work,'Done writing')
    xyz,tets,_,tri=fea.read_mesh(work/'assembly.msh')
    # Components do not overlie one another in the axial direction except for
    # the cast pocket flanks alongside the seat.
    centre=xyz[tets[:,:4]].mean(axis=1)
    seat_outline=base.rounded_distance(centre[:,0],centre[:,1],340.,180.,12.)<0.
    seat_mask=(centre[:,2]>=thickness_mm)&(centre[:,2]<z_joint)&seat_outline
    blade_mask=centre[:,2]<thickness_mm
    body_masks={'blade':blade_mask,'seat':seat_mask,'cast':~(seat_mask|blade_mask)}
    partitions={}
    for name,mask in body_masks.items():
        body=tets[mask]
        verts=np.unique(body)
        active=np.zeros(len(xyz),dtype=bool)
        active[verts]=True
        triangles=tri[active[tri].all(axis=1)]
        front,back={'blade':(0.,thickness_mm),'seat':(thickness_mm,z_joint),
                    'cast':(z_joint,thickness_mm+205.)}[name]
        partitions[name]=(body,verts,triangles,fea.plane_triangles(xyz,triangles,2,front),
                          fea.plane_triangles(xyz,triangles,2,back))
    joints={}
    for first,second,key in (('blade','seat','blade_seat'),('seat','cast','seat_cast')):
        outgoing,incoming=partitions[first][-1],partitions[second][-2]
        shared=common_faces(outgoing,face_keys(incoming))
        if not len(shared):
            raise ValueError('No common triangulation on '+key)
        joints[key]=face_keys(shared)

    parts={}
    n_nodes=n_elements=0
    for name,(body,verts,triangles,front,back) in partitions.items():
        mapping=np.zeros(len(xyz),dtype=int)
        mapping[verts]=np.arange(1,len(verts)+1)
        points=np.vstack((np.zeros((1,3)),xyz[verts]))
        x,y,z=points.T
        local=points.copy()
        if name=='blade':
            d=base.rounded_distance(x,y-(2.-travel_mm),158.,65.,3.)
            edge=-base.rounded_distance(x,y+18.+(travel_mm-75.)/2,260.,212.+travel_mm-75.,5.)
            z -= eased(np.minimum(d,edge),3.,.035)*(z/thickness_mm)**4
            t=np.clip((np.abs(x)-80.)/45.,0.,1.)
            z -= trial['wing_mm']*t*t*(3.-2.*t)*(1.-z/thickness_mm)
            back=common_faces(back,joints['blade_seat'])
            surface_dict={'blade_back':back}
        elif name=='seat':
            local[:,2] -= thickness_mm
            depth=local[:,2]
            d=base.rounded_distance(x,y-2.,158.,65.,3.)
            z += eased(d,trial['runout_length_mm'],trial['runout_depth_mm'])*(1.-depth/55.)**4
            edge=-base.rounded_distance(x,y,340.,180.,12.)
            rear_d=base.rounded_distance(x,y,176.,74.,20.)
            z -= eased(np.minimum(edge,rear_d),3.,.035)*(depth/55.)**4
            front=common_faces(front,joints['blade_seat'])
            back=common_faces(back,joints['seat_cast'])
            surface_dict={'seat_front':front,'seat_back':back}
        else:
            local[:,2] -= thickness_mm
            # Cut the small nominal side clearance after matching the floor mesh.
            # The edges at the loaded floor and outside casting surface stay put.
            distance=base.rounded_distance(x,y,340.,180.,12.)
            step=1.e-3
            ddx=(base.rounded_distance(x+step,y,340.,180.,12.)-distance)/step
            ddy=(base.rounded_distance(x,y+step,340.,180.,12.)-distance)/step
            shift=.10*np.clip(1.-np.maximum(distance,0.)/20.,0.,1.)*np.clip((z_joint-z)/8.,0.,1.)
            x += shift*ddx
            y += shift*ddy
            front=common_faces(front,joints['seat_cast'])
            surface_dict={'cast_pocket':front}
        body=mapping[body]
        active=np.arange(1,len(points))
        surfaces={key:base.surface_rows(body,mapping[faces],n_elements) for key,faces in surface_dict.items()}
        base.write_body(work,name,points,body,active,n_nodes,n_elements)
        parts[name]=dict(xyz=points,local=local,tets=body,active=active,tri=mapping[triangles],
                         front=mapping[front],back=mapping[back],offset=n_nodes,surfaces=surfaces)
        n_nodes+=len(points)
        n_elements+=len(body)
    return parts,n_nodes,n_elements
