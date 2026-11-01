from fx import *
import numpy as np
from matplotlib.patches import Patch
OUT='../man_out/'
COL=["#8e44ad","#3498db","#2e8b57","#7f8c8d","#b8c0c4"]
def perclass():
    W,H=7.2,9.6; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    classes=[('Cribriform','55 tiles'),('Micropap.','55 tiles'),('Solid','85 tiles'),('Papillary','100 tiles'),('Acinar','145 tiles'),('Lepidic','69 tiles')]
    meths=['FuzzyArcLoss V2','ArcFace','V3 SubCenters','Softmax (CE)','SphereFace']
    mc=['#8e44ad','#3498db','#2874a6','#7f8c8d','#aab7b8']
    D={'FuzzyArcLoss V2':[(83.6,9.2),(93.8,3.6),(94.6,3.1),(91.8,2.5),(95.3,1.9),(94.8,3.7)],
       'ArcFace':[(81.4,10.0),(94.9,3.4),(95.0,2.9),(92.6,3.8),(95.2,2.2),(93.9,4.4)],
       'V3 SubCenters':[(79.1,10.5),(94.4,3.6),(94.3,2.4),(92.4,3.3),(95.2,1.6),(95.4,3.7)],
       'Softmax (CE)':[(81.5,10.4),(94.3,6.0),(94.7,2.3),(90.6,3.8),(94.3,2.0),(93.8,4.6)],
       'SphereFace':[(76.1,12.8),(91.2,8.2),(94.2,2.5),(91.0,4.1),(93.5,2.4),(94.3,4.8)]}
    c.text(W/2,H-0.35,'Per-class F1 scores across 5 methods (15-run mean ± std)\nRed shading = minority classes (identical size, different boundary ambiguity)',9.5,weight='bold',w=W-0.3,h=0.6)
    ax=c.fig.add_axes([1.1/W,0.7/H,5.95/W,7.45/H]); xl=(60,108)
    bh=0.15; pitch=0.17; gap=0.35; y=0; cen=[]
    tops=[]
    for ci,(cn,tn) in enumerate(classes):
        ys=[]; ytop=-(y)+0.1
        for mi,m in enumerate(meths):
            v,s=D[m][ci]; yy=-(y+mi*pitch)
            ax.barh(yy,v-xl[0],left=xl[0],height=bh,color=mc[mi],edgecolor='white',lw=P(.5),zorder=3)
            ax.errorbar(v,yy,xerr=s,color='k',capsize=P(2),lw=P(.8),capthick=P(.8),zorder=4)
            ax.text(v+s+0.5,yy,f'{v:.1f} ± {s:.1f}',va='center',ha='left',fontsize=P(8),zorder=5)
            ys.append(yy)
        ybot=min(ys)-0.12
        if ci<2: ax.axhspan(ybot,ytop,color='#fbe9e7',zorder=0,lw=0)
        cen.append(np.mean(ys)); y+=5*pitch+gap
    ax.set_yticks(cen); ax.set_yticklabels([f'{a}\n({b})' for a,b in classes],fontsize=P(9),fontweight='bold'); ax.tick_params(axis='y',length=0)
    ax.set_xlim(*xl); ax.set_ylim(-(y-gap)-0.05,0.18); ax.set_xticks([60,70,80,90,100]); ax.tick_params(axis='x',labelsize=P(8))
    ax.grid(axis='x',alpha=.3,lw=P(.6),zorder=0)
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    ax.set_xlabel('Per-class F1 (%)',fontsize=P(9))
    c.fig.legend(handles=[Patch(fc=mc[i],label=m) for i,m in enumerate(meths)],loc='upper center',bbox_to_anchor=(0.5,(H-0.7)/H),ncol=3,fontsize=P(8),frameon=False,handlelength=1.4,columnspacing=1.4)
    c.save(OUT+'perclass_f1_bar.png'); print(audit(c.fig))
def single():
    W,H=7.2,7.4; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    T={'S':('Standard','#7f8c8d'),'F':('Fixed margin','#3498db'),'Z':('Fuzzy margin','#8e44ad'),'M':('Metric','#e67e22')}
    rows=[('SphereFace',95.03,'F',1),('FuzzyArcLoss V2 (Optuna)',94.48,'Z',1),('AdaptiveFace',93.97,'F',0),('FuzzyArcLoss V2 ClassParams',93.92,'Z',0),('FuzzyArcLoss V3 SC (Optuna)',93.73,'Z',1),('ArcFace',93.38,'F',1),('FuzzyCosFace V2',93.21,'Z',0),('Softmax (CE)',92.87,'S',1),('Label Smoothing CE',92.64,'S',0),('FuzzyArcLoss V1',92.48,'Z',0),('Combined Margin (Arc+Cos)',92.31,'F',0),('FuzzyArcLoss V2 (default)',92.10,'Z',0),('FuzzySphereFace V2',91.85,'Z',0),('CosFace',91.72,'F',0),('FuzzyArcLoss V3 (Optuna)',91.30,'Z',0),('Center Loss + Softmax',90.88,'M',0),('Focal Loss',90.54,'S',0),('Triplet + Angular',89.23,'M',0)]
    c.text(W/2,H-0.35,'Single-run screening: 18 loss functions ranked by macro-F1\n(128 test tiles, 80/20 split; stars = selected for K-fold)',9.5,weight='bold',w=W-0.3,h=0.6)
    ax=c.fig.add_axes([2.35/W,1.0/H,4.75/W,5.65/H]); n=len(rows)
    for i,(nm,v,t,st) in enumerate(rows):
        y=n-1-i; ax.barh(y,v-88,left=88,height=0.7,color=T[t][1],zorder=3)
        ax.text(v-0.05,y,f'{v:.2f}',ha='right',va='center',fontsize=P(8),color='white',weight='bold',zorder=4)
        if st: ax.plot(v+0.17,y,'*',color='#e74c3c',ms=P(10),zorder=4)
    ax.set_yticks(range(n)); ax.set_yticklabels([r[0] for r in rows][::-1],fontsize=P(8)); ax.tick_params(axis='y',length=0)
    ax.set_xlim(88,96); ax.set_ylim(-0.6,n-0.4); ax.set_xticks(range(88,97)); ax.tick_params(axis='x',labelsize=P(8))
    ax.grid(axis='x',alpha=.3,lw=P(.6),zorder=0); ax.set_xlabel('Macro-F1 (%)',fontsize=P(9))
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    c.fig.legend(handles=[Patch(fc=v[1],label=v[0]) for v in T.values()],loc='lower center',bbox_to_anchor=(0.5,0.0),ncol=4,fontsize=P(8),frameon=False,handlelength=1.4,columnspacing=1.2)
    c.save(OUT+'singlerun_18losses_bar.png'); print(audit(c.fig))
perclass(); single()
