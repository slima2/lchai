import re,subprocess,sys,os,csv,io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
Image.MAX_IMAGE_PIXELS=None
FIG='fullc/chapters/figures/'
uses={}
for ch in sorted(os.listdir('fullc/chapters')):
    if not ch.endswith('.tex'):continue
    t=open('fullc/chapters/'+ch,encoding='utf-8').read()
    for m in re.finditer(r'\\includegraphics\[width=([\d.]*)\\textwidth(?:,height=([\d.]+)in,keepaspectratio)?\]\{chapters/figures/([^}]+)\}',t):
        w=float(m.group(1) or 1); hh=float(m.group(2)) if m.group(2) else None
        uses.setdefault(m.group(3),[]).append((ch[:4],w,hh))
def run(fn):
    p=FIG+fn
    if not os.path.exists(p): return fn,None
    im=Image.open(p).convert('RGB'); W,H=im.size
    tmp=f'audit/{fn}.png'; im.save(tmp)
    r=subprocess.run(['tesseract',tmp,'-','--psm','11','tsv'],capture_output=True,text=True).stdout
    hs=[]
    for row in csv.DictReader(io.StringIO(r),delimiter='\t',quoting=csv.QUOTE_NONE):
        try:
            if float(row['conf'])>70 and len(row['text'])>=3 and re.search('[a-z]',row['text']): hs.append(int(row['height']))
        except: pass
    os.remove(tmp)
    return fn,(W,H,hs)
with ThreadPoolExecutor(6) as ex: res=list(ex.map(run,uses))
out=[]
for fn,r in res:
    if not r: continue
    W,H,hs=r
    w=uses[fn][0][1]*6.1
    hh=uses[fn][0][2]
    if hh: w=min(w,hh*W/H)
    if len(hs)<4: out.append((fn,None,len(hs),w));continue
    hs.sort(); q=hs[len(hs)//4]; med=hs[len(hs)//2]
    k=w/W*72/0.80
    out.append((fn,round(q*k,1),len(hs),round(med*k,1)))
for o in sorted(out,key=lambda x:(x[1] is None,x[1] or 0)): print(o)
