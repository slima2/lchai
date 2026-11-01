from fx import *
import numpy as np
OUT='../man_out/'
SRC='/home/claude/slima2/lchai/oncology-xai/thesis_edits/'
def load(fn):
    s=open(SRC+fn).read(); s=s[:s.index('conditions =')]
    s=s.replace('import matplotlib.pyplot as plt','').replace('matplotlib.use("Agg")','')
    ns={}; exec(s,ns); return ns['genes'],ns['data']
COL=["#7EC8E3","#1B3A5C","#2E8B57","#E05252","#B0A0D0","#F5A623"]; HAT=["","","","","//",""]
def gene_bars(fn,out,title,xlabel,xlim,xticks,ref,fmt):
    genes,data=load(fn); conds=list(data); nc=len(conds)
    W,H=7.2,10.6; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,H-0.25,title,10,weight='bold',w=W-0.3,h=0.4)
    ax=c.fig.add_axes([0.9/W,0.7/H,6.1/W,8.5/H])
    bh=0.13; pitch=0.15; gap=0.35; ypos=[]; y=0; centers=[]
    for gi,g in enumerate(genes):
        ys=[]
        for ci,cd in enumerate(conds):
            m,s=data[cd][g]; yy=-(y+ci*pitch)
            ax.barh(yy,m-xlim[0],left=xlim[0],height=bh,color=COL[ci],hatch=HAT[ci],edgecolor='white',lw=P(.5),zorder=3)
            ax.errorbar(m,yy,xerr=s,color='k',capsize=P(2),lw=P(.8),capthick=P(.8),zorder=4)
            ax.text(m+s+(xlim[1]-xlim[0])*0.008,yy,fmt(m,s),va='center',ha='left',fontsize=P(8),color='#222',zorder=5)
            ys.append(yy)
        centers.append(np.mean(ys)); y+=nc*pitch+gap
    ax.set_yticks(centers); ax.set_yticklabels(genes,fontsize=P(9.5),fontweight='bold')
    ax.set_ylim(-(y-gap)-0.08,0.12); ax.set_xlim(*xlim); ax.set_xticks(xticks); ax.tick_params(axis='x',labelsize=P(8)); ax.tick_params(axis='y',length=0)
    ax.grid(axis='x',alpha=.3,lw=P(.6),zorder=0)
    if ref is not None: ax.axvline(ref,color='gray',ls='--',lw=P(1),zorder=2)
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    ax.set_xlabel(xlabel,fontsize=P(9))
    from matplotlib.patches import Patch
    hs=[Patch(fc=COL[i],ec='white',hatch=HAT[i],label=cd) for i,cd in enumerate(conds)]
    if ref is not None:
        from matplotlib.lines import Line2D
        hs.append(Line2D([0],[0],color='gray',ls='--',label=f'Chance ({ref})'))
    c.fig.legend(handles=hs,loc='upper center',bbox_to_anchor=(0.5,(H-0.55)/H),ncol=3,fontsize=P(8),frameon=False,columnspacing=1.4,handlelength=1.6)
    c.save(OUT+out); print(audit(c.fig))
gene_bars('gen_auroc_bar_chart.py','auroc_by_gene_ver_15_mar_2026.png','AUROC per gene: 5-fold stratified CV on TCGA-LUAD','AUROC (mean ± std)',(0.36,0.93),[0.4,0.5,0.6,0.7,0.8,0.9],0.5,lambda m,s:f'{m:.3f} ± {s:.3f}')
gene_bars('gen_auprc_bar_chart.py','auprc_by_gene.png','AUPRC per gene: 5-fold stratified CV on TCGA-LUAD','AUPRC (mean ± std)',(0.0,0.92),[0,0.2,0.4,0.6,0.8],None,lambda m,s:f'{m:.2f} ± {s:.2f}')
