from fx import *
import numpy as np
from matplotlib.patches import FancyBboxPatch
OUT='../man_out/'
GREY='#666'
def mkh(c):
    def bx(x,y,w,h,fc,ec,lw=1.6,ls='-'):
        c.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=0.09',fc=fc,ec=ec,lw=lw,ls=ls,zorder=1))
    def T(x,y,t,p=8.5,**kw):
        kw.setdefault('color','#222'); return c.ax.text(x,y,t,fontsize=c.fs(p),ha=kw.pop('ha','center'),va=kw.pop('va','center'),zorder=5,**kw)
    def ln(pts,col,lw=1.4,ls='-',arrow=False):
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        if arrow and len(pts)>2: c.ax.plot(xs[:-1],ys[:-1],color=col,lw=lw,ls=ls,zorder=2,solid_capstyle='butt')
        if arrow: c.arrow(pts[-2][0],pts[-2][1],pts[-1][0],pts[-1][1],col,lw)
        else: c.ax.plot(xs,ys,color=col,lw=lw,ls=ls,zorder=2)
    def el(x,y,t,p=8,col='#444'):
        return c.ax.text(x,y,t,fontsize=c.fs(p),ha='center',va='center',color=col,style='italic',zorder=6,bbox=dict(fc='white',ec='none',pad=1.5))
    return bx,T,ln,el

def abmil():
    W,H=7.2,9.3; c=Canvas(W,H,minpt=8.0); bx,T,ln,el=mkh(c)
    T(W/2,H-0.28,'ABMIL Architecture (Artefact 2: PI-ABMIL)',11,weight='bold',color='#2c3e50')
    c.text(W/2,H-0.62,'Shared by conditions B2, B3, PI-ABMIL, and A  (FC-MIL adds a parallel Choquet branch)',8,style='italic',color=GREY,w=6.9,h=0.4)
    X,Wd=0.9,5.6; cx=X+Wd/2
    # input
    y=H-1.75; bx(X,y,Wd,0.85,'#eaf3fb','#2e86c1')
    T(cx,y+0.62,'Input: tile embeddings  $\\mathbf{h}_i$',9.5,weight='bold')
    T(cx,y+0.38,'Input dim.:  B1: 7   B2: 512   B3: 6   PI: 518   A: 518   FC: 512+6',8,color='#444')
    T(cx,y+0.15,'(Module 1: Encoder)',8,color='#2e86c1',style='italic')
    # module 1
    y1=y-1.45; bx(X,y1,Wd,1.0,'#d6e9f8','#1f6aa5')
    T(cx,y1+0.8,'Tile-Level Transformation',10,weight='bold')
    T(cx,y1+0.5,"$\\mathbf{h}'_i=\\mathrm{ReLU}(\\mathbf{W}_2\\cdot\\mathrm{ReLU}(\\mathbf{W}_1\\mathbf{h}_i+\\mathbf{b}_1)+\\mathbf{b}_2)\\in\\mathbb{R}^{256}$",9)
    T(cx,y1+0.2,'Dropout p = 0.25 after each ReLU   (Eq. 4.20)',8,color=GREY)
    ln([(cx,y),(cx,y1+1.0)],'#2c3e50',1.6,arrow=True)
    # module 2
    y2=y1-1.75; bx(X,y2,Wd,1.15,'#fef6e0','#f39c12')
    T(cx,y2+0.95,'Module 2: Gated Attention Mechanism',10,weight='bold')
    T(cx,y2+0.66,"$a_i=\\mathrm{softmax}(\\mathbf{w}^{\\top}(\\tanh(\\mathbf{V}\\mathbf{h}'_i)\\odot\\sigma(\\mathbf{U}\\mathbf{h}'_i)))$",9)
    T(cx,y2+0.38,'$\\mathbf{V},\\mathbf{U}\\in\\mathbb{R}^{128\\times256},\\ \\mathbf{w}\\in\\mathbb{R}^{128},\\ \\sigma$ = sigmoid   (Eq. 4.21)',8,color=GREY)
    T(cx,y2+0.14,'Gating (σ) suppresses irrelevant tiles',8,color='#b9770e',style='italic')
    ln([(cx,y1),(cx,y2+1.15)],'#2c3e50',1.6,arrow=True); el(cx+0.45,(y1+y2+1.15)/2,"$\\mathbf{h}'_i$",8.5)
    # module 3
    y3=y2-1.25; bx(X,y3,Wd,0.9,'#d5f5e3','#27ae60')
    T(cx,y3+0.7,'Module 3: Attention-Weighted Sum',10,weight='bold')
    T(cx,y3+0.4,"$\\mathbf{z}_s=\\sum_i a_i\\mathbf{h}'_i\\in\\mathbb{R}^{256}$   (Eq. 4.22)",9)
    ln([(cx+1.2,y2),(cx+1.2,y3+0.9)],'#2c3e50',1.6,arrow=True); el(cx+1.5,(y2+y3+0.9)/2,'$a_i$',8.5,'#e67e22')
    # skip h'
    ln([(X,y1+0.5),(0.35,y1+0.5),(0.35,y3+0.45),(X,y3+0.45)],'#999',1.2,ls='--',arrow=True)
    el(0.35,(y1+y3)/2,"$\\mathbf{h}'_i$",8.5,'#777')
    # classifier row
    y4=y3-1.4; wc=3.7; bx(X,y4,wc,1.0,'#f4ecf7','#8e44ad')
    T(X+wc/2,y4+0.8,'Linear Classifier (per gene g)',10,weight='bold')
    T(X+wc/2,y4+0.45,"$\\hat{Y}^{(g)}_s=\\sigma(\\mathbf{w}_g^{\\top}\\mathbf{z}_s+b_g)$   (Eq. 4.23)",9)
    ln([(X+wc/2,y3),(X+wc/2,y4+1.0)],'#2c3e50',1.6,arrow=True); el(X+wc/2+0.35,(y3+y4+1.0)/2,'$\\mathbf{z}_s$',8.5,'#27ae60')
    xp=X+wc+0.45; wp=X+Wd-xp; bx(xp,y4+0.15,wp,0.7,'#e8daef','#8e44ad')
    T(xp+wp/2,y4+0.62,'P(mut)',9.5,weight='bold'); T(xp+wp/2,y4+0.34,'∈ [0, 1]',8,color=GREY)
    ln([(X+wc,y4+0.5),(xp,y4+0.5)],'#2c3e50',1.6,arrow=True)
    # loss
    y5=y4-1.55; bx(X+0.9,y5,Wd-0.9,1.0,'#fadbd8','#e74c3c')
    lx=X+0.9+(Wd-0.9)/2
    T(lx,y5+0.8,'Binary Cross-Entropy Loss',10,weight='bold',color='#c0392b')
    T(lx,y5+0.45,"$\\mathcal{L}^{(g)}_{\\mathrm{BCE}}=-\\frac{1}{|S|}\\sum_s[Y_s\\log\\hat{Y}_s+(1-Y_s)\\log(1-\\hat{Y}_s)]$",8.5)
    T(lx,y5+0.14,'(Eq. 4.24)',8,color=GREY)
    ln([(X+wc/2,y4),(X+wc/2,y5+1.0)],'#e74c3c',1.5,arrow=True); el(X+wc/2+0.45,(y4+y5+1.0)/2,'$\\hat{Y}^{(g)}_s$',8.5,'#c0392b')
    bx(0.2,y5+0.2,0.7,0.6,'#f4f6f6','#aab7b8',lw=1.0)
    T(0.55,y5+0.5,'$Y_s^{(g)}$',8.5); ln([(0.9,y5+0.5),(X+0.9,y5+0.5)],'#7f8c8d',1.3,arrow=True)
    
    T(0.55,y5+0.05,'MAF label',8,color=GREY)
    c.save(OUT+'abmil_architecture.png'); print('abmil',W,H,audit(c.fig))

def fcmil():
    W,H=7.2,10.45; c=Canvas(W,H,minpt=8.0); bx,T,ln,el=mkh(c)
    T(W/2,H-0.28,'FC-MIL: Fuzzy Choquet MIL (Artefact 3)',11,weight='bold',color='#2c3e50')
    c.text(W/2,H-0.6,'Dual-pathway: embedding attention + Choquet pattern interactions',8,style='italic',color=GREY,w=6.9,h=0.4)
    ya=H-1.65; bx(0.3,ya,6.6,0.85,'#fef3cd','#d4a017')
    T(W/2,ya+0.63,'Artefact 1 Output (FuzzyArcLoss V2 Pattern Classifier)',10,weight='bold',color='#b8860b')
    T(W/2,ya+0.3,'Per tile i:  $\\mathbf{x}_i\\in\\mathbb{R}^{512}$ (CTransPath embedding)  +  $\\mathbf{p}_i\\in\\Delta^5$ (6-d fuzzy pattern probs)',8.5)
    LX,LW,RX,RW=0.2,3.15,3.85,3.15; lc=LX+LW/2; rc=RX+RW/2
    ln([(1.9,ya),(lc,ya-0.45)],'#2471a3',1.8,arrow=True); el(1.9,ya-0.17,'$\\mathbf{x}_i$ (512-d)',8.5,'#2471a3')
    ln([(5.3,ya),(rc,ya-0.45)],'#c0392b',1.8,arrow=True); el(5.3,ya-0.17,'$\\mathbf{p}_i$ (6-d)',8.5,'#c0392b')
    yh=ya-0.7
    T(lc,yh,'EMBEDDING PATHWAY',9,weight='bold',color='#2471a3',bbox=dict(fc='#eaf3fb',ec='#2471a3',pad=2)); T(lc,yh-0.27,'(shared with ABMIL)',8,color='#2471a3',style='italic')
    T(rc,yh,'CHOQUET PATHWAY',9,weight='bold',color='#c0392b',bbox=dict(fc='#fdedec',ec='#c0392b',pad=2)); T(rc,yh-0.27,'(pattern interactions)',8,color='#c0392b',style='italic')
    # left stack
    y=yh-0.45
    e1=y-0.75; bx(LX,e1,LW,0.75,'#d6e9f8','#1f6aa5'); T(lc,e1+0.55,'Encoder',9.5,weight='bold'); T(lc,e1+0.22,'Linear(512→256) + LayerNorm + ReLU + Dropout',8,color='#444')
    ln([(lc,yh-0.42),(lc,y)],'#2471a3',1.6,arrow=True)
    g1=e1-0.95; bx(LX,g1,LW,0.75,'#fef6e0','#f39c12'); T(lc,g1+0.55,'Gated Attention',9.5,weight='bold'); T(lc,g1+0.22,"$\\alpha_i=\\mathrm{softmax}(\\mathbf{w}^{\\top}(\\tanh(\\mathbf{Vh})\\odot\\sigma(\\mathbf{Uh})))$",8.5)
    ln([(lc,e1),(lc,g1+0.75)],'#2471a3',1.6,arrow=True)
    s1=g1-0.95; bx(LX,s1,LW,0.8,'#d6e9f8','#1f6aa5'); T(lc,s1+0.6,'Attention-Weighted Sum',9.5,weight='bold'); T(lc,s1+0.27,'$\\mathbf{z}_{\\mathrm{attn}}=\\sum_i\\alpha_i\\,\\mathrm{Enc}(\\mathbf{x}_i)\\in\\mathbb{R}^{256}$  (Eq. 4.26)',8.5)
    ln([(lc,g1),(lc,s1+0.8)],'#2471a3',1.6,arrow=True)
    # right stack
    f1=y-1.65; bx(RX,f1,RW,1.65,'#fdedec','#b03a2e'); T(rc,f1+1.45,'Learned Fuzzy Measure',9.5,weight='bold',color='#a93226')
    T(rc,f1+1.12,'$g(A)=\\sum_{k\\in A}\\phi_k+\\sum_{\\{j,k\\}\\subseteq A}I_{jk}$',8.5); T(rc,f1+0.83,'(Eq. 4.27)',8,color=GREY)
    T(rc,f1+0.6,'21 params: 6 Shapley + 15 interactions',8,color='#555')
    c.text(rc,f1+0.27,'Intrinsic interpretability: φ_k = importance, I_jk = synergy',8,style='italic',color='#a93226',w=RW-0.1,h=0.4)
    ln([(rc,yh-0.42),(rc,y)],'#c0392b',1.6,arrow=True)
    d1=f1-1.7; bx(RX,d1,RW,1.0,'#fce4ec','#b03a2e'); T(rc,d1+0.8,'Discrete Choquet Integral',9.5,weight='bold')
    T(rc,d1+0.5,'$C_g(\\mathbf{p})=\\sum_i(p_{\\sigma(i)}-p_{\\sigma(i-1)})\\cdot g(A_i)$',8.5); T(rc,d1+0.2,'$\\mathbf{c}_s\\in\\mathbb{R}^6$',8.5,color=GREY)
    ln([(rc,f1),(rc,d1+1.0)],'#c0392b',1.6,arrow=True)
    # merge
    ym=d1-1.65; mw=4.4; mx=(W-mw)/2; bx(mx,ym,mw,1.0,'#e8daef','#8e44ad'); 
    T(W/2,ym+0.8,'Merge: Concatenate + Project',10,weight='bold')
    T(W/2,ym+0.5,'$\\mathbf{z}_s=\\mathrm{ReLU}(\\mathbf{W}_{\\mathrm{proj}}[\\mathbf{c}_s\\|\\mathbf{z}_{\\mathrm{attn}}]+\\mathbf{b})\\in\\mathbb{R}^{256}$  (Eq. 4.30)',8.5); T(W/2,ym+0.2,'262 = 256 + 6 input dim',8,color=GREY)
    ln([(lc,s1),(lc,ym+0.5),(mx,ym+0.5)],'#2471a3',1.6,arrow=True); el(lc+0.45,(s1+ym+0.5)/2,'$\\mathbf{z}_{\\mathrm{attn}}$',8.5,'#2471a3')
    ln([(rc,d1),(rc,ym+0.5),(mx+mw,ym+0.5)],'#c0392b',1.6,arrow=True); el(rc+0.4,d1-0.3,'$\\mathbf{c}_s$',8.5,'#c0392b')
    # classifier
    yc=ym-1.2; cw=3.6; cxx=0.5; bx(cxx,yc,cw,0.9,'#d5f5e3','#27ae60'); T(cxx+cw/2,yc+0.68,'Gene-Specific Classifier',9.5,weight='bold'); T(cxx+cw/2,yc+0.33,'$\\hat{Y}^{(g)}_s=\\sigma(\\mathbf{w}_g^{\\top}\\mathbf{z}_s+b_g)$  (Eq. 4.31)',8.5)
    ln([(cxx+cw/2,ym),(cxx+cw/2,yc+0.9)],'#2c3e50',1.6,arrow=True)
    pw=1.7; px=W-0.3-pw; bx(px,yc+0.2,pw,0.65,'white','#8e44ad'); T(px+pw/2,yc+0.65,'P(mut)',9.5,weight='bold'); T(px+pw/2,yc+0.38,'∈ [0, 1]',8,color=GREY)
    ln([(cxx+cw,yc+0.45),(px,yc+0.45)],'#2c3e50',1.6,arrow=True)
    yl=yc-1.15; lw_=4.6; bx(cxx,yl,lw_,0.95,'#fadbd8','#e74c3c'); lx=cxx+lw_/2
    T(lx,yl+0.75,'BCE + Interaction Regulariser',9.5,weight='bold',color='#c0392b')
    T(lx,yl+0.42,'$\\mathcal{L}=\\mathcal{L}^{(g)}_{\\mathrm{BCE}}+\\lambda_I\\sum_{j<k}|I_{jk}|$   ($\\lambda_I=0.01$)',8.5)
    ln([(cxx+cw/2,yc),(cxx+cw/2,yl+0.95)],'#e74c3c',1.5,arrow=True)
    # params note
    nx=cxx+lw_+0.2; nw=W-0.3-nx; bx(nx,yl-0.15,nw,1.35,'#f8f9f9','#aab7b8',lw=1.0)
    c.text(nx+nw/2,yl+0.525,'Parameters\nTotal: ~266k\nEncoder: 131.8k\nAttention: 65.9k\nFuzzy meas.: 42\nProjection: 67.8k\nClassifier: 257',8,color='#444',w=nw,h=1.3)
    print('fc bottom',yl)
    c.save(OUT+'fcmil_architecture.png'); print('fcmil',W,H,audit(c.fig))

def edge():
    W,H=7.2,8.8; c=Canvas(W,H,minpt=8.0); bx,T,ln,el=mkh(c)
    def band(x,y,w,h,fc,ec,title,tc,tx=0.12,tw=None,th=0.35):
        c.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.0,rounding_size=0.12',fc=fc,ec=ec,lw=2.0,zorder=0))
        c.text(x+tx,y+h-0.05-th/2,title,8.5,weight='bold',color=tc,ha='left',w=(tw or w-0.2),h=th)
    def tb(x,y,w,h,txt,fc,ec,tc='#222',ls='-',weight='normal',lw=1.3):
        bx(x,y,w,h,fc,ec,lw=lw,ls=ls); c.text(x+w/2,y+h/2,txt,8,w=w,h=h,color=tc,weight=weight)
    LX,LW,RX,RW=0.15,3.05,4.2,2.85
    tw=3.6; tx=1.6; ty=H-0.85; tb(tx,ty,tw,0.6,'Case Inference Results\npattern composition + mutation predictions','#f2f4f4','#6c7a89',weight='bold',lw=2)
    # L1
    l1h=2.75; l1y=ty-0.5-l1h; band(LX,l1y,LW,l1h,'#dbe9ff','#2563eb','Layer 1: Curated Edge Store (Python dicts)','#1e40af',tx=0.6,tw=2.35,th=0.5)
    tb(1.4,l1y+1.15,1.7,1.0,'30 curated edges\npattern → gene → treatment\nwith PMID provenance\n(ontology_loader module)','#93c5fd','#2563eb')
    tb(0.3,l1y+0.15,2.8,0.75,'Dictionary traversal\nfilter: relevant IRIs only','#bfdbfe','#2563eb')
    ln([(2.25,l1y+1.15),(2.25,l1y+0.9)],'#2563eb',1.3,arrow=True)
    ln([(tx,ty+0.3),(0.55,ty+0.3),(0.55,l1y+0.9)],'#2563eb',1.3,arrow=True)
    T(0.65,ty-0.08,'pattern composition',8,color='#2563eb',style='italic',ha='left')
    # L2
    l2h=3.3; l2y=l1y-0.45-l2h; band(LX,l2y,LW,l2h,'#d1fae5','#059669','Layer 2: Dynamic Case Filter','#065f46')
    tb(0.3,l2y+1.3,2.65,1.45,'Retain only:\n• patterns > 0.5% composition\n• genes reachable from those patterns or predicted positive/inconclusive\n• associated therapies','#a7f3d0','#059669')
    tb(0.27,l2y+0.12,1.4,1.0,'Exclude irrelevant entities (e.g. EGFR inhibitors when no lepidic/papillary detected)','#ecfdf5','#6ee7b7',tc='#555',ls=(0,(4,2)))
    tb(1.78,l2y+0.12,1.2,1.0,'Filtered curated subgraph (asserted edges)','#6ee7b7','#059669')
    ln([(0.97,l2y+1.3),(0.97,l2y+1.12)],'#9ca3af',1.3,ls='--',arrow=True); ln([(2.38,l2y+1.3),(2.38,l2y+1.12)],'#059669',1.3,arrow=True)
    ln([(2.6,l1y+0.15),(2.6,l2y+2.75)],'#2563eb',1.3,arrow=True); el(2.6,(l1y+l2y+l2h)/2+0.0,'all curated edges',8,'#2563eb')
    # channels
    c1=3.5; yr=l2y+2.0
    ln([(c1,ty),(c1,yr),(2.95,yr)],'#059669',1.3,arrow=True); el(c1,ty-0.28,'mutation\npredictions',8,'#059669')
    # L3
    l3h=2.95; l3y=ty-0.45-l3h; band(RX,l3y,RW,l3h,'#fee2e2','#dc2626','Layer 3: Discovered Relations (PostgreSQL)','#991b1b',tw=RW-0.2,th=0.5)
    tb(4.3,l3y+1.5,2.65,0.95,'SQL query:\nSELECT ... FROM discovered_relations WHERE is_active = true ORDER BY created_at DESC','#fca5a5','#dc2626')
    tb(4.28,l3y+0.15,1.3,1.0,'Active discovered relations (inferred edges with provenance)','#fecaca','#dc2626')
    tb(5.68,l3y+0.15,1.3,1.0,'Admin can deactivate false positives (is_active = false)','#fef2f2','#f87171',tc='#991b1b',ls=(0,(4,2)))
    ln([(4.93,l3y+1.5),(4.93,l3y+1.15)],'#dc2626',1.3,arrow=True); ln([(6.33,l3y+1.5),(6.33,l3y+1.15)],'#f87171',1.2,ls='--',arrow=True)
    ay=l3y-0.55-0.8; ax_=4.2; aw=2.85
    tb(ax_,ay,aw,0.8,'Graph Assembly (Python dict merge)\nasserted + inferred edges → JSON','#8b5cf6','#6d28d9','white',weight='bold',lw=2.0)
    ln([(4.93,l3y),(4.93,ay+0.8)],'#dc2626',1.3,ls='--',arrow=True); T(5.05,l3y-0.28,'discovered relations',8,color='#dc2626',style='italic',ha='left')
    iy=ay-0.3-1.4; tb(ax_,iy,aw,1.4,'Injected into LLM prompt as structured context\n+ fuzzy linguistic labels (Level 6)\n+ clinical guardrails\n+ prohibited phrase filter','#ddd6fe','#7c3aed','#5b21b6',lw=2.0)
    cx_=ax_+aw/2
    ln([(cx_,ay),(cx_,iy+1.4)],'#6d28d9',1.8,arrow=True)
    fy=iy-0.3-0.7; tb(ax_,fy,aw,0.7,'Case-Specific Explanation\n(natural language + citations)','#f5f3ff','#7c3aed')
    ln([(cx_,iy),(cx_,fy+0.7)],'#6d28d9',1.8,arrow=True)
    c2=3.85; yf=l2y+0.62
    ln([(2.98,yf),(c2,yf),(c2,ay+0.4),(ax_,ay+0.4)],'#059669',1.3,arrow=True); el(c2,(yf+ay+0.4)/2,'curated\nsubgraph',8,'#059669')
    print('edge bottoms',fy,l2y)
    c.save(OUT+'edge_store_query_flow.png'); print('edge',W,H,audit(c.fig))

def signal():
    W,H=7.2,9.7; c=Canvas(W,H,minpt=8.0); bx,T,ln,el=mkh(c)
    GRN,ORG,BLU='#27ae60','#e08a2c','#2471a3'
    T(W/2,H-0.3,'What kind of problem is morphology  →  mutation prediction for each gene?',10.5,weight='bold',color='#2c3e50')
    c.text(W/2,H-0.62,'Three structural regimes (Finding 2 / RQ2(ii) ontology-coverage taxonomy)',8,style='italic',color='#2c3e50',w=6.9,h=0.3)
    def tb(x,y,w,h,txt,fc,ec,tc='#222',lw=1.6,weight='normal'):
        bx(x,y,w,h,fc,ec,lw=lw); c.text(x+w/2,y+h/2,txt,8,w=w,h=h,color=tc,weight=weight)
    def tb2(x,y,w,h,title,body,fc,ec,lw=1.6):
        bx(x,y,w,h,fc,ec,lw=lw); T(x+w/2,y+h-0.2,title,8.5,weight='bold',color='#222',wrap=False) if False else T(x+w/2,y+h-0.2,title,8.5,weight='bold',color='#222')
        c.text(x+w/2,y+(h-0.35)/2,body,8,w=w,h=h-0.35,color='#222')
    ry=H-1.7; tb(1.2,ry,4.8,0.75,'Where is the discriminative signal p(slide | gene mutant)?\n(CTransPath embedding 512-d  +  6-pattern ANORAK simplex)','#f4f6f6','#2c3e50',weight='bold',lw=1.8)
    gw=1.1; gap=0.08; gx=[0.1+i*(gw+gap) for i in range(6)]; gc=[x+gw/2 for x in gx]
    reg_y=H-3.3; rh=1.3
    tb2(gx[0],reg_y,2*gw+gap,rh,'Regime A','encoder saturation (within the CTransPath embedding)','#d5f5e3',GRN,lw=1.8)
    tb2(gx[2],reg_y,3*gw+2*gap,rh,'Regime B','out-of-ontology signal (no exploitable morphological footprint within the simplex)','#fdebd0',ORG,lw=1.8)
    tb2(gx[5],reg_y,gw,rh,'Regime C','cross-term in label space (logical AND of two channels)','#d6eaf8',BLU,lw=1.8)
    ac=(gx[0]+gx[1]+gw)/2; bc=gc[3]; cc=gc[5]; busy=ry-0.3
    ln([(W/2,ry),(W/2,busy)],BLU,1.6); ln([(ac,busy),(W/2,busy)],GRN,1.6); ln([(W/2,busy),(cc,busy)],BLU,1.6)
    ln([(ac,busy),(ac,reg_y+rh)],GRN,1.6); ln([(bc,busy),(bc,reg_y+rh)],ORG,1.6); ln([(cc,busy),(cc,reg_y+rh)],BLU,1.6)
    sh=1.5; sy=reg_y-0.75-sh
    subs=[('Label-space mismatch','(signal in TME)'),('No morphological projection','(biochemical regulator)'),('Collapse-to-\nprior','(low prevalence, n = 37 mutated slides)')]
    for i,(t,b) in enumerate(subs):
        bx(gx[2+i],sy,gw,sh,'white',ORG,lw=1.6); c.text(gc[2+i],sy+sh-0.38,t,8.5,w=gw,h=0.65,weight='bold'); c.text(gc[2+i],sy+0.48,b,8,w=gw,h=0.8)
    busy2=reg_y-0.35; ln([(bc,reg_y),(bc,busy2)],ORG,1.6); ln([(gc[2],busy2),(gc[4],busy2)],ORG,1.6)
    for i in range(3): ln([(gc[2+i],busy2),(gc[2+i],sy+sh)],ORG,1.6)
    gh=1.2; gy=sy-0.6-gh
    genes=[('TP53','P = 0.951 (TP)','Δpat=−16.1 pp',GRN,'#d5f5e3'),('EGFR','P = 0.076 (FN)','Δpat=−0.5 pp',GRN,'#d5f5e3'),('STK11','P = 0.046 (FN)','Δpat=−5.5 pp',ORG,'#fdebd0'),('KEAP1','P = 0.247 (FN)','Δpat=−44.7 pp',ORG,'#fdebd0'),('RBM10','P = 0.017 (FN)','Δpat=+0.3 pp',ORG,'#fdebd0'),('KRAS','P = 0.965 (TP)','Δpat=+7.6 pp',BLU,'#d6eaf8')]
    for i,(n,p,d,ec,fc) in enumerate(genes):
        bx(gx[i],gy,gw,gh,fc,ec,lw=1.8); T(gc[i],gy+gh-0.25,n,10,weight='bold',color=ec); T(gc[i],gy+0.6,p,8); T(gc[i],gy+0.25,d,8,color='#444')
    for i in (2,3,4): ln([(gc[i],sy),(gc[i],gy+gh)],ORG,1.6)
    ba=gy+gh+0.4
    ln([(ac,reg_y),(ac,ba)],GRN,1.6); ln([(gc[0],ba),(gc[1],ba)],GRN,1.6); ln([(gc[0],ba),(gc[0],gy+gh)],GRN,1.6); ln([(gc[1],ba),(gc[1],gy+gh)],GRN,1.6)
    ln([(cc,reg_y),(cc,gy+gh)],BLU,1.6)
    vy=gy-0.45; T(W/2,vy,'Cohort verdict (Hosmer–Lemeshow gate, AUROC threshold 0.70)',8.5,weight='bold',color='#2c3e50')
    vh=0.85; vb=vy-0.25-vh
    for x,w,t,b,fc,ec,tcol in ((gx[0],2*gw+gap,'Conclusive (AUROC ≥ 0.70)','TP53 (0.718)   EGFR (0.701)','#eafaf1','#82d4a4',GRN),(gx[2],4*gw+3*gap,'Inconclusive (AUROC < 0.70)','KRAS (0.609)   STK11 (0.695)   KEAP1 (0.610)   RBM10 (0.661)','#fef5e7','#f0c08a',ORG)):
        bx(x,vb,w,vh,fc,ec,lw=1.4); T(x+w/2,vb+vh-0.27,t,8.5,weight='bold',color=tcol); c.text(x+w/2,vb+0.27,b,8,w=w,h=0.4)
    c.text(W/2,vb-0.3,'Δpat = P_combined − P_emb-only (pp)   |   values from Table 6.10',8,color='#2c3e50',w=6.8,h=0.3)
    print('signal bottom',vb-0.45)
    c.save(OUT+'signal_tree.png'); print('signal',W,H,audit(c.fig))
if __name__=='__main__':
    import sys
    for f in (sys.argv[1:] or ['abmil','fcmil','edge','signal']): globals()[f]()
