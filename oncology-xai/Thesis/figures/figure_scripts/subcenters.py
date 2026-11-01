from fx import *
import numpy as np
from matplotlib.patches import Circle
W,H=7.2,8.6
c=Canvas(W,H,minpt=8.0); k=c.k
P=lambda p:p/k
# panel (a) geometry
axa=c.fig.add_axes([0.10,0.56,0.80,0.36]); 
cls={'Acinar':(0.1,1.0,'#e74c3c'),'Lepidic':(0.9,0.4,'#2980b9'),'Papillary':(-0.8,0.6,'#f39c12'),'Micropap.':(-0.95,-0.4,'#27ae60'),'Cribriform':(0.8,-0.6,'#16a085'),'Solid':(-0.15,-1.0,'#8e44ad')}
th=np.linspace(0,2*np.pi,200); axa.plot(np.cos(th)*1.1,np.sin(th)*1.1,color='#ccc',lw=1)
rng=np.random.RandomState(1)
for n,(x,y,col) in cls.items():
    for j in range(4): axa.plot(x+rng.randn()*0.14,y+rng.randn()*0.14,'*',color=col,ms=P(9),alpha=.6,mec='none')
    axa.add_patch(plt.Rectangle((x-0.07,y-0.07),0.14,0.14,fc=col,ec='#222',lw=1.5,zorder=3))
axa.set_xlim(-1.75,1.75); axa.set_ylim(-1.55,1.55); axa.set_aspect('equal')
for n,(x,y,col) in cls.items():
    dx,dy={'Acinar':(0.0,0.2),'Lepidic':(0.0,0.2),'Papillary':(0.0,0.42),'Micropap.':(0,-0.25),'Cribriform':(0,-0.25),'Solid':(0,-0.25)}[n]
    axa.text(x+dx,y+dy,n,fontsize=P(8.5),ha='center',va='center',color=col,fontweight='bold')
axa.set_xlabel('Embedding dim. $j$',fontsize=P(9)); axa.set_ylabel('Embedding dim. $k$',fontsize=P(9)); axa.tick_params(labelsize=P(8.5))
axa.set_title('(a) Prototype geometry on $\\mathbb{S}^{511}$\nsquares = V2 prototypes, stars = V3 sub-centers',fontsize=P(9.5),fontweight='bold',loc='left')
# panel (b)
axb=c.fig.add_axes([0.12,0.12,0.34,0.33])
axb.bar([0,1],[3.072,12.288],color=['#8e44ad','#3498db'],width=0.55)
axb.set_xticks([0,1]); axb.set_xticklabels(['V2\n1 proto/class','V3\n4 sub-centers'],fontsize=P(8.5))
axb.set_ylabel('Prototype parameters (thousands)',fontsize=P(8.5)); axb.tick_params(axis='y',labelsize=P(8.5)); axb.set_ylim(0,15)
axb.text(0,3.072+0.4,'3,072',ha='center',fontsize=P(9),fontweight='bold'); axb.text(1,12.288+0.4,'12,288',ha='center',fontsize=P(9),fontweight='bold')
axb.annotate('4x',xy=(0.85,11),xytext=(0.2,7.2),fontsize=P(10),fontweight='bold',color='#c0392b',arrowprops=dict(arrowstyle='-|>',color='#c0392b',connectionstyle='arc3,rad=-0.3'))
axb.set_title('(b) Parameter count',fontsize=P(9.5),fontweight='bold',loc='left')
for s_ in ('top','right'): axb.spines[s_].set_visible(False)
# panel (c)
axc=c.fig.add_axes([0.62,0.12,0.34,0.33])
axc.bar([0,1],[92.31,91.79],yerr=[2.04,2.12],capsize=P(5),color=['#8e44ad','#3498db'],width=0.55,error_kw=dict(lw=1.5))
axc.set_ylim(85,97); axc.set_xticks([0,1]); axc.set_xticklabels(['FuzzyArcLoss V2\n(Optuna)','FuzzyArcLoss V3\nSubCenters (C=4)'],fontsize=P(8.5))
axc.set_ylabel('Macro-F1 (%)',fontsize=P(8.5)); axc.tick_params(axis='y',labelsize=P(8.5))
axc.text(0,92.31+2.04+0.3,'92.31\n$\\pm$2.04',ha='center',fontsize=P(8.5),fontweight='bold'); axc.text(1,91.79+2.12+0.3,'91.79\n$\\pm$2.12',ha='center',fontsize=P(8.5),fontweight='bold')
c.text(W/2,0.2,'$-$0.52 pp: simpler models generalise better under data scarcity',8.5,color='#c0392b',style='italic',w=6.5,h=0.5)
axc.set_title('(c) 15-run K-fold evaluation',fontsize=P(9.5),fontweight='bold',loc='left')
for s_ in ('top','right'): axc.spines[s_].set_visible(False)
c.save('../man_out/fuzzyarcloss_v3_subcenters.png')
