import os
from fx import *
import numpy as np
from matplotlib.lines import Line2D
OUT='../man_out/'
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'gen_fuzzy_mf_plots.py')).read().split('def trapezoid')[0].split('OUT_DIR')[0]
ns={}; exec(src+"\n",ns)
code=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'gen_fuzzy_mf_plots.py')).read()
i=code.index('SCALES = {'); j=code.index('def trapezoid'); exec(code[i:j],ns); SC=ns['SCALES']
def trap(x,abcd):
    a,b,c,d=abcd; y=np.zeros_like(x)
    if b>a: m=(x>=a)&(x<b); y[m]=(x[m]-a)/(b-a)
    m=(x>=b)&(x<=c); y[m]=1
    if d>c: m=(x>c)&(x<=d); y[m]=(d-x[m])/(d-c)
    return y
def fz():
    W,H=7.2,9.2; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    order=[('shap_balance','SHAP Balance (pattern contribution %)','Pattern contribution (%)'),
           ('interaction_index','Interaction Index $|I_{jk}|$','$|I_{jk}|$'),
           ('shapley_profile','Shapley Profile (spread)','Spread = max φ − min φ'),
           ('shapley_individual','Shapley Individual $|\\delta_k|$','$|\\delta_k|$ from uniform (%)'),
           ('attention_level','ABMIL Attention Level (tile percentile)','Attention percentile')]
    pw,ph=2.95,1.35; rowh=3.0
    cells=[(0.6,0),(3.95,0),(0.6,1),(3.95,1),(2.125,2)]
    for (key,ttl,xl),(x,r) in zip(order,cells):
        spec=SC[key]; y=H-0.55-ph-r*rowh
        ax=c.fig.add_axes([x/W,y/H,pw/W,ph/H]); xmin,xmax=spec['xlim']; xs=np.linspace(xmin,xmax,2000)
        for lab,abcd,col in spec['sets']:
            yy=trap(xs,abcd); ax.plot(xs,yy,color=col,lw=P(1.8)); ax.fill_between(xs,yy,alpha=.15,color=col)
        ax.set_xlim(xmin,xmax); ax.set_ylim(0,1.08); ax.set_yticks([0,0.5,1.0]); ax.axhline(1,color='#d1d5db',lw=P(.6),ls='--')
        ax.tick_params(labelsize=P(8.5),length=P(3)); ax.set_xlabel(xl,fontsize=P(9)); ax.set_ylabel('μ',fontsize=P(9.5),rotation=0,labelpad=P(8))
        for s in ('top','right'): ax.spines[s].set_visible(False)
        ax.set_title(ttl,fontsize=P(9.5),fontweight='bold',pad=P(6))
        hs=[Line2D([0],[0],color=col,lw=P(2.4),label=lab) for lab,_,col in spec['sets']]
        c.fig.legend(handles=hs,loc='upper center',bbox_to_anchor=((x+pw/2)/W,(y-0.5)/H),ncol=2,fontsize=P(8),frameon=False,columnspacing=1.0,handlelength=1.4,handletextpad=0.5,labelspacing=0.3)
    c.save(OUT+'fuzzy_mf_scales_combined.png'); print(audit(c.fig))
fz()
