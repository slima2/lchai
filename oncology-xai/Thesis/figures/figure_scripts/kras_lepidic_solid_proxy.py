from fx import *
import numpy as np
from matplotlib.patches import Ellipse, Polygon
W,H=7.2,9.1
c=Canvas(W,H,minpt=8.0)
c.text(W/2,H-0.3,'Why the model learns $I_{lepidic,solid}$ = +0.032 for KRAS',11.5,weight='bold',color='#1b1b1b',w=W-0.3)
c.text(W/2,H-0.78,'A KRAS-driven mucinous tumour has three components,\nbut ANORAK only labels two of them.',9,style='italic',color='#555')
# reality panel
c.ax.add_patch(FancyBboxPatch((0.15,H-4.55),W-0.3,3.45,boxstyle='round,pad=0,rounding_size=0.1',fc='#faf7f0',ec='#bbb'))
c.text(W/2,H-1.3,'REALITY: a KRAS-mutant IMA slide (three observable components)',9.5,weight='bold',color='#1f3a5f',w=W-0.5)
colw=(W-0.3)/3
cols=[('(1) Surface-growing layer along alveoli','tumour cells creep along existing lung surfaces','lepidic','#e0a50c'),
      ('(2) Dense sheet-like masses','tumour piles up into solid blocks','solid','#7e46b4'),
      ('(3) Mucus content (cellular, not architectural)','the defining feature of mucinous tumours','no ANORAK channel','#c0392b')]
for i,(h,sub,tag,col) in enumerate(cols):
    x0=0.15+i*colw; cx=x0+colw/2
    c.text(cx,H-1.95,h,9,weight='bold',w=colw-0.15,h=0.75,color='#222')
    c.text(cx,H-2.55,sub,8.5,style='italic',color='#555',w=colw-0.15,h=0.55)
    yb=H-3.3
    if i==0:
        xs=np.linspace(x0+0.2,x0+colw-0.2,200); c.ax.plot(xs,yb+0.12*np.sin((xs-x0)*6),color='#999',lw=1)
        for xx in np.linspace(x0+0.3,x0+colw-0.3,9): c.ax.add_patch(Ellipse((xx,yb+0.12*np.sin((xx-x0)*6)+0.14),0.09,0.12,fc=col,ec='none'))
    if i==1:
        px=np.linspace(x0+0.25,x0+colw-0.25,8); py=yb-0.15+np.array([0.25,0.1,0.1,0.3,0.1,0.05,0.12,0.28])
        c.ax.add_patch(Polygon([(px[0],yb-0.15)]+list(zip(px,py))+[(px[-1],yb-0.15)],fc=col,ec='none',alpha=.9))
    if i==2:
        for ex in (x0+0.55,x0+colw-0.55): c.ax.add_patch(Ellipse((ex,yb),0.7,0.38,fc='#9fd4cc',ec='#6bb',lw=.8))
        rng=np.random.RandomState(3)
        for _ in range(26):
            ex=rng.choice([x0+0.55,x0+colw-0.55]); c.ax.add_patch(Ellipse((ex+rng.randn()*0.15,yb+rng.randn()*0.08),0.04,0.05,fc='#2a9d8f',ec='none'))
    c.text(cx,H-3.85,'-> '+tag if i<2 else tag,8.5,weight='bold',color=col,w=colw-0.15)
c.text(W/2,H-4.2,'Two components are architectural (lepidic, solid); one is cellular (mucus).',8.5,color='#333',w=W-0.6)
c.arrow(W/2,H-4.6,W/2,H-5.15,lw=1.8)
c.text(W/2+0.1,H-4.88,'ANORAK projection\n(layout-only, no mucinous slot)',8.5,weight='bold',color='#1f3a5f',ha='left',w=4.6,h=0.7)
# model panel
c.ax.add_patch(FancyBboxPatch((0.15,H-8.15),W-0.3,2.95,boxstyle='round,pad=0,rounding_size=0.1',fc='#f3f6fa',ec='#bbb'))
c.text(W/2,H-5.4,'WHAT THE MODEL SEES: 6-d ANORAK vector',9.5,weight='bold',color='#1f3a5f',w=W-0.5)
names=['lepidic','papillary','micropapillary','acinar','cribriform','solid','[ missing ]']
vals=[0.62,0.05,0.06,0.09,0.04,0.55,None]
for i,(n,v) in enumerate(zip(names,vals)):
    y=H-5.85-i*0.31
    on=n in('lepidic','solid')
    c.text(0.4,y,n,8.5,ha='left',weight='bold' if on else 'normal',color='#222' if on else '#777',w=1.5)
    c.ax.add_patch(Rectangle((2.1,y-0.1),4.6,0.2,fc='white',ec='#bbb',lw=.8,ls='--' if v is None else '-',**({'edgecolor':'#c0392b'} if v is None else {})))
    if v: c.ax.add_patch(Rectangle((2.1,y-0.1),4.6*v,0.2,fc='#e0a50c' if n=='lepidic' else ('#7e46b4' if n=='solid' else '#ddd'),ec='none'))
    if v is None: c.text(2.2+0.1,y,'no mucinous channel',8.5,ha='left',weight='bold',color='#c0392b',w=3)
c.text(W/2,H-8.3-0.0,' ',8)
c.box(0.15,0.08,W-0.3,0.85,'FC-MIL learns $I_{lepidic,solid}$ = +0.032: lepidic and solid co-presence acts as a learned PROXY for "mucinous, KRAS-like tumour", the channel the ontology does not provide.',8.8,fc='#fff6d6',ec='#b8921a',tc='#6b5200')
c.save('../man_out/kras_lepidic_solid_proxy.png')
