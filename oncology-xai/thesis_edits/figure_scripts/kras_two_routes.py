from fx import *
c=Canvas(7.2,8.6,minpt=8.0)
W,H=7.2,8.6
c.text(W/2,H-0.30,'Why B3 (patterns only + additive head)\ncollapses to chance on KRAS',11.5,weight='bold',color='#1b1b1b')
c.text(W/2,H-0.85,'Two routes from KRAS morphology to the classifier: both must be\nclosed for B3 to fail, and both are.',9,style='italic',color='#555')
c.box(1.9,H-1.95,3.4,0.75,'KRAS-driven morphology:\ninvasive mucinous adenocarcinoma (IMA)',9,fc='#fff6d6',ec='#b8921a',weight='bold')
LX,RX,CW=0.15,3.75,3.3
c.arrow(3.2,H-1.95,LX+CW/2,H-2.55); c.arrow(4.0,H-1.95,RX+CW/2,H-2.55)
c.text(LX+CW/2-0.55,H-2.17,'Route 1: direct',9,weight='bold',color='#1f3a5f')
c.text(RX+CW/2+0.45,H-2.12,'Route 2: indirect\n(joint reading)',9,weight='bold',color='#1f3a5f')
c.box(LX,H-3.55,CW,0.95,'A dedicated "mucinous" channel in the 6-d pattern vector',9,fc='#fbeceb',ec='#c0392b')
c.box(RX,H-3.55,CW,0.95,'A joint reading of two channels: lepidic AND solid on the same slide',9,fc='#eaf5ec',ec='#1f3a5f')
names=['lepidic','papillary','micropap.','acinar','cribriform','solid']
def chips(x0,y0,hi):
    cw=1.02
    for i,n in enumerate(names):
        r,cidx=divmod(i,3)
        on=n in hi
        c.box(x0+cidx*(cw+0.07),y0-r*0.5,cw,0.4,n,8.5,fc='#ffdf80' if on else '#e8f0f9',ec='#b8921a' if on else '#1f3a5f',weight='bold' if on else 'normal',round=0.05)
c.text(LX+CW/2,H-3.85,'ANORAK output (6-d vector)',8.5,color='#333')
chips(LX,H-4.35,[])
c.text(LX+CW/2,H-5.0,'No "mucinous" slot in this vector',9,weight='bold',color='#c0392b',w=CW)
c.text(LX+CW/2,H-5.45,'ANORAK has 6 classes; IMA is not one of them (see Section 3.2)',8.5,style='italic',color='#555',w=CW,h=0.6)
c.box(LX+0.9,H-7.4,1.5,0.42,'CLOSED',9.5,fc='#c0392b',ec='#c0392b',tc='white',weight='bold')
c.text(RX+CW/2,H-3.85,'Do lepidic and solid fire together?',8.5,color='#8a6d0b',weight='bold',w=CW,h=0.4)
chips(RX,H-4.35,['lepidic','solid'])
c.box(RX,H-5.85,CW,0.8,'ABMIL + linear head (B3, PI-ABMIL) adds channels independently: cannot ask AND',8.5,fc='#fbeceb',ec='#c0392b')
c.box(RX,H-6.75,CW,0.8,'FC-MIL (Choquet) aggregates jointly over the 6-d vector and learns $I_{lep,sol}$ = +0.032',8.5,fc='#e6f3e8',ec='#2a8a4a')
c.box(RX+CW-1.0,H-5.65-0.3,0.0001,0.0001,'',8) if False else None
c.box(RX+CW/2-0.75,H-7.15,1.5,0.4,'CLOSED  /  OPEN',9,fc='#888',ec='#888',tc='white',weight='bold') if False else None
c.box(RX,H-7.4,1.5,0.42,'B3: CLOSED',9,fc='#c0392b',ec='#c0392b',tc='white',weight='bold')
c.box(RX+1.8,H-7.4,1.5,0.42,'FC-MIL: OPEN',9,fc='#2a8a4a',ec='#2a8a4a',tc='white',weight='bold')
c.ax.add_patch(FancyBboxPatch((0.15,0.1),W-0.3,1.0,boxstyle='round,pad=0,rounding_size=0.08',fc='#f8f8f8',ec='#bbb'))
c.text(W/2,0.95,'KRAS (5-fold CV, mean AUROC, Table 6.5)',9,weight='bold',color='#222')
items=[('B3 (patterns only)','AUROC = 0.545','#c0392b','both routes closed'),('PI-ABMIL','AUROC = 0.590','#c0392b','Route 2 still closed'),('B2 (embedding only)','AUROC = 0.607','#1f3a5f','picks up signal'),('FC-MIL','AUROC = 0.609','#2a8a4a','Route 2 opens')]
for i,(a,b,col,d) in enumerate(items):
    x=0.15+i*1.78+0.9
    c.text(x,0.72,a,8,w=1.7,color='#333'); c.text(x,0.5,b,9,weight='bold',color=col,w=1.7); c.text(x,0.27,d,8,style='italic',color='#555',w=1.7)
c.save('../man_out/kras_two_routes.png')
