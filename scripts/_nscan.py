import sys, json, numpy as np, rasterio
from pathlib import Path
ROOT=Path('.'); sys.path.insert(0,str(ROOT/'src'))
from gemsw import grid as G, exact as EX
import importlib.util
spec=importlib.util.spec_from_file_location('d','scripts/design_inv.py'); d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
g=G.load_grid(); rho=d.load_rho(Path('data/work'), g.foot.shape)
H,meta=d.build_field(g,rho,{"rho":1.0,"scarp":0.45,"mag_hgrad":0.30,"rad_hgrad":0.20})
picked=d.greedy_select(H,40000,3.0)
champ=rasterio.open('data/work/champion_ref.tif').read(1)>0
c_champ=d.credit_per_dot(rho,champ)
cal=json.load(open('evidence/design_calibration.json'))['calibration']
rows=[]
sup=np.zeros(g.foot.shape,bool)
prev=0
for N in [4000,8000,12000,14000,18000,24000,30000,40000]:
    idx=picked[prev:N]; prev=N
    sup.ravel()[idx]=True
    c=d.credit_per_dot(rho,sup)
    predT=5470.0*c/c_champ
    Tcal=cal['slope']*predT+cal['intercept']
    dti=Tcal/(0.2*int(sup.sum())+0.8*15200.0)
    rows.append(dict(N=int(sup.sum()),credit_per_dot=c,pred_T=predT,T_cal=Tcal,DTI_cal=dti))
    print(f"N={sup.sum():6d} c={c:7.3f} predT={predT:8.0f} Tcal={Tcal:8.0f} DTI_cal={dti:.4f}")
best=max(rows,key=lambda r:r['DTI_cal']); print("BEST",best)
json.dump({"scan":rows,"best":best},open('evidence/design_nscan.json','w'),indent=1)
