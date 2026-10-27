#!/usr/bin/env python3
"""Session-2026-10-27 diagnostic: session2_holdout_k4.
Reproduces a recorded result in evidence/session2_*.json using ignored local caches.
Not part of the release path; kept for auditability. No submission slot is used.
"""
import sys,time,json,numpy as np
from pathlib import Path
import rasterio
from scipy import ndimage as ndi
R=Path('/home/user/WBGGEMSDOE3');sys.path.insert(0,str(R/'src'))
from gemsw import sgce,grid as G,holdout as H
T=time.time();g=G.load_grid();bins=sgce.load_bins(g);ctx=H.load_holdout_context(R/'data/raw')
avoid=np.load(R/'data/work/dense_cover_count.npy')>4
d28p=next((R/'data/ledger').glob('*dotted-h19-5-d2-8-20261002*.tif'))
with rasterio.open(d28p) as ds: a28=ds.read(1)
d28=np.isfinite(a28)&(a28>0)&g.foot
ch={}
for cell in ctx.cells:
 vis=cell.visible_full;dv=ndi.distance_transform_edt(~vis)
 ch[cell.key]=d28&(dv>sgce.B_PX)&~vis
chev=H.evaluate_hide_and_recover(ch,ctx,name='champion_proxy',n_boot=1000)
print('champion',chev['pooled_dti'],'t',round(time.time()-T),flush=True)
per={};info=[]
for cell in ctx.cells:
 vis=cell.visible_full
 geo=sgce.geometry(vis,g.foot,15.0);rho,_=sgce.density(bins,vis,g.foot,geo)
 r=sgce.place(rho,vis,g.foot,geo,n_cap=45000,mu=0.28,max_rounds=12,iters=3,avoid=avoid,region=cell.bbox)
 per[cell.key]=r['dots'];info.append(dict(cell=cell.key,n=r['n']))
 print(' ',cell.key,r['n'],round(time.time()-T),flush=True)
ev=H.evaluate_hide_and_recover(per,ctx,name='E1_softrepair',n_boot=1000)
def paired(a,b,n_boot=4000,seed=7):
 tpa,fpa,fna,act=a;tpb,fpb,fnb,_=b;rng=np.random.default_rng(seed)
 f=lambda tp,fp,fn:tp.sum()/(tp.sum()+0.2*fp.sum()+0.8*fn.sum()+1e-12)
 d0=f(tpa,fpa,fna)-f(tpb,fpb,fnb);ds=[]
 for _ in range(n_boot):
  i=rng.choice(act,size=len(act),replace=True);ds.append(f(tpa[i],fpa[i],fna[i])-f(tpb[i],fpb[i],fnb[i]))
 return dict(delta=float(d0),ci95=[float(np.quantile(ds,.025)),float(np.quantile(ds,.975))],p_delta_le_0=float(np.mean(np.array(ds)<=0)))
p=paired(ev['_block_totals'],chev['_block_totals'])
out=dict(evidence_class='HOLDOUT-DTI on the soft-repaired unique construction (k=4)',
 evaluator=ev['evaluator_version'],n_withheld=ev['n_withheld_positives'],n_clusters=ev['n_spatial_clusters'],
 candidate=dict(pooled_dti=ev['pooled_dti'],ci95=ev['ci95_cluster_bootstrap'],per_quadrant=ev['per_quadrant_dti'],cells=info),
 champion_proxy=dict(pooled_dti=chev['pooled_dti'],ci95=chev['ci95_cluster_bootstrap']),
 paired_delta_vs_champion_proxy=p,promotion_rule_passed=bool(p['ci95'][0]>0),
 avoid_zone_px=int((~avoid&g.foot).sum()),n_release_dots=99488)
json.dump(out,open(R/'evidence/session2_holdout_k4.json','w'),indent=1,default=float)
print('RESULT',out['candidate']['pooled_dti'],out['candidate']['ci95'],'champion',out['champion_proxy']['pooled_dti'],'paired',p,flush=True)
