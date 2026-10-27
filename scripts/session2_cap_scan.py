#!/usr/bin/env python3
"""Session-2026-10-27 diagnostic: session2_cap_scan.
Reproduces a recorded result in evidence/session2_*.json using ignored local caches.
Not part of the release path; kept for auditability. No submission slot is used.
"""
import sys,json,numpy as np, hashlib
from pathlib import Path
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
R=Path('/home/user/WBGGEMSDOE3');sys.path.insert(0,str(R/'src'));sys.path.insert(0,str(R/'scripts'))
import session2_projection as P
from gemsw import sgce,grid as G,uniq2
g=G.load_grid();bins=sgce.load_bins(g)
reg=json.loads((R/'registry/registry_session2.json').read_text())
by_sha={e['sha256']:e['dots_sha256'] for e in reg['files'] if e['status']=='ok'}
ledger=json.loads((R/'data/ledger/index.json').read_text())
chp=next((R/'data/ledger').glob('*h33-h33-2-b2*.tif'));d28p=next((R/'data/ledger').glob('*dotted-h19-5-d2-8-20261002*.tif'))
with rasterio.open(chp) as ds:a=ds.read(1)
ch=np.isfinite(a)&(a>0)&g.foot
with rasterio.open(d28p) as ds:a=ds.read(1)
d28=np.isfinite(a)&(a>0)&g.foot
near_ch=ndi.binary_dilation(ch,structure=uniq2.DISC);near_d28=ndi.binary_dilation(d28,structure=uniq2.DISC)
d_cat=ndi.distance_transform_edt(~g.labels).astype(np.float32)
X=[];y=[];groups=[]
for r in ledger:
 s=r.get('score');dsha=by_sha.get(r['sha256'])
 if not(isinstance(s,(int,float)) and s>0 and dsha and (P.CACHE/f'{dsha}.npy').exists()):continue
 f=P.descriptors(P.load_dots(dsha,g.foot.shape),g,near_ch,near_d28,d_cat,bins)
 if f is None:continue
 X.append(f);y.append(float(s));groups.append(r['site'])
X=np.asarray(X);y=np.asarray(y);sc=StandardScaler().fit(X)
m=RandomForestRegressor(n_estimators=200,min_samples_leaf=2,random_state=7,n_jobs=2).fit(sc.transform(X),y)
# rho and full dots
cnt=np.load(R/'data/work/dense_cover_count.npy')
geo=sgce.geometry(g.labels,g.foot,15.0);rho,_=sgce.density(bins,g.labels,g.foot,geo);rho[cnt>6]=0
full=uniq2.unpack(np.load(R/'data/work/session2_dots_packed.npy'),g.foot.shape)
ys,xs=np.nonzero(full);vals=rho[ys,xs];order=np.argsort(-vals)
print('full',int(full.sum()),'projection',m.predict(sc.transform(P.descriptors(full,g,near_ch,near_d28,d_cat,bins)[None,:]))[0])
for K in (80000,60000,50000,45000,40000,37654,30000):
 d=np.zeros(g.foot.shape,bool);d[ys[order[:K]],xs[order[:K]]]=True
 f=P.descriptors(d,g,near_ch,near_d28,d_cat,bins)
 print(K,'proj',round(float(m.predict(sc.transform(f[None,:]))[0]),4),'overlap_ch',round(f[1],3),'blockcov',round(f[5],3))
 np.save(R/f'data/work/sgce_cap{K}.npy',np.packbits(d.ravel()))
