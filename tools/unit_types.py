import json,pickle,collections,numpy as np,sys
from PIL import Image
from skimage.color import rgb2lab
Image.MAX_IMAGE_PIXELS=None
ps,s2=pickle.load(open('work/ps_s2.pkl','rb'))
CREAM=[(245,243,202),(244,243,176),(247,243,181),(248,243,181),(240,238,173),(248,242,166),(244,241,201),(242,239,172)]
PINK=[(234,187,233),(241,188,241),(237,186,237),(235,189,233)]
M=(130,185); E=(195,280)
# type: (beds, plotrange, [palette])
SPEC={
'costabrava':{'LTH-4B-M':(4,(130,165),[(248,245,134),(163,170,103)]),'LTH-3B-M':(3,(130,165),[(135,177,183)]),
  'LTH-5B-EM':(5,(166,260),[(94,92,117),(153,136,170)]),'LTH-5B-E':(5,(166,260),[(218,106,106)]),
  'LV-3B':(5,(380,520),[(153,136,170)]),'LVD-1B':(7,(600,2000),[(234,131,234)])},
'portofino':{'BL-3-M':(3,(130,165),[(101,219,251),(156,184,192)]),'BL-4-M':(4,(130,165),[(248,220,192),(246,197,150),(190,173,145)]),
  'BL-5-E':(5,(190,300),[(165,4,219),(102,105,116),(143,63,177)]),'BL-VD1':(7,(550,850),[(252,166,91)]),'BL-V75':(7,(851,4000),[(249,175,231)])},
'santorini':{'LTH-4A-M':(4,(130,165),[(246,243,189),(212,209,176)]),'LTH-3A-M':(3,(130,165),[(95,170,171)]),'LTH-5A-M':(5,(130,165),[(235,179,186)]),
  'LTH-5A-E':(5,(190,280),[(232,225,60),(202,199,89)]),'LV3':(6,(380,480),[(188,122,175)]),'LV4':(6,(380,480),[(205,190,168)])},
'nice':{'LTH-4C-M':(4,(130,165),[(232,213,163),(201,189,159),(237,222,194)]),'LTH-5C-M':(5,(130,165),[(210,235,201)]),
  'LTH-5C-E':(5,(190,280),[(240,248,164),(249,242,193)]),'LV-3C':(6,(380,520),[(245,194,235)])},
'venice':{'LV-1000E':(6,(900,4000),[(239,187,237)]),'LV-75E':(7,(900,4000),[(191,236,239)]),'LV-55E':(6,(600,900),[(241,246,189)]),
  'LVD-1E':(7,(600,900),[(202,222,192)]),'LV-3E':(6,(400,650),[(225,173,174)]),'LV-4E':(6,(400,650),[(238,216,118)])},
'malta':{'LTH-4D-M':(4,M,CREAM),'LTH-5D-E':(5,E,PINK),'LVD-1D':(7,(560,900),[(217,113,26)])},
'marbella':{'LTH-4F-M':(4,M,CREAM),'LTH-5F-E':(5,E,PINK)},
'montecarlo':{'LTH-4G-M':(4,M,CREAM),'LTH-5G-E':(5,E,PINK)},
'mykonos':{'LTH-4J-M':(4,M,CREAM),'LTH-5J-E':(5,E,PINK)},
'ibiza':{'LTH-4H-M':(4,M,CREAM),'LTH-5H-E':(5,E,PINK)},
'morocco':{'LTH-4K-M':(4,(130,185),[(246,196,147),(148,131,76)]),'LTH-5K-E':(5,(195,280),[(166,1,222),(145,18,187),(109,15,141)]),
  'LV-55K':(6,(600,900),[(218,114,20)]),'LV-75K':(7,(900,1300),[(171,221,246)]),'LV-1000K':(6,(1301,4000),[(222,178,211)])},
}
def mask(px):
    px=px.astype(float); mx=px.max(1); mn=px.min(1); sat=(mx-mn)/np.maximum(mx,1)
    grass=(px[:,1]>px[:,0]+8)&(px[:,1]>px[:,2]+8)&(mx<170)
    return (mx>90)&(sat>0.12)&~grass
def classify(c,win=12,tol=14,minv=6):
    spec=SPEC[c]; codes=list(spec)
    pal=[(t,rgb) for t in codes for rgb in spec[t][2]]
    PL=rgb2lab(np.array([p[1] for p in pal],float)[:,None,:]/255.).reshape(-1,3)
    im=np.array(Image.open(f'lk/clusters/{c}.jpg').convert('RGB')); H,W,_=im.shape
    d=json.load(open(f'lk/clusters/{c}_units.json')); out={}
    for q,u in d.items():
        x=int(u['x']/100*W); y=int(u['y']/100*H)
        w=im[max(0,y-win):y+win+1,max(0,x-win):x+win+1].reshape(-1,3); w=w[mask(w)]
        votes=collections.Counter()
        if len(w)>=minv:
            l=rgb2lab(w[:,None,:]/255.).reshape(-1,3); dist=np.linalg.norm(l[:,None,:]-PL[None],axis=2)
            j=dist.argmin(1); ok=dist.min(1)<tol
            for jj in j[ok]: votes[pal[jj][0]]+=1
        plot=ps.get(q); beds=s2.get(q,{}).get('beds')
        cand=codes
        if plot is not None:
            pc=[t for t in codes if spec[t][1][0]<=plot<=spec[t][1][1]]
            if pc: cand=pc
        how=None
        if isinstance(beds,int):
            bc=[t for t in cand if spec[t][0]==beds]
            if bc: cand=bc; how='s2'
        if len(cand)==1: t=cand[0]; how=how or 'plot'
        else:
            v={t:votes[t] for t in cand if votes[t]>0}
            if v and sum(v.values())>=minv: t=max(v,key=v.get); how='colour'
            else: t=None
        out[q]=(t,how,plot,beds)
    return out
if __name__=='__main__':
    c=sys.argv[1]; o=classify(c); spec=SPEC[c]
    cnt=collections.Counter(v[0] for v in o.values()); print(c,len(o),dict(cnt),collections.Counter(v[1] for v in o.values()))
    bad=[(q,v) for q,v in o.items() if isinstance(v[3],int) and v[0] and spec[v[0]][0]!=v[3]]
    print(' s2 beds conflicts',len(bad),bad[:5])
    print(' none with no plot:',sum(1 for v in o.values() if v[0] is None and v[2] is None),' none with plot:',sum(1 for v in o.values() if v[0] is None and v[2] is not None))
