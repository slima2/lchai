from fx import *
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyArrowPatch
OUT='../man_out/'
NAVY='#1b3a5c'; RED='#c0392b'; PUR='#8e44ad'; GRY='#7f8c8d'; BLU='#2e86c1'; GRN='#27ae60'; ORG='#e8a02c'; TEAL='#1abc9c'
TAU=0.448; M=0.518

def mk(H,minpt=8.0):
    c=Canvas(7.2,H,minpt=minpt); k=c.k; P=lambda p:p/k
    def AX(l,b,w,h):
        ax=c.fig.add_axes([l/7.2,b/H,w/7.2,h/H])
        ax.tick_params(labelsize=P(8.5),length=P(3),width=P(.8)); ax.grid(alpha=.2,lw=P(.6))
        for s in ax.spines.values(): s.set_linewidth(P(.9))
        return ax
    return c,P,AX
def title(ax,P,t): ax.set_title(t,fontsize=P(9.5),fontweight='bold',pad=P(6))
def bx(ax,P,x,y,t,col,fc='white',ha='center',va='center',fs=8,**kw):
    return ax.text(x,y,t,fontsize=P(fs),ha=ha,va=va,color='#222',bbox=dict(fc=fc,ec=col,boxstyle='round,pad=0.25',lw=P(.9)),zorder=7,**kw)
def regions(ax,x0=0,x1=1,ylo=-5,yhi=5):
    ax.axvspan(x0,TAU,color='#fdeeee',zorder=0); ax.axvspan(TAU,x1,color='#e9f7ef',zorder=0)
    ax.axvline(TAU,color='#999',ls=':',lw=0.8,zorder=1)

# ------------------------------------------------------------------ combined loss
def combined():
    H=10.4; c,P,AX=mk(H)
    # (a)
    top=H-0.25; a=AX(0.95,top-0.4-1.7,6.0,1.7); title(a,P,'(a) Target distribution: one-hot vs smoothed (acinar tile, correct class = acinar)')
    cls=['Lepidic','Acinar','Papillary','Micropap.','Solid','Cribriform']; x=np.arange(6)
    oh=np.array([0,1,0,0,0,0.]); sm=np.where(x==1,1-0.1+0.1/6,0.1/6)
    a.bar(x[1]-0.21,1.0,0.42,color='#6bb3e3',label='One-hot target',zorder=3)
    a.bar(x+0.21,sm,0.42,color='#ee7b6c',label='Smoothed (ε = 0.1)',zorder=3)
    a.text(x[1]-0.21,1.03,'1.0',fontsize=P(8),ha='center',color='#2c7fb8')
    for i in range(6): a.text(x[i]+0.21,sm[i]+0.03,('0.917' if i==1 else '0.017'),fontsize=P(8),ha='center',color='#c0392b')
    a.set_xticks(x); a.set_xticklabels(cls,fontsize=P(8.5)); a.set_ylim(0,1.45); a.set_xlim(-0.6,5.6); a.set_yticks([0,.5,1.0]); a.set_ylabel('Target probability',fontsize=P(9))
    a.legend(fontsize=P(8.5),loc='upper right',frameon=True,framealpha=.95)
    # (b),(c)
    yb=top-0.4-1.7-0.3-0.1-0.5-2.4
    b=AX(0.9,yb,2.6,2.4); title(b,P,'(b) Loss functions for\ncorrect class')
    p=np.linspace(0.01,0.992,600); ce=-np.log(p); K=6; e=0.1
    ls=-(1-e+e/K)*np.log(p)-(e/K)*(K-1)*np.log(1-p); fo=-(1-p)**2*np.log(p); co=0.6*ls+0.4*fo
    b.axvspan(0,0.3,color='#fdeeee',zorder=0); b.axvspan(0.7,1,color='#e9f7ef',zorder=0)
    b.plot(p,ce,'--',color=GRY,lw=P(1.5),label='Standard CE'); b.plot(p,ls,color=BLU,lw=P(1.9),label='Label-smoothed CE (ε = 0.1)')
    b.plot(p,fo,color='#e04b3a',lw=P(1.9),label='Focal loss (γ = 2)'); b.plot(p,co,color=PUR,lw=P(1.9),label='Combined (α = 0.6)')
    b.set_xlim(0,1); b.set_ylim(0,4.5); b.set_xlabel('Predicted probability p of correct class',fontsize=P(9)); b.set_ylabel('Loss value',fontsize=P(9))
    b.legend(fontsize=P(8),loc='upper right',frameon=True,framealpha=.95,handlelength=1.3,borderpad=0.4,labelspacing=0.3)
    b.text(0.15,0.2,'hard',fontsize=P(8),style='italic',color='#c0392b',ha='center'); b.text(0.85,1.1,'easy\nsamples',fontsize=P(8),style='italic',color='#27ae60',ha='center')
    cc=AX(4.4,yb,2.6,2.4); title(cc,P,'(c) Focal modulating factor\n(1 − p)$^{\\gamma}$ with γ = 2')
    cc.axvspan(0,0.3,color='#fdeeee',zorder=0); cc.axvspan(0.7,1,color='#e9f7ef',zorder=0)
    pp=np.linspace(0,1,300); cc.plot(pp,np.ones_like(pp),'--',color=GRY,lw=P(1.5),label='CE weight = 1'); cc.plot(pp,(1-pp)**2,color='#e04b3a',lw=P(2),label='Focal (1 − p)², γ = 2')
    cc.fill_between(pp,(1-pp)**2,1,color='#f5b7b1',alpha=.35,lw=0,label='Down-weighted')
    cc.set_xlim(0,1); cc.set_ylim(0,1.12); cc.set_xlabel('Predicted probability p of correct class',fontsize=P(9)); cc.set_ylabel('Loss weight multiplier',fontsize=P(9))
    cc.legend(fontsize=P(8),loc='upper right',bbox_to_anchor=(1,0.9),frameon=True,framealpha=.95,handlelength=1.3,borderpad=0.4,labelspacing=0.3)
    cc.annotate('p = 0.2:\nweight 0.64\n(36% lower)',xy=(0.2,0.64),xytext=(0.2,0.2),fontsize=P(8),ha='center',va='center',bbox=dict(fc='#fff4d6',ec=ORG,boxstyle='round,pad=0.25',lw=P(.9)),arrowprops=dict(arrowstyle='-|>',color='#333',lw=P(1)),zorder=8)
    cc.annotate('p = 0.9:\nweight 0.01\n(99% lower)',xy=(0.9,0.01),xytext=(0.7,0.36),fontsize=P(8),ha='center',va='center',bbox=dict(fc='#fff4d6',ec=ORG,boxstyle='round,pad=0.25',lw=P(.9)),arrowprops=dict(arrowstyle='-|>',color='#333',lw=P(1)),zorder=8)
    # (d)
    ytitle=yb-0.7-0.05
    c.text(3.6,ytitle,'(d) Combined effect in the FuzzyArcLoss V2 pipeline',9.5,weight='bold',w=7.0,h=0.3)
    yy=ytitle-0.2
    # flow boxes (inches)
    n1y=yy-0.3
    c.text(4.05,n1y,'Prevents overconfidence (softens 1.0 to 0.917)',8,style='italic',color='#1e8449',w=2.9,h=0.42)
    ceY=n1y-0.21-0.55; c.box(3.0,ceY,2.1,0.55,'α · L_CE-smooth\nε = 0.1, α = 0.6',8,fc='#d6eaf8',ec=BLU)
    foY=ceY-0.2-0.55; c.box(3.0,foY,2.1,0.55,'(1 − α) · L_focal\nγ = 2, (1 − α) = 0.4',8,fc='#f9d6d2',ec='#e04b3a')
    n2y=foY-0.3
    c.text(4.05,n2y,'Down-weights easy samples (99% reduction at p = 0.9)',8,style='italic',color='#1e8449',w=2.9,h=0.42)
    mid=(ceY+foY+0.55)/2
    lgY=mid-0.3; c.box(0.25,lgY,1.9,0.6,'Modulated logits s · z̃',8,fc='#d6eaf8',ec=BLU)
    mgY=lgY-0.3-0.6; c.box(0.25,mgY,1.9,0.6,'FuzzyArcLoss V2 margin modulation',8,fc='#fff4d6',ec=ORG,style='italic')
    c.arrow(1.2,mgY+0.6,1.2,lgY,ORG,1.3)
    c.arrow(2.2,lgY+0.3+0.1,2.95,ceY+0.275,'#2c3e50',1.3); c.arrow(2.2,lgY+0.3-0.1,2.95,foY+0.275,'#2c3e50',1.3)
    c.box(5.85,mid-0.3,1.1,0.6,'L_combined',8,fc='#ebdef0',ec=PUR)
    c.arrow(5.15,ceY+0.275,5.8,mid+0.1,'#2c3e50',1.3); c.arrow(5.15,foY+0.275,5.8,mid-0.1,'#2c3e50',1.3)
    sy=n2y-0.3-0.95
    c.ax.add_patch(FancyBboxPatch((0.25,sy),6.7,0.95,boxstyle='round,pad=0,rounding_size=0.08',fc='white',ec=NAVY,lw=1.3))
    c.text(3.6,sy+0.47,'Three complementary mechanisms:\n1. Fuzzy margin: reduces the penalty for ambiguous tiles\n2. Label smoothing: prevents overconfident predictions\n3. Focal loss: up-weights minority classes (cribriform, micropapillary)',8,w=6.6,h=0.92)
    print('combined bottom',sy)
    c.save(OUT+'fuzzyarcloss_v2_combined_loss.png'); print(audit(c.fig))

# ------------------------------------------------------------------ gradient decomposition
def grad():
    H=10.1; c,P,AX=mk(H)
    cs=np.linspace(0.004,0.99,900)
    th=np.arccos(cs); phi=np.cos(th+M); dphi=np.sin(th+M)/np.sin(th)
    mu=np.where(cs>=TAU,0.8+0.2*cs,0.3+0.4*cs); dmu=np.where(cs>=TAU,0.2,0.4)
    t1=mu*dphi; t2=1-mu; t3=(phi-cs)*dmu
    top=H-0.25
    def sh(ax):
        ax.axvspan(0,TAU,color='#fdeeee',zorder=0); ax.axvspan(TAU,1,color='#e9f7ef',zorder=0); ax.axvline(TAU,color='#999',ls=':',lw=0.9,zorder=1)
        ax.set_xlim(0,1); ax.set_xlabel('c = cos θ  (cosine similarity to own prototype)',fontsize=P(9))
    def seg(ax,y,**kw):
        lo=cs<TAU; ax.plot(cs[lo],y[lo],**kw); kw.pop('label',None); ax.plot(cs[~lo],y[~lo],**kw)
    a=AX(0.95,top-0.35-2.7,6.0,2.7); sh(a); title(a,P,'(a) The three gradient terms (Eq. 4.10)')
    seg(a,t1,color=BLU,lw=P(2),label='(i) μ ∂φ/∂c'); seg(a,t2,color=GRN,lw=P(2),label='(ii) (1 − μ)'); seg(a,t3,color='#e04b3a',lw=P(2),label='(iii) (φ − c) ∂μ/∂c')
    a.set_ylim(-0.5,3.5); a.set_ylabel('Gradient contribution',fontsize=P(9)); a.legend(fontsize=P(8.5),loc='upper left',frameon=True,framealpha=.95)
    a.text(0.22,-0.38,'low confidence',fontsize=P(8),style='italic',color='#c0392b',ha='center'); a.text(0.72,-0.38,'high confidence (c ≥ τ = 0.448)',fontsize=P(8),style='italic',color='#1e8449',ha='center')
    b=AX(0.95,top-0.35-2.7-0.5-0.35-2.4,6.0,2.4); sh(b); title(b,P,'(b) Total gradient: V2 vs standard ArcFace')
    tot=t1+t2+t3
    seg(b,tot,color=PUR,lw=P(2.2),label='FuzzyArcLoss V2 (total)'); b.plot(cs,dphi,'--',color=GRY,lw=P(2),label='Standard ArcFace (μ = 1)')
    b.fill_between(cs,tot,dphi,where=dphi>tot,color=PUR,alpha=.15,lw=0,label='Reduced gradient (ambiguous tiles)')
    b.set_ylim(-0.5,3.5); b.set_ylabel('$\\partial\\tilde{z}/\\partial c$',fontsize=P(10)); b.legend(fontsize=P(8.5),loc='upper left',frameon=True,framealpha=.95)
    cc=AX(0.95,top-0.35-2.7-0.5-0.35-2.4-0.5-0.35-2.2,6.0,2.2); sh(cc); title(cc,P,'(c) Effective margin strength')
    eff=mu*(phi-cs); seg(cc,eff,color=PUR,lw=P(2.2),label='V2: μ (φ − c)'); cc.plot(cs,phi-cs,'--',color=GRY,lw=P(2),label='ArcFace: φ − c')
    cc.fill_between(cs,eff,phi-cs,where=eff>phi-cs,color='#e74c3c',alpha=.2,lw=0,label='Margin reduction')
    cc.axhline(0,color='#555',lw=0.8); cc.set_ylim(-1.15,0.12); cc.set_ylabel('Effective margin penalty',fontsize=P(9)); cc.legend(fontsize=P(8.5),loc='lower left',frameon=True,framealpha=.95)
    print('grad bottom', top-0.35-2.7-0.5-0.35-2.4-0.5-0.35-2.2-0.5)
    c.save(OUT+'fuzzyarcloss_v2_gradient_decomposition.png'); print(audit(c.fig))

# ------------------------------------------------------------------ coefficient rationale
def coeff():
    H=10.2; c,P,AX=mk(H)
    top=H-0.25
    def sh(ax,ylab,xl=True):
        ax.axvspan(0,TAU,color='#fdeeee',zorder=0); ax.axvspan(TAU,1,color='#e9f7ef',zorder=0); ax.axvline(TAU,color='#999',ls=':',lw=0.9,zorder=1)
        ax.set_xlim(0,1); ax.set_ylabel(ylab,fontsize=P(9)); ax.set_xlabel('|cos θ|  (classification confidence)',fontsize=P(9))
    xl=np.linspace(0,TAU,50); xh=np.linspace(TAU,1,50)
    # (a)
    a=AX(0.95,top-0.35-2.8,6.0,2.8); sh(a,'μ (fuzzy membership)'); title(a,P,'(a) Design constraints on the membership function μ')
    a.plot(xl,0.3+0.4*xl,color=PUR,lw=P(2.4),label='FuzzyArcLoss V2'); a.plot(xh,0.8+0.2*xh,color=PUR,lw=P(2.4))
    a.plot([0,TAU],[1,1],'--',color='#999',lw=P(1.5),label='FuzzyArcLoss V1'); a.plot([TAU,TAU],[1,TAU],'--',color='#999',lw=P(1.5)); a.plot(xh,xh,'--',color='#999',lw=P(1.5))
    a.plot([0,TAU],[0.8,0.8],':',color=BLU,lw=P(1.3)); a.plot([0],[0.3],'o',color='#e04b3a',ms=P(8),zorder=6,clip_on=False)
    a.set_ylim(0,1.2); a.set_yticks([0,.2,.4,.6,.8,1.0])
    a.text(0.01,0.84,'P1: a_H = 0.8 (80% floor)',fontsize=P(8),color=BLU,ha='left',va='bottom')
    a.text(0.03,0.16,'P2: a_L = 0.3 (30% floor)',fontsize=P(8),color='#c0392b',ha='left',va='center')
    a.annotate('',xy=(TAU,0.8896),xytext=(TAU,0.479),arrowprops=dict(arrowstyle='<|-|>',color=ORG,lw=P(1.4)),zorder=6)
    bx(a,P,TAU+0.02,0.68,'Gap = 0.41',ORG,ha='left')
    a.text(0.72,1.06,'b_H = 0.2',fontsize=P(8),color=PUR,ha='center'); 
    bx(a,P,0.86,0.5,'a_H + b_H = 1',GRN)
    a.annotate('',xy=(0.9,0.9),xytext=(0.87,0.55),arrowprops=dict(arrowstyle='-|>',color=GRN,lw=P(1.1)),zorder=6)
    a.text(0.5*TAU,1.13,'low confidence',fontsize=P(8),style='italic',color='#c0392b',ha='center'); a.text(0.74,1.13,'high confidence',fontsize=P(8),style='italic',color='#1e8449',ha='center')
    a.text(TAU+0.01,0.03,'τ = 0.448',fontsize=P(8),color='#555',ha='left')
    a.legend(fontsize=P(8.5),loc='lower right',frameon=True,framealpha=.95)
    # (b)
    b=AX(0.95,top-0.35-2.8-0.5-0.35-2.5,6.0,2.5); sh(b,'μ'); title(b,P,'(b) Why alternative coefficients fail')
    b.plot(xl,0.3+0.4*xl,color=PUR,lw=P(2.4),label='V2 chosen (0.8 / 0.2 / 0.3 / 0.4)'); b.plot(xh,0.8+0.2*xh,color=PUR,lw=P(2.4))
    b.plot(xh,0.5+0.5*xh,'--',color='#5dade2',lw=P(1.7),label='a_H = 0.5: under-penalises')
    b.plot(xl,0.4*xl,'-.',color='#e74c3c',lw=P(1.7),label='a_L = 0: softmax collapse')
    b.plot(xl,0.3+0.2*xl,':',color='#f5a623',lw=P(2),label='b_L = b_H: no differential')
    b.plot(xl,0.3+0.6*xl,'--',color=TEAL,lw=P(1.7),label='b_L = 3 b_H: erodes gap')
    b.set_ylim(0,1.15); b.set_yticks([0,.2,.4,.6,.8,1.0])
    b.text(0.14,0.185,'softmax collapse',fontsize=P(8),color='#c0392b',ha='center')
    bx(b,P,0.6,0.64,'gap eroded',TEAL)
    b.legend(fontsize=P(8.2),loc='upper left',frameon=True,framealpha=.95,handlelength=2.2,labelspacing=0.35)
    # (c)
    cc=AX(0.95,top-0.35-2.8-0.5-0.35-2.5-0.5-0.35-2.1,6.0,2.1); sh(cc,'∂μ/∂|cos θ|'); title(cc,P,'(c) P3: doubled gradient for ambiguous tiles')
    d=lambda lo,hi,col,ls,lw,lab=None:(cc.plot([0,TAU],[lo,lo],ls,color=col,lw=P(lw),label=lab),cc.plot([TAU,1],[hi,hi],ls,color=col,lw=P(lw)))
    d(0.6,0.2,TEAL,'--',1.7,'b_L = 3 b_H (too aggressive)'); d(0.2,0.2,'#f5a623',':',2,'b_L = b_H (no benefit)'); d(0.4,0.2,PUR,'-',2.4,'V2: b_L = 2 b_H (chosen)')
    cc.plot([TAU,TAU],[0.2,0.4],color=PUR,lw=P(2.4))
    cc.set_ylim(0,0.8); cc.set_yticks([0,.2,.4,.6])
    cc.annotate('',xy=(0.2,0.4),xytext=(0.2,0.2),arrowprops=dict(arrowstyle='<|-|>',color=PUR,lw=P(1.4)),zorder=6); cc.text(0.23,0.3,'2 ×',fontsize=P(10),fontweight='bold',color=PUR,va='center')
    cc.text(0.5*TAU,0.74,'ambiguous tiles',fontsize=P(8),style='italic',color='#c0392b',ha='center')
    cc.legend(fontsize=P(8.5),loc='upper right',bbox_to_anchor=(1,0.97),frameon=True,framealpha=.95)
    print('coeff bottom',top-0.35-2.8-0.5-0.35-2.5-0.5-0.35-2.1-0.5)
    c.save(OUT+'fuzzyarcloss_v2_coefficient_rationale.png'); print(audit(c.fig))

# ------------------------------------------------------------------ choquet interpretability
def choq():
    H=10.4; c,P,AX=mk(H)
    PAT=['Cribri.','Solid','Acinar','Lepidic','Micropap.','Papillary']
    top=H-0.25
    a=AX(0.95,top-0.4-1.9,6.0,1.9); title(a,P,'(a) Singleton Shapley values (real data, Ch. 6)')
    kr=[0.170,0.168,0.167,0.165,0.165,0.165]; rb=[0.167,0.167,0.167,0.166,0.166,0.166]; un=1/6
    x=np.arange(6); w=0.27
    a.bar(x-w,[un]*6,w,color='#b8bec4',label='Uniform (1/6)',zorder=3); a.bar(x,kr,w,color=PUR,label='KRAS (learned)',zorder=3); a.bar(x+w,rb,w,color='#e67e22',label='RBM10 (learned)',zorder=3)
    a.axhline(un,color='#999',ls='--',lw=P(1),zorder=4)
    a.set_ylim(0.160,0.1795); a.set_xlim(-0.55,5.55); a.set_yticks([0.160,0.165,0.170]); a.set_xticks(x); a.set_xticklabels(PAT,fontsize=P(8.5))
    a.set_ylabel('Shapley value φ\n(axis starts at 0.160)',fontsize=P(8.5)); a.grid(axis='x',alpha=0)
    for i,v in enumerate(kr):
        dlt=(v-un)*100; a.text(i,0.1722,f'KRAS {dlt:+.1f}%'.replace('-','−'),fontsize=P(8),color=PUR,ha='center',va='center')
    a.text(2.5,0.1752,'Both profiles are “Uniform” (all deviations < 0.5%)',fontsize=P(8),style='italic',color='#333',ha='center',va='center')
    a.legend(fontsize=P(8.5),loc='upper center',ncol=3,frameon=False,borderaxespad=0.2)
    # heatmaps
    cmap=plt.get_cmap('RdBu'); vm=0.035
    rows=PAT[1:]; cols=PAT[:5]
    kras={(1,0):-0.006,(2,0):-0.019,(2,1):0.025,(3,0):-0.006,(3,1):0.032,(3,2):0.002,(4,0):-0.025,(4,1):-0.002,(4,2):0.004,(4,3):0.003,(5,0):-0.022,(5,1):-0.004,(5,2):0.001,(5,3):-0.001,(5,4):0.007}
    rbm={(1,0):-0.004,(2,0):0.0,(2,1):0.0,(3,0):0.003,(3,1):0.0,(3,2):0.0,(4,0):-0.003,(4,1):0.0,(4,2):0.0,(4,3):0.003,(5,0):0.0,(5,1):0.0,(5,2):0.0,(5,3):0.008,(5,4):0.0}
    cs=0.5
    ytop=top-0.4-1.9-0.35-0.8   # top of matrix area (below 2-line titles)
    def hm(x0,data,ttl,flag):
        c.text(x0+0.8+cs*2.5,ytop+0.4,ttl,9.5,weight='bold',w=3.4,h=0.5)
        for (i,j),v in data.items():
            r=i-1; col=cmap(0.5+0.5*(v/vm))
            yb=ytop-(r+1)*cs; xb=x0+0.8+j*cs
            c.ax.add_patch(Rectangle((xb,yb),cs,cs,fc=col,ec='white',lw=1.0))
            lab=f'{v:+.3f}'.replace('-','−'); tcol='white' if abs(v)>=0.02 else '#222'
            if flag and abs(v)>=0.02: lab+='\nMod '+('↑' if v>0 else '↓')
            c.text(xb+cs/2,yb+cs/2,lab,8,color=tcol,weight=('bold' if abs(v)>=0.02 and flag else 'normal'))
        for r,n in enumerate(rows): c.text(x0+0.75,ytop-(r+0.5)*cs,n,8.5,ha='right')
        for j,n in enumerate(cols): c.ax.text(x0+0.8+(j+0.5)*cs+0.05,ytop-5*cs-0.08,n,fontsize=c.fs(8.5),rotation=40,ha='right',va='top',rotation_mode='anchor')
    hm(0.15,kras,'(b) KRAS interactions: structured\n(Lepidic × Solid = Mod ↑)',True)
    hm(3.65,rbm,'(c) RBM10 interactions: flat\n(all near zero)',False)
    ycb=ytop-5*cs-0.98
    cax=c.fig.add_axes([1.6/7.2,ycb/H,4.0/7.2,0.16/H]); g=np.linspace(-vm,vm,256)[None,:]
    cax.imshow(g,aspect='auto',cmap=cmap.reversed() if False else plt.get_cmap('RdBu'),extent=[-vm,vm,0,1]); cax.set_yticks([]); cax.set_xticks([-0.03,-0.02,-0.01,0,0.01,0.02,0.03]); cax.set_xticklabels(['−0.03','−0.02','−0.01','0','+0.01','+0.02','+0.03'],fontsize=c.fs(8))
    cax.tick_params(length=2)
    c.text(3.6,ycb-0.42,'Interaction index I(j,k)   (red = redundancy, blue = synergy)',8.5,w=6.0,h=0.25)
    # (d)
    yd=ycb-0.42-0.4
    c.text(3.6,yd,'(d) Reading Choquet parameters with fuzzy linguistic labels',9.5,weight='bold',w=7.0,h=0.3)
    items=[('Shapley profile classification','#8e44ad','#f4ecf7','“Uniform”: all φ ≈ 1/6 (KRAS, RBM10)\n“Differentiated”: one φ ≫ 1/6\n“Polarised”: strong deviation'),
           ('Interaction fuzzy labels','#27ae60','#e4f6ea','“Moderate ↑”: I > +0.02 (supra-additive)\n“Moderate ↓”: I < −0.02 (sub-additive)\n“Negligible”: |I| < 0.005'),
           ('Clinical reading','#d68910','#fdf3dc','KRAS: uniform singletons + structured interactions ⇒ co-occurrence matters\nRBM10: uniform + flat ⇒ no pattern signal'),
           ('Key distinction','#c0392b','#fbe3e0','SHAP (post-hoc, 518-d) ≠ Choquet Shapley (intrinsic, 21 params)')]
    bw,bh=3.4,0.95
    for i,(h_,ec,fc,t) in enumerate(items):
        xx=0.15+(i%2)*3.55; yy=yd-0.25-bh-(i//2)*(bh+0.12)
        c.ax.add_patch(FancyBboxPatch((xx,yy),bw,bh,boxstyle='round,pad=0,rounding_size=0.06',fc=fc,ec=ec,lw=1.2))
        c.text(xx+bw/2,yy+bh-0.15,h_,8.5,weight='bold',color=ec,w=bw,h=0.3)
        c.text(xx+bw/2,yy+(bh-0.28)/2,t,8,w=bw-0.1,h=bh-0.3)
    print('choq bottom',yd-0.25-2*bh-0.12)
    c.save(OUT+'choquet_interpretability.png'); print(audit(c.fig))
combined(); grad(); coeff(); choq()
