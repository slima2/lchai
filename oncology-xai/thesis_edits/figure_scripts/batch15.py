from fx import *
import numpy as np
from matplotlib.lines import Line2D
OUT='../man_out/'
NAVY='#1b3a5c'
def prev():
    W,H=7.2,7.4; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    genes=["RBM10","STK11","EGFR","KEAP1","KRAS","TP53"]; prev_=np.array([5.4,9.9,11.4,14.3,20.4,46.0])
    au=np.array([0.661,0.695,0.701,0.610,0.609,0.718]); ap=np.array([0.17,0.32,0.36,0.30,0.34,0.64]); bm=["FC-MIL","PI-ABMIL","B2","PI-ABMIL","FC-MIL","B2"]
    c.text(W/2,H-0.28,'AUROC, AUPRC and the prevalence-driven gap on TCGA-LUAD',10,weight='bold',w=W-0.3,h=0.4)
    ax=c.fig.add_axes([0.85/W,2.7/H,6.2/W,4.1/H]); x=np.arange(6)
    for xi,hi,lo in zip(x,au,ap):
        ax.fill_between([xi-0.18,xi+0.18],[lo,lo],[hi,hi],color='#7ec8e3',alpha=.35,lw=0)
        ax.text(xi+0.22,lo+0.3*(hi-lo),f'{hi-lo:+.2f}',ha='left',va='center',fontsize=P(8.5),color=NAVY,weight='bold')
    ax.plot(x,au,'o',color=NAVY,ms=P(9),mec='white',mew=P(1),zorder=3,label='Mean AUROC (best condition per gene)')
    ax.plot(x,ap,'s',color='#e05252',ms=P(8),mec='white',mew=P(1),zorder=3,label='Mean AUPRC (same condition)')
    ax.plot(x,prev_/100,'^--',color='#888',ms=P(8),lw=P(1),mec='white',zorder=2,label='AUPRC random baseline (= prevalence)')
    for xi,a,b in zip(x,au,bm): ax.text(xi,a+0.035,b,ha='center',va='bottom',fontsize=P(8),color=NAVY)
    ax.axhline(0.5,color='#888',ls=':',lw=P(1)); ax.text(5.65,0.505,'AUROC random = 0.50',ha='right',va='bottom',fontsize=P(8),color='#555')
    ax.set_xlim(-0.5,5.7); ax.set_ylim(0,0.85); ax.set_xticks(x); ax.set_xticklabels([f'{g}\n({p}%)' for g,p in zip(genes,prev_)],fontsize=P(8.5))
    ax.tick_params(axis='y',labelsize=P(8)); ax.grid(axis='y',alpha=.3,lw=P(.6)); ax.set_axisbelow(True)
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    ax.set_ylabel('Metric value (mean over 5-fold CV)',fontsize=P(9)); ax.set_xlabel('Target gene (sorted by ascending mutation prevalence in TCGA-LUAD)',fontsize=P(8.5))
    c.fig.legend(loc='lower center',bbox_to_anchor=(0.5,0.13),ncol=1,fontsize=P(8),frameon=False,handlelength=2)
    c.text(W/2,0.4,'Blue band = AUROC-AUPRC gap. As prevalence increases, the gap shrinks because the AUPRC random baseline rises towards AUROC, while AUROC stays in a narrow band (0.61-0.72) independent of prevalence.',8,style='italic',color='#444',w=W-0.3,h=0.7)
    c.save(OUT+'auroc_auprc_prevalence.png'); print(audit(c.fig))
def var():
    W,H=7.2,6.9; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,H-0.28,'FC-MIL engagement map: AUROC gain vs. fold-variance gain',10,weight='bold',w=W-0.3,h=0.4)
    ax=c.fig.add_axes([0.95/W,1.4/H,6.1/W,4.95/H]); L=0.045
    ax.set_xlim(-L,L); ax.set_ylim(-L,L)
    ax.add_patch(Rectangle((-L,0),L,L,fc='#fbf6ef',ec='none',zorder=0)); ax.add_patch(Rectangle((0,0),L,L,fc='#f1f7f3',ec='none',zorder=0))
    ax.add_patch(Rectangle((-L,-L),L,L,fc='#eff3f7',ec='none',zorder=0)); ax.add_patch(Rectangle((0,-L),L,L,fc='#e6f4ea',ec='none',zorder=0))
    ax.axhline(0,color='#888',lw=P(1)); ax.axvline(0,color='#888',lw=P(1)); ax.grid(alpha=.35,ls=':',lw=P(.6),zorder=1)
    OR,BL,GN='#e67e22','#2874a6','#27ae60'
    pts=[('STK11',-0.026,0.035,OR,(0.002,0.004),'left'),('RBM10',0.019,0.009,OR,(0.002,0.004),'left'),('KEAP1',-0.008,0.0,OR,(0.001,0.0055),'left'),
         ('TP53',-0.003,-0.005,BL,(0.0024,0.0033),'right'),('EGFR',-0.005,-0.008,BL,(-0.0025,0.0),'right'),('KRAS',0.002,-0.019,GN,(0.002,-0.0045),'left')]
    for n,xv,yv,col,(dx,dy),ha in pts:
        ax.plot(xv,yv,'o',color=col,ms=P(10),mec='white',mew=P(1),zorder=4)
        ax.text(xv+dx,yv+dy,n,color=col,fontsize=P(9),weight='bold',ha=ha,va='center',zorder=5)
    q=dict(fontsize=P(8.5),style='italic',weight='bold')
    ax.text(-0.043,0.003,'engagement without\nconversion',color=OR,ha='left',va='bottom',**q)
    ax.text(0.043,0.041,'unstable\nexploration',color='#7f8c8d',ha='right',va='top',**q)
    ax.text(-0.043,-0.041,'silent /\nnot engaged',color=BL,ha='left',va='bottom',**q)
    ax.text(0.043,-0.041,'constructive\n(productive + stable)',color=GN,ha='right',va='bottom',**q)
    ax.set_xlabel('ΔAUROC (FC-MIL − B2)',fontsize=P(9)); ax.set_ylabel('Δσ (FC-MIL − B2, fold std)',fontsize=P(9)); ax.tick_params(labelsize=P(8))
    hs=[Line2D([0],[0],marker='o',ls='',color=col,ms=P(9),label=l) for col,l in ((GN,'Regime C (constructive)'),(BL,'Regime A (silent)'),(OR,'Regime B (engaged but unproductive)'))]
    c.fig.legend(handles=hs,loc='lower center',bbox_to_anchor=(0.5,0.02),ncol=3,fontsize=P(8),frameon=False,title='Structural taxonomy (Finding 2)',title_fontsize=P(8.5),columnspacing=1.2,handletextpad=0.2)
    c.save(OUT+'choquet_variance_map.png'); print(audit(c.fig))
prev(); var()
