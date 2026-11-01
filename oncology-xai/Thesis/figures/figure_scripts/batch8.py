from fx import *
import numpy as np
OUT='../man_out/'
DK='#2c3e50'; GN='#27ae60'; OR='#e67e22'; RD='#c0392b'
def scale():
    W,H=7.2,7.4; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,7.0,'Interpretability vs data scale across H&E mutation prediction studies\n(EGFR axis; full Conclusive AUROC threshold = 0.70)',9.5,weight='bold',color=DK,w=W-0.3,h=0.6)
    ax=c.fig.add_axes([0.9/W,2.7/H,6.1/W,3.9/H]); ax.set_xscale('log'); ax.set_xlim(250,110000); ax.set_ylim(0.61,0.94)
    ax.axvspan(250,1000,color='#eef1f5',alpha=.8,lw=0); ax.axvspan(1000,10000,color='#fdf3e3',alpha=.8,lw=0); ax.axvspan(10000,110000,color='#f3eef8',alpha=.8,lw=0)
    ax.grid(alpha=.3,lw=P(.6),ls=':'); ax.axhline(0.70,color='#777',ls='--',lw=P(1))
    ax.tick_params(labelsize=P(8)); ax.set_yticks([0.65,0.70,0.75,0.80,0.85,0.90])
    ax.set_xlabel('Cohort size N (slides, log scale)',fontsize=P(9),weight='bold',color=DK); ax.set_ylabel('EGFR AUROC',fontsize=P(9),weight='bold',color=DK)
    mk=dict(mec=DK,mew=P(1))
    pts=[('o',RD,382,0.826),('o',RD,3600,0.86),('o',RD,8400,0.89),('o',RD,60000,0.80),('o',RD,680,0.670),('s',OR,750,0.682),('*',GN,690,0.701),('*',GN,690,0.695)]
    for m,col,x,y in pts: ax.plot(x,y,m,color=col,ms=P(11 if m!='*' else 17),zorder=5,**mk)
    ar=dict(arrowstyle='-',color='#888',lw=P(.8),shrinkA=0,shrinkB=P(6))
    def lab(t,xy,xt,ha='left',va='center'): ax.annotate(t,xy=xy,xytext=xt,fontsize=P(8),ha=ha,va=va,color='#333',arrowprops=ar,zorder=4)
    lab('Coudray 2018\n(N=382, single split)',(382,0.826),(420,0.865),va='bottom') if False else lab('Coudray 2018 (N=382,\nsingle split)',(382,0.826),(450,0.865))
    lab('DeepGEM 2025',(3600,0.86),(4600,0.835),ha='left')
    lab('EAGLE 2025',(8400,0.89),(6200,0.915),ha='right')
    lab('CHIEF 2024',(60000,0.80),(30000,0.83),ha='right')
    lab('This thesis B2',(690,0.701),(1500,0.742))
    lab('This thesis PI-ABMIL',(690,0.695),(1500,0.715)) 
    lab('Logan 2022',(750,0.682),(1500,0.683))
    lab('Saldanha 2023',(680,0.670),(1500,0.652))
    ax.text(105000,0.707,'Conclusive threshold (AUROC = 0.70)',fontsize=P(8),style='italic',color='#555',ha='right',va='bottom')
    for t,x in (('Public-data regime',500),('Mid-scale',3200),('Foundation-scale',33000)):
        ax.text(x,0.625,t,fontsize=P(8),weight='bold',color='#4a5a6a',ha='center',va='center')
    ax.text(500,0.625,'',fontsize=P(8))
    # legend
    c.text(0.9,1.85,'Interpretability level',8.5,weight='bold',ha='left',color=DK)
    for i,(m,col,t) in enumerate([('*',GN,'Full 6-level XAI framework'),('s',OR,'Partial / single-feature interpretability'),('o',RD,'None (slide-level black-box output)')]):
        y=1.58-i*0.24; c.ax.plot(1.0,y,m,color=col,ms=P(11 if m!='*' else 15),mec=DK,mew=P(1)); c.text(1.3,y,t,8,ha='left')
    c.text(W/2,0.47,"Caveat: Coudray's 0.826 used a single 62-slide held-out test split (no cross-validation); cross-validated estimates are typically lower (Section 6.3). The vertical separation between this thesis and the foundation-scale studies (DeepGEM, EAGLE, CHIEF) is structural (data asymmetry between public and proprietary cohorts), not methodological.",8,style='italic',color='#444',w=W-0.3,h=0.9)
    c.save(OUT+'interpretability_vs_data_scale.png'); print(audit(c.fig))
scale()
