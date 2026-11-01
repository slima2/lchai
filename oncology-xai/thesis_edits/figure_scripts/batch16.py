from fx import *
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
OUT='../man_out/'
NAVY='#1b3a5c'; RED='#c0392b'; GOLD='#b8860b'; GRN='#2e8b57'; GREY='#555'
def arb():
    W,H=7.2,9.3; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,H-0.25,'Why LCHAI v2.0 does not arbitrate models per slide',10.5,weight='bold',w=W-0.3,h=0.4)
    c.text(W/2,H-0.58,'Four reasons why label-blind per-slide model selection is statistically ill-posed.',8.3,style='italic',color=GREY,w=W-0.3,h=0.3)
    CW=3.45
    def head(x,y,t,sub,two=False):
        if two:
            c.text(x,y-0.18,t,9,weight='bold',color=RED,ha='left',w=CW,h=0.5); c.text(x,y-0.7,sub,8,style='italic',color=GREY,ha='left',w=CW,h=0.42)
        else:
            c.text(x,y,t,9,weight='bold',color=RED,ha='left',w=CW,h=0.4); c.text(x,y-0.3,sub,8,style='italic',color=GREY,ha='left',w=CW,h=0.42)
    y0=H-0.95; xl=0.1; xr=3.75
    # R1
    head(xl,y0-0.1,'(R1) Circularity','Per-slide selection requires the ground-truth label.')
    bx,bw,bh=0.65,2.4,0.5
    yA,yB,yC=y0-1.25,y0-1.95,y0-2.65
    c.box(bx,yA,bw,bh,'Test slide arrives (label y unknown)',8,fc='#e8f0f8',ec=NAVY)
    c.box(bx,yB,bw,bh,'Choose the model whose output matches y',8,fc='#fff4d6',ec=GOLD)
    c.box(bx,yC,bw,bh,'But y is exactly what we are predicting',8,fc='#fbe9e7',ec=RED,weight='bold')
    c.arrow(bx+bw/2,yA,bx+bw/2,yB+bh,NAVY,1.6); c.arrow(bx+bw/2,yB,bx+bw/2,yC+bh,NAVY,1.6)
    c.ax.add_patch(FancyArrowPatch((bx,yC+bh/2),(bx,yA+bh/2),connectionstyle='arc3,rad=-0.45',arrowstyle='-|>',mutation_scale=11,color=RED,lw=1.6))
    c.text(xl+1.7,y0-3.2,'Any rule of the form "use the model that matches the truth" is not implementable at inference time: it is post-hoc cherry-picking.',8,style='italic',color=GREY,w=CW,h=0.6)
    # R2
    head(xr,y0-0.1,'(R2) Score incomparability','Sigmoid outputs of independently trained models are not on a common scale.')
    def nl(yy,lab,m,txt,col):
        x0,x1=xr+0.7,xr+3.0; c.ax.plot([x0,x1],[yy,yy],color=NAVY,lw=2.2)
        for xv,t in ((x0,'0'),((x0+x1)/2,'0.5'),(x1,'1')):
            c.ax.plot([xv,xv],[yy-0.07,yy+0.07],color=NAVY,lw=1.5); c.text(xv,yy-0.22,t,8)
        c.ax.plot([(x0+x1)/2]*2,[yy-0.15,yy+0.18],color='#777',ls='--',lw=1.2)
        c.ax.plot(x0+m*(x1-x0),yy,'o',color=col,ms=P(9),zorder=5); c.text(x0+m*(x1-x0),yy+0.27,txt,8,color=col)
        c.text(xr+0.32,yy,lab,8.5,w=0.6)
    nl(y0-1.5,'f_B2',0.69,'P_B2 = 0.69',GRN); nl(y0-2.2,'f_PI',0.25,'P_PI = 0.25',RED)
    c.text(xr+3.3,y0-1.85,'?',20,weight='bold',color=RED)
    c.text(xr+CW/2,y0-3.0,'Both use σ(·) > 0.5, but in different feature spaces (518-d vs 512-d) with different implicit calibration; max(P_B2, P_PI) is not a calibrated probability of any well-defined event.',8,style='italic',color=GREY,w=CW,h=0.7)
    # R3
    y2=y0-3.75
    head(xl,y2,'(R3) max-of-experts is not generally better','max(s_A, s_B) inflates scores in BOTH the mutant and wild-type cohorts.')
    hs=[Line2D([0],[0],color=NAVY,lw=2.2,label='s_A'),Line2D([0],[0],color=GOLD,lw=2.2,label='s_B'),Line2D([0],[0],color=RED,lw=2.2,label='max(s_A, s_B)')]
    c.fig.legend(handles=hs,loc='center',bbox_to_anchor=((xl+1.75)/W,(y2-0.8)/H),ncol=3,fontsize=P(8),frameon=False,handlelength=1.4,columnspacing=1)
    xs=np.linspace(0,1,300); g=lambda m,s:np.exp(-0.5*((xs-m)/s)**2)
    for i,(ttl,ma,mb,mm,cap) in enumerate([('Mutant cohort',.55,.42,.63,'max shifts right: recovers some false negatives'),('Wild-type cohort',.35,.25,.47,'max shifts right: creates new false positives')]):
        x=xl+0.05+i*1.75; ax=c.fig.add_axes([x/W,(y2-2.3)/H,1.6/W,0.95/H])
        ax.fill_between(xs,g(ma,.11),color=NAVY,alpha=.18,lw=0); ax.plot(xs,g(ma,.11),color=NAVY,lw=P(1.6))
        ax.fill_between(xs,g(mb,.11),color=GOLD,alpha=.25,lw=0); ax.plot(xs,g(mb,.11),color=GOLD,lw=P(1.6))
        ax.plot(xs,g(mm,.085),color=RED,lw=P(1.8)); ax.axvline(.5,color='#777',ls='--',lw=P(1))
        ax.set_xlim(0,1); ax.set_ylim(0,1.12); ax.set_yticks([]); ax.set_xticks([.5]); ax.tick_params(labelsize=P(8))
        for s_ in ('top','right','left'): ax.spines[s_].set_visible(False)
        c.text(x+0.8,y2-1.1,ttl,8,weight='bold'); c.text(x+0.8,y2-2.95,cap,8,style='italic',color=NAVY,w=1.65,h=0.5)
    c.text(xl+1.7,y2-3.65,'Net effect on cross-validated AUROC is empirical and frequently negative, especially for low-prevalence genes (e.g. KEAP1: 14.3% mutation rate).',8,style='italic',color=GREY,w=CW,h=0.65)
    # R4
    head(xr,y2,'(R4) Per-slide variance is what\nAUROC already integrates','5-fold CV AUROC = expected ranking quality; per-slide gaps are noise.',two=True)
    rng=np.random.default_rng(42); n=14; b2=rng.uniform(.10,.85,size=n); pi=np.clip(b2+rng.normal(.05,.18,size=n),.05,.95)
    ax=c.fig.add_axes([(xr+0.4)/W,(y2-2.95)/H,3.0/W,1.25/H]); i=np.arange(n)
    for a,b,j in zip(b2,pi,i): ax.plot([j,j],[a,b],color='#ccc',lw=P(1.2),zorder=1)
    ax.plot(i,b2,'o',color=NAVY,ms=P(6),zorder=3); ax.plot(i,pi,'s',color=RED,ms=P(6),zorder=3)
    ax.axhline(.5,color='#666',ls='--',lw=P(1)); ax.axhline(b2.mean(),color=NAVY,lw=P(1.2),alpha=.6); ax.axhline(pi.mean(),color=RED,lw=P(1.2),alpha=.6)
    ax.set_xlim(-0.7,n-0.3); ax.set_ylim(0,1.02); ax.set_yticks([0,.5,1]); ax.set_xticks([]); ax.tick_params(labelsize=P(8)); ax.set_xlabel('slides (cohort)',fontsize=P(8),color=GREY)
    hs=[Line2D([0],[0],marker='o',ls='',color=NAVY,label='P_B2'),Line2D([0],[0],marker='s',ls='',color=RED,label='P_PI-ABMIL'),Line2D([0],[0],color=NAVY,alpha=.6,lw=1.5,label='mean P_B2'),Line2D([0],[0],color=RED,alpha=.6,lw=1.5,label='mean P_PI')]
    c.fig.legend(handles=hs,loc='center',bbox_to_anchor=((xr+1.75)/W,(y2-1.3)/H),ncol=2,fontsize=P(8),frameon=False,columnspacing=0.6,handletextpad=0.2,handlelength=1.2)
    c.text(xr+CW/2,y2-3.85,'On any single slide either model can win; cohort AUROC integrates this spread. Choosing the per-gene best-in-expectation model minimises misranking risk.',8,style='italic',color=GREY,w=CW,h=0.65)
    print('bottom',y2-4.2)
    c.save(OUT+'per_slide_arbitration_fails.png'); print(audit(c.fig))
arb()
