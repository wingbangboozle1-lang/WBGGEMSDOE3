#!/usr/bin/env python3
"""Session-2026-10-27 diagnostic: session2_repair_family.
Reproduces a recorded result in evidence/session2_*.json using ignored local caches.
Not part of the release path; kept for auditability. No submission slot is used.
"""
import sys,time,json,numpy as np
from pathlib import Path
import rasterio
from scipy import ndimage as ndi
R=Path('/home/user/WBGGEMSDOE3');sys.path.insert(0,str(R/'src'))
from gemsw import sgce,grid as G,uniq2,holdout as H
T=time.time();g=G.load_grid();bins=sgce.load_bins(g);ctx=H.load_holdout_context(R/'data/raw')
cnt=np.load(R/'data/work/dense_cover_count.npy')
geo=sgce.geometry(g.labels,g.foot,15.0);rho,_=sgce.density(bins,g.labels,g.foot,geo)
q=H.quadrant_ids(g.foot);tiles={}
for f in range(4):
 m=q==f;rr=np.flatnonzero(m.any(axis=1));cc=np.flatnonzero(m.any(axis=0))
 tiles[f]=(slice(max(0,int(rr[0])-6),min(g.foot.shape[0],int(rr[-1])+7)),slice(max(0,int(cc[0])-6),min(g.foot.shape[1],int(cc[-1])+7)))
reg=json.load(open(R/'registry/registry_session2.json'))
refs=[(d,e) for d,e in {e['dots_sha256']:e for e in reg['files'] if e['status']=='ok' and 0<e['n_dots']<=1000000}.items()]
rng=np.random.default_rng(11);fi=np.flatnonzero(g.foot.ravel())
def faudit(dots):
 n=int(dots.sum());nu=np.zeros(g.foot.size,bool);nu[rng.choice(fi,n,replace=False)]=True;nu=nu.reshape(g.foot.shape)
 mx=(0,None);mxl=(0,None)
 for d,e in refs:
  ref=uniq2.unpack(np.load(R/'.cache/registry2'/f'{d}.npy'),g.foot.shape)
  near=ndi.binary_dilation(ref,structure=uniq2.DISC);del ref
  obs=float((dots&near).sum())/n;nul=float((nu&near).sum())/n
  if nul>=0.70:
   if obs-nul>mxl[0]:mxl=(obs-nul,e['path'])
  elif obs>mx[0]:mx=(obs,e['path'])
  del near
 return dict(n=n,max_nonlat=mx[0],worst=mx[1],max_lat_excess=mxl[0],passed=bool(mx[0]<=0.70 and mxl[0]<=0.05))
d28p=next((R/'data/ledger').glob('*dotted-h19-5-d2-8-20261002*.tif'))
with rasterio.open(d28p) as ds:a28=ds.read(1)
d28=np.isfinite(a28)&(a28>0)&g.foot
ch={}
for cell in ctx.cells:
 vis=cell.visible_full;dv=ndi.distance_transform_edt(~vis);ch[cell.key]=d28&(dv>sgce.B_PX)&~vis
chev=H.evaluate_hide_and_recover(ch,ctx,name='champion_proxy',n_boot=1000)
def paired(a,b,n_boot=4000,seed=7):
 tpa,fpa,fna,act=a;tpb,fpb,fnb,_=b;rng=np.random.default_rng(seed)
 f=lambda tp,fp,fn:tp.sum()/(tp.sum()+0.2*fp.sum()+0.8*fn.sum()+1e-12)
 d0=f(tpa,fpa,fna)-f(tpb,fpb,fnb);ds=[]
 for _ in range(n_boot):
  i=rng.choice(act,size=len(act),replace=True);ds.append(f(tpa[i],fpa[i],fna[i])-f(tpb[i],fpb[i],fnb[i]))
 return dict(delta=float(d0),ci95=[float(np.quantile(ds,.025)),float(np.quantile(ds,.975))],p_delta_le_0=float(np.mean(np.array(ds)<=0)))
res={}
for k in (5,6):
 avoid=cnt>k;dots=np.zeros(g.foot.shape,bool)
 for f,b in tiles.items():
  r=sgce.place(rho,g.labels,g.foot,geo,n_cap=45000,mu=0.28,max_rounds=12,iters=3,avoid=avoid,region=b);dots|=r['dots']
 a=faudit(dots);print('k',k,'audit',a,'t',round(time.time()-T),flush=True)
 np.save(R/f'data/work/sgce_dots_k{k}.npy',np.packbits(dots.ravel()))
 per={};info=[]
 for cell in ctx.cells:
  vis=cell.visible_full;gc=sgce.geometry(vis,g.foot,15.0);rc,_=sgce.density(bins,vis,g.foot,gc)
  rr=sgce.place(rc,vis,g.foot,gc,n_cap=45000,mu=0.28,max_rounds=12,iters=3,avoid=avoid,region=cell.bbox)
  per[cell.key]=rr['dots'];info.append(dict(cell=cell.key,n=rr['n']))
 ev=H.evaluate_hide_and_recover(per,ctx,name=f'E1_k{k}',n_boot=1000)
 p=paired(ev['_block_totals'],chev['_block_totals'])
 res[k]=dict(audit=a,holdout=dict(dti=ev['pooled_dti'],ci95=ev['ci95_cluster_bootstrap'],n_withheld=ev['n_withheld_positives'],
   evaluator=ev['evaluator_version'],cells=info),champion=chev['pooled_dti'],paired=p,
   promotion=bool(a['passed'] and p['ci95'][0]>0))
 print('k',k,'HOLDOUT',ev['pooled_dti'],'CI',ev['ci95_cluster_bootstrap'],'paired',p,'t',round(time.time()-T),flush=True)
json.dump(res,open(R/'evidence/session2_k56.json','w'),indent=1,default=float)
