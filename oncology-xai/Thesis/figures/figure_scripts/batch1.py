from fx import *
import numpy as np
from scipy import stats
OUT='../man_out/'
# ---------- b1_per_gene ----------
def b1():
    W,H=7.2,5.0; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    ax=c.fig.add_axes([0.17,0.17,0.78,0.68])
    g=['EGFR','STK11','KRAS','TP53','KEAP1','RBM10']; v=[.634,.545,.522,.518,.489,.474]
    col=['#b8900a','#9aa0ab','#9aa0ab','#9aa0ab','#b0172f','#b0172f']
    ax.barh(range(6)[::-1],v,color=col,height=0.62,zorder=3)
    ax.set_yticks(range(6)[::-1]); ax.set_yticklabels(g,fontsize=P(9))
    ax.set_xlim(0.40,0.80); ax.tick_params(axis='x',labelsize=P(8.5)); ax.set_xlabel('B1 AUROC (5-fold CV)',fontsize=P(9))
    for i,x in enumerate(v): ax.text(x-0.004,5-i,f'{x:.3f}',va='center',ha='right',fontsize=P(8.5),fontweight='bold',color='white',zorder=4)
    for x,cc in [(.5,'#777'),(.530,'#222'),(.607,'#2e7d32'),(.658,'#1565c0')]:
        ax.plot([x,x],[-0.6,6.3],color=cc,ls='--',lw=P(1.2),zorder=1)
    ax.text(.5-0.003,7.0,'random 0.500',ha='right',va='center',fontsize=P(8.2),color='#777')
    ax.text(.530+0.003,6.6,'B1 0.530',ha='left',va='center',fontsize=P(8.2),color='#222')
    ax.text(.607-0.003,7.0,'B3 0.607',ha='right',va='center',fontsize=P(8.2),color='#2e7d32')
    ax.text(.658+0.003,7.0,'B2 0.658',ha='left',va='center',fontsize=P(8.2),color='#1565c0')
    ax.set_ylim(-0.6,7.5)
    ax.text(0.665,5.0,'EGFR: concentrated-signal\nregime (Finding 4)',fontsize=P(8.2),color='#8a6d0b',style='italic',va='center')
    ax.text(0.665,0.5,'below random: no single-pattern\ncorrelate, naive aggregation fails',fontsize=P(8.2),color='#b0172f',style='italic',va='center',ha='left')
    for s in ('top','right'): ax.spines[s].set_visible(False)
    c.text(W/2,H-0.15,'B1 (XGBoost on slide-level pattern frequencies): AUROC by gene',9.5,weight='bold',w=W-0.3)
    c.save(OUT+'b1_per_gene.png')
# ---------- choquet bars ----------
def choq(name,gene,sh,ints,order_note):
    W,H=7.2,7.4; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    pc={'Cribriform':'#00e5e5','Solid':'#7a0000','Acinar':'#ff2020','Lepidic':'#1030ff','Micropapillary':'#20e020','Papillary':'#ffee00'}
    ax=c.fig.add_axes([0.22,0.575,0.72,0.34])
    n=len(sh); y=np.arange(n)[::-1]
    ax.barh(y,[s[1] for s in sh],color=[pc[s[0]] for s in sh],edgecolor='#333',lw=.6,height=0.62)
    ax.set_yticks(y); ax.set_yticklabels([s[0] for s in sh],fontsize=P(8.5))
    ax.axvline(1/6,color='#555',ls='--',lw=P(1.2)); ax.set_xlim(0,0.25); ax.tick_params(axis='x',labelsize=P(8.5))
    ax.set_xlabel('Shapley value $\\phi$  (dashed line: uniform 1/6)',fontsize=P(8.8))
    for yy,s in zip(y,sh): ax.text(s[1]+0.004,yy,f'$\\phi$={s[1]:.4f} ({s[2]})',va='center',fontsize=P(8.2))
    ax.set_title(f'Pattern Shapley values: {gene} (singleton importance)',fontsize=P(9.2),fontweight='bold',loc='left')
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    ax2=c.fig.add_axes([0.40,0.09,0.54,0.34]); n=len(ints); y=np.arange(n)[::-1]
    mx=max(abs(i[1]) for i in ints)
    ax2.barh(y,[abs(i[1]) for i in ints],color=['#2563eb' if i[1]>0 else '#ef4444' for i in ints],edgecolor='#333',lw=.6,height=0.62)
    ax2.set_yticks(y); ax2.set_yticklabels([i[0] for i in ints],fontsize=P(8.5)); ax2.set_xlim(0,mx*1.85)
    ax2.tick_params(axis='x',labelsize=P(8.5)); ax2.set_xlabel('Interaction index $|I|$',fontsize=P(8.8))
    for yy,i in zip(y,ints): ax2.text(abs(i[1])+mx*0.03,yy,('Synergy +' if i[1]>0 else 'Redundancy ')+f'{i[1]:.3f}'.replace('-','$-$') if i[1]>0 else 'Redundancy $-$'+f'{abs(i[1]):.3f}',va='center',fontsize=P(8.2))
    ax2.set_title(f'Interaction indices: {gene} (pairwise synergy / redundancy)',fontsize=P(9.2),fontweight='bold',loc='left',x=-0.7)
    for s_ in ('top','right'): ax2.spines[s_].set_visible(False)
    c.save(OUT+name)
def lat():
    W,H=7.2,8.2; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,H-0.3,'How $I_{lepidic,solid}$ = +0.032 modifies the fuzzy measure $\\mu(S)$',11,weight='bold',w=W-0.3)
    c.text(W/2,H-0.78,'Only the subset containing BOTH lepidic and solid receives a bump;\nthe Choquet integral picks it up only when both patterns are present.',8.8,style='italic',color='#555',w=W-0.3,h=0.6)
    ax=c.fig.add_axes([0.13,0.43,0.82,0.40]); x=np.arange(4)
    base=[0,.165,.168,.333]; withI=[0,.165,.168,.365]
    ax.bar(x-0.19,base,0.36,color='#9aa0ab',edgecolor='#333',lw=.6,label='without $I$ (additive baseline)')
    ax.bar(x+0.19,[0,.165,.168,.333],0.36,color='#a8d8b5',edgecolor='#333',lw=.6,label='with learned $I$')
    ax.bar([3.19],[0.032],0.36,bottom=[0.333],color='#2e8b57',edgecolor='#333',lw=.6)
    for xx,b,w in [(1,.165,.165),(2,.168,.168),(3,.333,.365)]:
        ax.text(xx-0.19,b+0.006,f'{b:.3f}',ha='center',fontsize=P(8.2)); ax.text(xx+0.19,w+0.006,f'{w:.3f}',ha='center',fontsize=P(8.2),fontweight='bold' if xx==3 else 'normal')
    ax.text(3.19+0.25,0.352,'bump\n+0.032',fontsize=P(8.2),color='#2e8b57',va='center',ha='left')
    ax.set_xticks(x); ax.set_xticklabels(['$\\emptyset$','{lepidic}','{solid}','{lepidic, solid}'],fontsize=P(8.8))
    ax.set_ylim(0,0.5); ax.set_xlim(-0.6,4.0); ax.tick_params(axis='y',labelsize=P(8.5)); ax.set_ylabel('$\\mu(S)$',fontsize=P(9.5))
    ax.legend(fontsize=P(8.2),loc='upper left',frameon=False)
    ax.set_xlabel('Subset $S \\subseteq$ {lepidic, solid} of the 6-pattern lattice',fontsize=P(8.5))
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    c.ax.add_patch(FancyBboxPatch((0.2,0.15),W-0.4,2.7,boxstyle='round,pad=0,rounding_size=0.1',fc='#f2efe8',ec='#1f3a5f'))
    c.text(W/2,2.62,'On TCGA-55-7815 (KRAS-mutant)',9.5,weight='bold',color='#1f3a5f')
    rows=[('p(lepidic)','> 0','#a07d00'),('p(solid)','= 0.64% (> 0)','#a07d00'),('p(micropapillary)','= 79.44%','#555'),('p(cribriform)','= 2.5%','#555')]
    for i,(a,b,cc) in enumerate(rows):
        c.text(0.6,2.28-i*0.27,a,8.5,ha='left',color=cc); c.text(2.5,2.28-i*0.27,b,8.5,ha='left',color=cc)
    c.text(W/2,1.12,'p(lepidic) > 0 AND p(solid) > 0: Choquet integral aggregates with $\\mu$({lep, sol}) = 0.365 (vs 0.333 additive)',8.5,weight='bold',color='#2e8b57',w=W-0.8,h=0.55)
    c.text(W/2,0.5,'$P$(KRAS) = 0.965 (Combined) vs 0.782 (Embeddings-only)',8.5,color='#222',w=W-0.8,h=0.4)
    c.save(OUT+'kras_mu_subset_lattice.png')
b1()
choq('choquet_kras_55_7815.png','KRAS',[('Cribriform',.1703,'+2.18%'),('Solid',.1684,'+1.04%'),('Acinar',.1671,'+0.26%'),('Lepidic',.1651,'$-$0.94%'),('Micropapillary',.1646,'$-$1.24%'),('Papillary',.1646,'$-$1.24%')],[('Lepidic × Solid',.032),('Solid × Acinar',.025),('Cribriform × Acinar',-.019),('Cribriform × Papillary',-.022),('Micropap. × Cribriform',-.025)],'')
choq('choquet_rbm10_78_7148.png','RBM10',[('Cribriform',.1671,'+0.26%'),('Solid',.1668,'+0.08%'),('Acinar',.1668,'+0.08%'),('Micropapillary',.1665,'$-$0.10%'),('Papillary',.1664,'$-$0.16%'),('Lepidic',.1664,'$-$0.16%')],[('Papillary × Lepidic',.008),('Micropap. × Lepidic',.003),('Cribriform × Lepidic',.003),('Solid × Acinar',-.002),('Micropap. × Cribriform',-.003)],'')
lat()
