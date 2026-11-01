from fx import *
import numpy as np
from PIL import Image
OUT='../man_out/'
def who():
    im=np.array(Image.open('../src/who_orig.png').convert('RGB'))
    xs=[(0,283),(285,567),(568,850),(852,1133),(1135,1418),(1420,1700)]
    names=['Lepidic','Acinar','Papillary','Micropapillary','Solid','Cribriform']
    W,H=7.2,5.55; c=Canvas(W,H,minpt=8.0)
    tw=2.2; gx=0.2; th=2.2
    for i,(n,(a,b)) in enumerate(zip(names,xs)):
        r,col=divmod(i,3); x=0.1+col*(tw+gx); y=H-0.45-th-r*(th+0.55)
        ax=c.fig.add_axes([x/W,y/H,tw/W,th/H]); ax.imshow(im[22:299,a:b],aspect='auto'); ax.axis('off')
        c.text(x+tw/2,y+th+0.2,n,10,weight='bold')
    c.save(OUT+'who_luad_patterns.png'); print(audit(c.fig))
def he():
    im=np.array(Image.open('../src/he_orig.png').convert('RGB'))
    crops=[(10,378),(450,711),(893,1237),(1322,1671)]
    titles=['Step 1: Tissue fixation\nin formaldehyde','Step 2: H&E staining\nof tissue sections','Step 3: Whole-slide\nscanning (Ventana)','Step 4: Digital image\ncorrection (if needed)']
    W,H=7.2,6.85; c=Canvas(W,H,minpt=8.0)
    ph=2.45; cellw=3.4
    pos=[]
    for i,((a,b),t) in enumerate(zip(crops,titles)):
        r,col=divmod(i,2); w=ph*(b-a)/(444-70)
        cx=0.1+col*(cellw+0.3)+cellw/2; x=cx-w/2; y=H-0.75-ph-r*(ph+0.95)
        ax=c.fig.add_axes([x/W,y/H,w/W,ph/H]); ax.imshow(im[70:444,a:b],aspect='auto'); ax.axis('off')
        c.text(cx,y+ph+0.28,t,9.5,weight='bold',w=cellw,h=0.5)
        pos.append((x,y,w))
    # arrows 1->2 and 3->4 (horizontal), 2->3 (bent)
    for i in (0,2):
        x,y,w=pos[i]; x2=pos[i+1][0]
        c.arrow(x+w+0.08,y+ph/2,x2-0.08,y+ph/2,'#444',2.0)
    c.save(OUT+'he_workflow_solca.png'); print(audit(c.fig))
who(); he()
