from fx import *
import numpy as np
W,H=7.2,8.3
c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
c.text(W/2,H-0.3,'When does the pattern-only stream (B3) catch up?',11.5,weight='bold',color='#1b1b1b',w=W-0.3)
c.text(W/2,H-0.7,'Two regimes explain all exceptions; everywhere else B2 > B3 > B1',8.8,style='italic',color='#555',w=W-0.3)
pw=W-0.3
def panel(y0,h,fc,ec,title,tcol,sub):
    c.ax.add_patch(FancyBboxPatch((0.15,y0),pw,h,boxstyle='round,pad=0,rounding_size=0.1',fc=fc,ec=ec,lw=1))
    c.text(0.3,y0+h-0.25,title,9.8,weight='bold',color=tcol,ha='left',w=pw-0.3)
    c.text(0.3,y0+h-0.6,sub,8.5,color='#333',ha='left',w=pw-0.3)
# panel 1
y0=H-3.15; panel(y0,2.3,'#e8f2ec','#8fc1a2','Low-prevalence regime','#1e7a3e','RBM10: 37 / 687 mutated slides (5.4%)')
for r in range(3):
    for j in range(10):
        on=(r,j) in [(0,0),(1,1)]
        c.ax.add_patch(Rectangle((0.35+j*0.17,y0+1.35-r*0.17),0.14,0.14,fc='#b0172f' if on else '#d9d9d9',ec='none'))
c.text(2.7,y0+1.5,'few positives -> high-d models overfit',8.5,style='italic',color='#555',ha='left',w=4.3)
c.text(2.7,y0+1.15,'B3 = 0.653 > B2 = 0.642',9.5,weight='bold',color='#1e7a3e',ha='left',w=4.3)
c.ax.add_patch(Rectangle((0.35,y0+0.62),4.0,0.2,fc='#1565c0',ec='none')); c.text(0.4,y0+0.72,'B2: 512-d',8,color='white',weight='bold',ha='left')
c.ax.add_patch(Rectangle((0.35,y0+0.3),0.047*4.0*1.0+0.0,0.2,fc='#2e7d32',ec='none')); c.text(0.65,y0+0.4,'B3: 6-d (~85x smaller: implicit regulariser)',8.5,color='#1e7a3e',ha='left',weight='bold',w=5)
# panel 2
y1=y0-2.5; panel(y1,2.3,'#fbf5e4','#d9c27a','Concentrated-signal regime','#a07d00','EGFR: signal lives in 1-2 patterns (two channels carry most of it)')
vals=[0.9,0.78,0.1,0.14,0.08,0.06]; nm=['lep','pap','micro','acin','crib','sol']
for i,(v,n) in enumerate(zip(vals,nm)):
    c.ax.add_patch(Rectangle((0.4+i*0.42,y1+0.45),0.34,v*0.9,fc='#b8900a' if i<2 else '#cfcfcf',ec='none'))
    c.text(0.57+i*0.42,y1+0.3,n,8,color='#555')
c.text(3.0,y1+1.3,'argmax(p) ~ full p',9,weight='bold',ha='left',color='#333',w=3.9)
c.text(3.0,y1+0.95,'slide-level mean of "% lepidic" suffices',8.5,style='italic',color='#555',ha='left',w=3.9,h=0.6)
c.text(3.0,y1+0.45,'B1 = 0.634 ~ B3 = 0.625\n(B2 = 0.701 still wins on its embedding)',8.8,weight='bold',color='#a07d00',ha='left',w=3.9,h=0.6)
# panel 3
y2=y1-2.2; panel(y2,2.0,'#eef1f9','#9fb1da','Default regime','#1565c0','TP53, STK11, KEAP1, KRAS: signal spread across patterns')
vals=[0.55,0.4,0.62,0.5,0.38,0.58]
for i,(v,n) in enumerate(zip(vals,nm)):
    c.ax.add_patch(Rectangle((0.4+i*0.42,y2+0.45),0.34,v*0.9,fc='#7f96c8',ec='none'))
    c.text(0.57+i*0.42,y2+0.3,n,8,color='#555')
c.text(3.0,y2+1.05,'B2 > B3 > B1',10.5,weight='bold',ha='left',color='#1565c0',w=3.9)
c.text(3.0,y2+0.65,'embedding adds discriminative bits; within-slide attention beats slide means',8.5,style='italic',color='#555',ha='left',w=3.9,h=0.7)
c.text(3.0,y2+0.2,'systematic gap on five of six genes',8.5,color='#333',ha='left',w=3.9)
c.save('../man_out/b3_regimes.png')
