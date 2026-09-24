import json, numpy as np, sys
M=json.load(open('work/master_text_pos.json')); AFF=json.load(open('work/aff_live.json'))
tot=0
for c,X in AFF.items():
    X=np.array(X); L=np.array([[X[0,0],X[1,0]],[X[0,1],X[1,1]]]); t=X[2]; Li=np.linalg.inv(L)
    f=f'lk/clusters/{c}_units.json'; d=json.load(open(f)); moved=0
    for k,u in d.items():
        if k not in M: continue
        pos=Li@(np.array(M[k])-t); cur=np.array([u['x'],u['y']])
        if np.linalg.norm(L@(pos-cur))>3:
            u['x'],u['y']=round(float(min(max(pos[0],0),100)),3),round(float(min(max(pos[1],0),100)),3); moved+=1
    json.dump(d,open(f,'w'),ensure_ascii=False,separators=(',',':')); tot+=moved
    print(f"{c:11s} snapped {moved:4d} of {len(d)}")
print("total",tot)
