from fx import *
import numpy as np
from scipy import stats
OUT='../man_out/'
def egfr():
    W,H=7.2,6.4; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,H-0.25,'Why a false negative is statistically expected for EGFR slides with atypical morphology',9.8,weight='bold',w=W-0.3,h=0.7)
    ax=c.fig.add_axes([0.08,0.27,0.89,0.58])
    x=np.linspace(0,1,500); wt=stats.gamma.pdf(x,3,scale=0.085); mu=stats.gamma.pdf(x,5,scale=0.075)
    wt=wt/wt.max()*0.95; mu=mu/mu.max()
    ax.fill_between(x,wt,color='#d8909c',alpha=.7,lw=0); ax.plot(x,wt,color='#b5495b',lw=P(1.2))
    ax.fill_between(x,mu,color='#7aa0c8',alpha=.7,lw=0); ax.plot(x,mu,color='#3b6a9e',lw=P(1.2))
    ax.axvline(0.5,color='#777',ls=':',lw=P(1))
    ax.set_xlim(0,1); ax.set_yticks([]); ax.tick_params(axis='x',labelsize=P(8.5))
    ax.set_xlabel('Predicted P(EGFR mutated)',fontsize=P(9)); ax.set_ylabel('Density (normalised)',fontsize=P(9),loc='bottom')
    bb=dict(boxstyle='round,pad=0.35',lw=1)
    ax.set_ylim(0,2.65)
    ax.text(0.015,2.55,'False-negative tail: EGFR-mutant slides\nwhose morphology lacks the typical\nlepidic/papillary fingerprint fall here',fontsize=P(8),va='top',bbox=dict(fc='#e8eef9',ec='#3b6a9e',**bb))
    ax.annotate('',xy=(0.04,0.42),xytext=(0.04,1.95),arrowprops=dict(arrowstyle='-|>',color='#3b6a9e',lw=P(1)))
    ax.text(0.985,2.55,'False-positive tail: wild-type slides\nwhose morphology happens to\nresemble EGFR fall here',fontsize=P(8),va='top',ha='right',bbox=dict(fc='#f9e6e8',ec='#b5495b',**bb))
    ax.annotate('',xy=(0.62,0.1),xytext=(0.82,1.95),arrowprops=dict(arrowstyle='-|>',color='#b5495b',lw=P(1)))
    ax.plot([0.076,0.076],[0,0.43],color='k',ls='--',lw=P(1.4),zorder=4)
    ax.plot(0.076,0.43,'o',color='k',ms=P(8),zorder=5)
    ax.text(0.13,1.75,'Slide TCGA-86-8280\n(EGFR-mutant): P = 0.076,\na false negative',fontsize=P(8),va='top',bbox=dict(fc='white',ec='k',**bb))
    ax.annotate('',xy=(0.08,0.47),xytext=(0.15,1.38),arrowprops=dict(arrowstyle='-',color='k',lw=P(1)))
    ax.text(0.5,2.55,'threshold\n= 0.5',fontsize=P(8),color='#555',va='top',ha='center',bbox=dict(fc='white',ec='none',pad=2))
    for s_ in ('top','right','left'): ax.spines[s_].set_visible(False)
    c.ax.add_patch(Rectangle((0.8,0.95),0.25,0.14,fc='#d8909c',alpha=.8)); c.text(1.15,1.02,'Wild-type EGFR slides (n = 609, 88.6%)',8.2,ha='left')
    c.ax.add_patch(Rectangle((4.2,0.95),0.25,0.14,fc='#7aa0c8',alpha=.8)); c.text(4.55,1.02,'EGFR-mutant slides (n = 78, 11.4%)',8.2,ha='left')
    c.text(W/2,0.4,'Schematic: the score distributions overlap heavily (AUROC = 0.701, i.e. about 30% of positive-negative pairs mis-ranked; AUPRC = 0.36; prevalence 11.4%).',8,style='italic',color='#444',w=W-0.4,h=0.55)
    c.save(OUT+'egfr_score_overlap.png')
egfr()
