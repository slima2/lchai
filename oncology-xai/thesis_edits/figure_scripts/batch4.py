from fx import *
import numpy as np
from matplotlib.patches import Arc
OUT='../man_out/'
def regimes():
    W,H=7.2,9.6; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,H-0.3,'When does the Choquet branch (FC-MIL) help, hurt, or stay neutral?',10.8,weight='bold',w=W-0.3)
    c.text(W/2,H-0.75,'Three regimes across the six target genes, aligned with the structural taxonomy of Finding 2.',8.5,style='italic',color='#555',w=W-0.3)
    pw=W-0.3
    def panel(y0,h,fc,ec,title,tc,sub):
        c.ax.add_patch(FancyBboxPatch((0.15,y0),pw,h,boxstyle='round,pad=0,rounding_size=0.1',fc=fc,ec=ec,lw=1.2))
        c.text(0.3,y0+h-0.25,title,9.8,weight='bold',color=tc,ha='left',w=pw-0.3)
        c.text(0.3,y0+h-0.58,sub,8.5,style='italic',color='#444',ha='left',w=pw-0.3)
    pats=['lep','pap','mic','aci','cri','sol']
    # C
    y=H-3.45; panel(y,2.55,'#e6f5ec','#2e9e5b','Constructive (regime C): KRAS','#1e7a3e','Cross-term in label space')
    xs=[0.5+i*0.62 for i in range(6)]; by=y+1.0
    for i,(x,p) in enumerate(zip(xs,pats)):
        c.ax.plot(x,by,'o',ms=P(8 if p in('lep','sol','aci') else 5),color='#2e9e5b' if p in('lep','sol','aci') else '#999'); c.text(x,by-0.22,p,8,color='#333')
    for (a_,b_,h) in [(0,5,0.65),(3,5,0.35)]:
        c.ax.add_patch(Arc(((xs[a_]+xs[b_])/2,by),xs[b_]-xs[a_],2*h,theta1=0,theta2=180,color='#2e9e5b',lw=P(1.8)))
    c.text(5.5,y+1.3,'Choquet captures a stable cross-term: $I_{lep\\times sol}$ = +0.032 and $I_{aci\\times sol}$ = +0.025 (lepidic x solid IMA proxy; Finding 2/4).',8.5,color='#333',w=3.0,h=1.5)
    c.box(0.3,y+0.08,pw-0.3,0.42,'FC-MIL > B2: KRAS $\\Delta$AUROC = +0.002, $\\Delta\\sigma$ = $-$0.019 (stable across folds)',8.3,fc='white',ec='#2e9e5b',tc='#1e7a3e',weight='bold')
    # B
    y2=y-3.25; panel(y2,3.05,'#fdf1e1','#e08a1e','Engaged but unproductive (regime B): STK11, KEAP1, RBM10','#b45f06','Branch trains over a no-signal feature space')
    cl=[('STK11','$-$0.026','label-space mismatch (signal in TME)'),('KEAP1','$-$0.008','spread: no morphological projection'),('RBM10','+0.019','collapse-to-prior (n = 37)')]
    rng=np.random.RandomState(2)
    for j,(g,d,t) in enumerate(cl):
        x0=0.35+j*1.6
        for i in range(6): c.ax.add_patch(Rectangle((x0+i*0.2,y2+1.25),0.15,0.3+rng.rand()*0.15,fc='#f0b27a',ec='none'))
        c.text(x0+0.55,y2+2.15,g,8.5,weight='bold',color='#b45f06'); c.text(x0+0.55,y2+1.85,'$\\Delta$AUROC '+d,8,color='#444')
        c.text(x0+0.55,y2+0.9,t,8,w=1.5,h=0.65,color='#555',style='italic')
    c.text(5.9,y2+1.5,'$\\phi_k$ near-uniform, $|I_{kl}|$ < 0.01: fold-specific exploration without convergence.',8.3,color='#333',w=2.1,h=1.6)
    c.box(0.3,y2+0.08,pw-0.3,0.5,'FC-MIL ~ B2: no real Choquet contribution (RBM10 lift comes from the shared embedding pathway)',8,fc='white',ec='#e08a1e',tc='#b45f06',weight='bold')
    # A
    y3=y2-2.75; panel(y3,2.55,'#e8f1fa','#4a90c2','Silent (regime A): TP53, EGFR','#1f5f8b','CTransPath embedding saturates the signal')
    for i in range(6): c.ax.add_patch(Rectangle((0.5+i*0.42,y3+1.0),0.32,0.7,fc='#7fb0d3',ec='none')); c.text(0.66+i*0.42,y3+0.82,pats[i],8,color='#333')
    c.ax.plot([0.45,3.05],[y3+1.7,y3+1.7],color='#555',ls='--',lw=P(1))
    c.text(3.15,y3+1.7,'1/6',8,color='#555',ha='left')
    c.text(5.5,y3+1.3,'$\\phi_k$ = 1/6 for all k, $|I_{kl}|$ << 0.1. Choquet reduces to an additive weighted average; the signal lives in the shared embedding pathway.',8.3,color='#333',w=3.0,h=1.5)
    c.box(0.3,y3+0.08,pw-0.3,0.42,'FC-MIL ~ B2: $|\\Delta$AUROC$|$ $\\leq$ 0.005, $\\Delta\\sigma$ < 0 (no engagement, no harm)',8.3,fc='white',ec='#4a90c2',tc='#1f5f8b',weight='bold')
    c.save(OUT+'choquet_regimes.png')
regimes()
