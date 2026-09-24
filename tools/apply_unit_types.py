import importlib.util,collections,json,statistics,re
spec=importlib.util.spec_from_file_location('ttypes','work/types.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
LK='lk/'
BUA_OVERRIDE={('venice','LV-75E'):1634.3,('venice','LV-4E'):377.8,('venice','LV-1000E'):2299.5,('venice','LV-55E'):1021.1,('venice','LVD-1E'):991.5,('venice','LV-3E'):424.8}
BUA_DROP={('nice','LTH-5C-E'),('montecarlo','LTH-5G-E'),('mykonos','LTH-5J-E')}   # S2 'built' == plot size / out of family, unreliable
LABEL={'M':'Middle unit','E':'End unit','EM':'End-middle unit'}
def label(c,code,beds):
    v=re.match(r'^(LV|LVD|BL-V)',code) is not None
    if v: return f'{beds}-bedroom villa'
    suf=code.split('-')[-1]
    return f'{beds}-bedroom townhouse · {LABEL.get(suf,"")}'.strip(' ·')
root=json.load(open(LK+'units.json')); types={}
rep=[]
for c in m.SPEC:
    a=m.classify(c); b=m.classify(c,win=22,tol=20,minv=4)
    for q,v in a.items():
        if v[0] is None and b[q][0] is not None: a[q]=(b[q][0],'colour~',v[2],v[3])
    spec=m.SPEC[c]
    bua={}; ptyp={}
    by=collections.defaultdict(list); pl=collections.defaultdict(list)
    for q,(t,how,plot,beds) in a.items():
        if not t: continue
        s=m.s2.get(q)
        if s and s.get('built'): by[t].append(round(s['built'],1))
        if plot: pl[t].append(plot)
    for t in spec:
        if (c,t) in BUA_OVERRIDE: bua[t]=BUA_OVERRIDE[(c,t)]
        elif (c,t) in BUA_DROP: bua[t]=None
        elif by[t]:
            mc=collections.Counter(by[t]).most_common(1)[0]
            bua[t]=mc[0] if mc[1]>=2 else None
        else: bua[t]=None
        ptyp[t]=None
        if len(pl[t])>=5:
            q10,q90=sorted(pl[t])[len(pl[t])//10],sorted(pl[t])[-1-len(pl[t])//10]; med=statistics.median(pl[t])
            if q10>=med*0.94 and q90<=med*1.06: ptyp[t]=round(med)   # only fill a 'typical' plot where the type's plot size barely varies
    types[c]={t:{'l':label(c,t,spec[t][0]),'b':spec[t][0],'ba':bua[t],'pt':ptyp[t],'img':f'floorplans/{c}/{t}.jpg'} for t in spec}
    d=json.load(open(f'{LK}clusters/{c}_units.json'))
    n=collections.Counter()
    for q,u in d.items():
        t,how,plot,beds=a[q]
        for k in ('t','b','ps','pa','ba','ts'): u.pop(k,None)
        if plot: u['ps']=round(plot,1)
        if t:
            u['t']=t; u['b']=spec[t][0]; u['ts']=how
            if bua[t]: u['ba']=bua[t]
            if not plot and ptyp[t]: u['ps']=ptyp[t]; u['pa']=1
        elif isinstance(beds,int): u['b']=beds
        n[how]+=1
        if q in root:
            for k in ('t','b','ps','pa','ba','ts'):
                root[q].pop(k,None)
                if k in u: root[q][k]=u[k]
    json.dump(d,open(f'{LK}clusters/{c}_units.json','w'),ensure_ascii=False,separators=(',',':'))
    rep.append((c,len(d),dict(n),sum(1 for u in d.values() if 'ps' in u),sum(1 for u in d.values() if 'ba' in u)))
json.dump(root,open(LK+'units.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(types,open(LK+'floorplans/types.json','w'),indent=1,ensure_ascii=False)
for r in rep: print(r)
