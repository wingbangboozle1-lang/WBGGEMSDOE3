#!/usr/bin/env python3
"""Session-2026-10-27 diagnostic: session2_repair_scan.
Reproduces a recorded result in evidence/session2_*.json using ignored local caches.
Not part of the release path; kept for auditability. No submission slot is used.
"""
import sys,time,json,numpy as np
from pathlib import Path
from scipy import ndimage as ndi
R=Path('/home/user/WBGGEMSDOE3');sys.path.insert(0,str(R/'src'))
from gemsw import sgce,grid as G,uniq2,holdout as H
g=G.load_grid();bins=sgce.load_bins(g)
geo=sgce.geometry(g.labels,g.foot,15.0);rho,_=sgce.density(bins,g.labels,g.foot,geo)
cnt=np.load(R/'data/work/dense_cover_count.npy')
q=H.quadrant_ids(g.foot);tiles={}
for f in range(4):
 m=q==f;rr=np.flatnonzero(m.any(axis=1));cc=np.flatnonzero(m.any(axis=0))
 tiles[f]=(slice(max(0,int(rr[0])-6),min(g.foot.shape[0],int(rr[-1])+7)),slice(max(0,int(cc[0])-6),min(g.foot.shape[1],int(cc[-1])+7)))
reg=json.load(open(R/'registry/registry_session2.json'))
refs=[(d,e) for d,e in {e['dots_sha256']:e for e in reg['files'] if e['status']=='ok' and 0<e['n_dots']<=1000000}.items()]
print('refs',len(refs),flush=True)
rng=np.random.default_rng(11);fi=np.flatnonzero(g.foot.ravel())
def faudit(dots,label):
 n=int(dots.sum()); nu=np.zeros(g.foot.size,bool);nu[rng.choice(fi,n,replace=False)]=True;nu=nu.reshape(g.foot.shape)
 worst=(0,None);worstlat=(0,None)
 for d,e in refs:
  ref=uniq2.unpack(np.load(R/'.cache/registry2'/f'{d}.npy'),g.foot.shape)
  near=ndi.binary_dilation(ref,structure=uniq2.DISC)
  del ref
  obs=float((dots&near).sum())/n;nul=float((nu&near).sum())/n
  lat=nul>=0.70
  if lat:
   if obs-nul>worstlat[0]: worstlat=(obs-nul,dict(path=e['path'],obs=obs,nul=nul))
  else:
   if obs>worst[0]: worst=(obs,dict(path=e['path'],obs=obs,nul=nul))
 print(label,'n',n,'max_nonlat',round(worst[0],4),worst[1]['path'][:80] if worst[1] else None,
       'max_lat_excess',round(worstlat[0],4),'PASS',worst[0]<=0.70 and worstlat[0]<=0.05,flush=True)
 return dict(n=n,max_nonlat=worst[0],worst=worst[1],max_lat_excess=worstlat[0],worst_lat=worstlat[1],
             passed=bool(worst[0]<=0.70 and worstlat[0]<=0.05))
res={}
for k in (4,3,2):
 t=time.time();avoid=cnt>k;dots=np.zeros(g.foot.shape,bool)
 for f,bbox in tiles.items():
  r=sgce.place(rho,g.labels,g.foot,geo,n_cap=45000,mu=0.28,max_rounds=12,iters=3,avoid=avoid,region=bbox)
  dots|=r['dots']
 print('built k',k,'n',int(dots.sum()),'t',round(time.time()-t,1),flush=True)
 res[k]=faudit(dots,f'k={k}')
 np.save(R/f'data/work/sgce_dots_k{k}.npy',np.packbits(dots.ravel()))
json.dump(res,open(R/'evidence/session2_threshold_scan.json','w'),indent=1,default=float)
