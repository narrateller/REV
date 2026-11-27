"""Local elastic fatigue screen using the project T-1.7d/T-2.2f coefficients."""

from math import log10

import numpy as np

from solver import mises


def tensor(values):
    x,y,z,xy,yz,zx = np.moveaxis(values,-1,0)
    return np.stack((x,xy,zx,xy,y,yz,zx,yz,z),axis=-1).reshape((*values.shape[:-1],3,3))


def normal_gradient(xyz, tets, triangles, delta):
    vertices = tets[:,:4]
    corners = xyz[vertices]
    jac = corners[:,1:]-corners[:,:1]
    sigma = np.max(np.abs(np.linalg.eigvalsh(tensor(delta))),axis=1)
    slopes = np.linalg.solve(jac,(sigma[vertices[:,1:]]-sigma[vertices[:,:1]])[...,None])[...,0]
    volume = np.abs(np.linalg.det(jac))
    accum,weights = np.zeros_like(xyz),np.zeros(len(xyz))
    for i in range(10):
        np.add.at(accum,tets[:,i],slopes*volume[:,None])
        np.add.at(weights,tets[:,i],volume)
    # Exterior facets only. Use the adjacent corner to orient the normal.
    adj = {}
    for i,tet in enumerate(vertices):
        for j in range(4):
            face = tuple(sorted(np.delete(tet,j)))
            adj[face] = -1 if face in adj else i
    owners = np.array([adj.get(tuple(sorted(face[:3])),-1) for face in triangles])
    surface = triangles[owners>=0]
    points = xyz[surface[:,:3]]
    normal = np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])
    inside = corners[owners[owners>=0]].mean(axis=1)-points.mean(axis=1)
    normal *= np.where(np.einsum("ij,ij->i",normal,inside)>0.,-1.,1.)[:,None]
    by_node = np.zeros_like(xyz)
    for i in range(6):
        np.add.at(by_node,surface[:,i],normal)
    denom = np.linalg.norm(by_node,axis=1)*weights*sigma
    slope = np.einsum("ij,ij->i",by_node,accum)
    return np.clip(np.divide(slope,denom,out=np.zeros(len(xyz)),where=denom>0.),0.,100.)


def margins(proof, start, end, grade, gradient=0.):
    rp02_MPa, rm_MPa, cast = grade
    delta = end-start
    mean = (start+end)/2
    k_R = 1-(.20 if cast else .22)*log10(6.3)*log10(2*rm_MPa/400)
    j_G = 1.25 if cast else 1.
    base_MPa = (.34 if cast else .40)*rm_MPa*k_R*10**(-1/15)/(1.5*j_G)
    M = .00035*rm_MPa+(.05 if cast else -.1)
    aG,bG = (.25,2000.) if cast else (.5,2700.)
    n_sigma = 1 + 10**(-aG-rm_MPa/bG)*np.where(gradient<=.1,np.sqrt(10)*gradient,
                       np.where(gradient<=1,np.sqrt(gradient),np.power(gradient,.25)))
    # The mixed-state screen follows T-1.7d. Tensile principal mean only.
    mean_max_MPa = np.maximum(0.,np.linalg.eigvalsh(tensor(mean))[..., -1])
    equivalent = mises(delta)/2 + M*mean_max_MPa
    vm_MPa = mises(proof)
    return {"static":np.divide(rp02_MPa,vm_MPa,out=np.full_like(vm_MPa,np.inf),where=vm_MPa>0),
            "FKM":np.divide(base_MPa*n_sigma,equivalent,out=np.full_like(equivalent,np.inf),where=equivalent>0),
            "FKM_no_notch_credit":np.divide(base_MPa,equivalent,out=np.full_like(equivalent,np.inf),
                                          where=equivalent>0),
            "n_sigma":n_sigma,"Rz_um":6.3,"j_G":j_G,"component_amplitude_MPa":base_MPa}

