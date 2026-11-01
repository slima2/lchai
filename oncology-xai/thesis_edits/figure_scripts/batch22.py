import sys
from fx import *
import numpy as np
OUT='../man_out/'
def al():
    W,H=7.2,7.3; c=Canvas(W,H,minpt=8.0)
    c.text(W/2+0.2,H-0.3,'Active Learning: Expert Pattern Correction Workflow',10.5,weight='bold',color='#1e293b',w=W-0.5,h=0.4)
    items=[('1. Viewer Tab Pattern Overlay (misclassification detected)','#1e40af','Pathologist identifies error'),
    ('2. Draw lasso around incorrect tiles (click & drag)','#f97316','~150 tiles selected'),
    ('3. Select correct pattern from dropdown (6 ANORAK classes)','#7c3aed','e.g., acinar → micropapillary'),
    ('4. Save & retrain (submit to active-learning service)','#dc2626','Corrections persisted in DB'),
    ('5. Delta training (head-only, 10 epochs)','#059669','~30 seconds, CPU only'),
    ('6. Updated overlays + predictions','#0891b2','New model version v2.0.1')]
    bx,bw,bh,pitch=1.0,3.7,0.72,1.0; top=H-0.95
    ys=[]
    for i,(t,col,a) in enumerate(items):
        y=top-bh-i*pitch; ys.append(y)
        c.box(bx,y,bw,bh,t,8,fc=col,ec='#374151',tc='white',weight='bold')
        c.text(bx+bw+0.2,y+bh/2,a,8,style='italic',color='#475569',ha='left',w=2.1,h=0.6)
        if i: c.arrow(bx+bw/2,ys[i-1],bx+bw/2,y+bh,'#6b7280',1.4)
    lx=0.62; BL='#2563eb'
    ym6=ys[5]+bh/2; ym1=ys[0]+bh/2
    c.ax.plot([bx,lx,lx],[ym6,ym6,ym1],color=BL,lw=1.6,zorder=2); c.arrow(lx,ym1,bx-0.01,ym1,BL,1.6)
    c.ax.text(0.28,(ym6+ym1)/2,'Feedback loop: pathologist reviews updated overlay and may correct further',rotation=90,ha='center',va='center',fontsize=c.fs(8),style='italic',color=BL)
    c.save(OUT+'active_learning_workflow.png'); print(audit(c.fig))

from matplotlib.patches import Polygon
def stagebox(c,x,y,w,h,title,body,fc,ec,tc):
    c.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=0.08',fc=fc,ec=ec,lw=1.2))
    c.text(x+w/2,y+h-0.2,title,8.5,weight='bold',color=tc,w=w-0.2,h=0.3)
    c.text(x+0.15,y+h-0.38,body,8,color=tc,ha='left',va='top',w=w-0.25,h=h-0.45,ls=1.2)
def tf():
    W,H=7.2,10.2; c=Canvas(W,H,minpt=8.0)
    cx=2.6; BW=4.6; X=cx-BW/2; G='#6b7280'
    c.text(W/2,H-0.3,'Tile Filtering Pipeline',11,weight='bold',color='#1e293b',w=W-0.4,h=0.4)
    c.text(W/2,H-0.65,'Three-stage quality control from WSI to accepted tiles',8.3,style='italic',color='#64748b',w=W-0.4,h=0.3)
    c.box(cx-1.3,H-1.5,2.6,0.6,'Whole Slide Image (WSI / SVS / BIF)',8,fc='#1e40af',ec='#374151',tc='white',weight='bold')
    c.arrow(cx,H-1.5,cx,H-1.85,G,1.4)
    stagebox(c,X,H-3.3,BW,1.45,'Stage 0: Global Tissue Mask','1. Thumbnail (1/32 resolution)\n2. Greyscale → Otsu threshold\n3. Dark pixel exclusion (<80)\n4. H&E hue check\n5. Downsample to tile grid','#dbeafe','#374151','#1e3a5f')
    c.arrow(cx,H-3.3,cx,H-3.65,G,1.4); c.text(cx+0.1,H-3.48,'tile candidates',8,color=G,ha='left',w=1.6,h=0.25)
    stagebox(c,X,H-5.25,BW,1.6,'Stage 1: Per-Tile Quality Checks','• Background rejection (>85% pixels intensity >220)\n• Very dark tile rejection (>30% pixels intensity <50)\n• Tissue fold detection (>40% intensity <100)\n• Low texture rejection (std dev <12)\n• Low saturation rejection (HSV sat <0.03)\n• H&E hue compatibility (≥30% H&E-compatible pixels)','#f0fdf4','#374151','#14532d')
    c.arrow(cx,H-5.25,cx,H-5.52,G,1.4)
    dy=H-5.97; c.ax.add_patch(Polygon([(cx,dy+0.45),(cx+1.7,dy),(cx,dy-0.45),(cx-1.7,dy)],fc='#fef3c7',ec='#f59e0b',lw=1.4,zorder=3))
    c.text(cx,dy,'Clinical slide?\n(pen marks expected)',8,weight='bold',color='#92400e')
    c.arrow(cx,dy-0.45,cx,H-6.85,G,1.4); c.text(cx+0.1,dy-0.65,'Yes',8,color=G,ha='left')
    stagebox(c,X,H-8.45,BW,1.6,'Stage 2: Pen Marker & Artefact Rejection','• Blue pen (B>R+40, B>G+30, B>120)\n• Red pen (R>180, R>G+50, R>B+50)\n• Green / olive / yellow markers\n• India ink, light blue / teal\n• Straight-edge detection (barcodes, labels)\n• Non-H&E colour cast rejection','#fef2f2','#374151','#7f1d1d')
    c.arrow(cx,H-8.45,cx,H-8.8,G,1.4)
    oy=H-9.5; c.box(cx-1.7,oy,3.4,0.7,'Accepted Tissue Tiles\ne.g., 8,468 / 22,692 (37%)',8.5,fc='#16a34a',ec='#374151',tc='white',weight='bold')
    c.text(cx,H-9.85,'→ CTransPath embedding → ABMIL / Choquet → P(mut)',8,style='italic',color='#64748b',w=W-0.6,h=0.3)
    # rejects
    for yc,txt,col,ac in ((H-2.575,'Rejected: glass, non-tissue, ink (~60–70%)','#2563eb','#93c5fd'),(H-4.45,'Rejected: background, folds, artifacts','#16a34a','#86efac'),(H-7.65,'Rejected: pen marks, labels (+25–40%)','#dc2626','#fca5a5')):
        c.arrow(X+BW,yc,X+BW+0.3,yc,ac,1.4); c.text(X+BW+0.4,yc,txt,8,style='italic',color=col,ha='left',w=1.7,h=0.8)
    # bypass
    bx=7.0
    c.ax.plot([cx+1.7,bx,bx],[dy,dy,oy+0.35],color=G,lw=1.4,zorder=2); c.arrow(bx,oy+0.35,cx+1.7,oy+0.35,G,1.4)
    c.text((cx+1.7+bx)/2,dy+0.17,'No (TCGA)',8,color=G)
    c.save(OUT+'tile_filtering_pipeline.png'); print(audit(c.fig))


def grp(c,x,y,w,h,fc,ec,label=None,lc=None,lx=None,ly=None,lw=None,lh=0.45,ha='left'):
    c.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=0.12',fc=fc,ec=ec,lw=1.3,zorder=0))
    if label: c.text(lx,ly,label,8,color=lc,ha=ha,w=lw or w-0.2,h=lh)
def ap():
    W,H=7.2,10.2; c=Canvas(W,H,minpt=8.0); T=H-0.1; Tl=T-0.25; G='#222'
    # preprocessing
    grp(c,0.1,T-1.35,7.0,1.35,'#f0f0f0','#999','Preprocessing (shared by all downstream stages)','#555',0.25,T-0.22,5.0)
    py=T-1.2; ph=0.7
    c.box(0.35,py,0.7,ph,'WSI',8,fc='white',ec='#777')
    c.box(1.5,py,1.4,ph,'Tiles\n224×224 at 20×',8,fc='white',ec='#777')
    c.box(3.25,py,1.2,ph,'CTransPath\n(frozen)',8,fc='#e8f5e9',ec='#43a047')
    c.box(4.8,py,1.6,ph,'Embeddings\n$x_i\\in\\mathbb{R}^{512}$',8,fc='#e3f2fd',ec='#1976d2')
    for xa,xb in ((1.05,1.5),(2.9,3.25),(4.45,4.8)): c.arrow(xa,py+ph/2,xb,py+ph/2,G,1.3)
    c.text(1.275,py+ph/2+0.17,'tiling',8,color='#333')
    # A1
    ORG='#e65100'
    grp(c,3.9,T-4.4,3.1,2.4,'#fff3e0',ORG,'Artefact 1 — FuzzyArcLoss V2',ORG,4.0,T-4.17,2.1,0.3)
    c.box(4.35,T-3.0,2.5,0.65,'FuzzyArcLoss V2\n(membership μ)',8,fc='#ffe0b2',ec=ORG)
    c.box(4.35,T-3.95,2.5,0.65,'Pattern Probs\n$p_i\\in\\Delta^{5}$ (6-d)',8,fc='#ffe0b2',ec=ORG)
    c.arrow(5.6,T-3.0,5.6,T-3.3,G,1.3); c.text(5.7,T-3.15,'softmax',8,ha='left',color='#333')
    c.arrow(5.6,T-1.2,5.6,T-2.35,G,1.3)
    # concat
    c.box(0.5,T-3.99,2.7,0.75,'Concat ‖\n$h_i=[x_i\\,‖\\,p_i]\\in\\mathbb{R}^{518}$',8,fc='#f3e5f5',ec='#7b1fa2')
    BL='#1976d2'
    c.ax.plot([5.0,1.85],[T-1.65]*2,color=BL,lw=2.0,zorder=2); c.ax.plot([1.85,1.85],[T-1.65,T-3.24],color=BL,lw=2.0,zorder=2); c.arrow(1.85,T-3.0,1.85,T-3.24,BL,2.0)
    c.arrow(5.0,T-1.2,5.0,T-1.64,BL,2.0)
    c.text(2.1,T-2.45,'512-d',8,ha='left',color='#333')
    c.arrow(4.35,T-3.62,3.21,T-3.62,ORG,2.0); c.text(4.1,T-3.42,'6-d',8,color='#333')
    # Art2
    A2='#1565c0'
    grp(c,0.1,Tl-8.55,3.4,4.05,'#e3f2fd',A2,'Artefact 2 — PI-ABMIL (Pattern-Informed ABMIL, ours)',A2,1.8,Tl-8.2,3.1,0.5,ha='center')
    c.box(0.55,Tl-5.85,2.6,0.85,'Gated Attention MIL\n(~200k params)\nMutation Prediction',8,fc='#bbdefb',ec=A2)
    c.box(0.55,Tl-7.7,2.6,0.7,'Attention Maps\n+ Pattern Overlay',8,fc='#bbdefb',ec=A2)
    c.arrow(1.85,T-3.99,1.85,Tl-5.0,'#7b1fa2',2.0); c.text(2.05,Tl-4.4,'518-d',8,ha='left',color='#333')
    c.arrow(1.85,Tl-5.85,1.85,Tl-7.0,G,1.3)
    # Art3
    A3='#bf360c'
    grp(c,3.7,Tl-8.55,3.3,4.05,'#fbe9e7',A3,'Artefact 3 — FC-MIL (Fuzzy Choquet MIL, ours, hybrid dual-pathway)',A3,5.35,Tl-8.2,3.1,0.5,ha='center')
    c.box(3.8,Tl-5.7,1.55,1.0,'Embedding Pathway\nEncoder + Attention\n(shared with Art. 2)',8,fc='#bbdefb',ec=G,lw=1.3)
    c.box(5.4,Tl-5.7,1.55,1.0,'Choquet Pathway\nChoquet Integral\nFuzzy Measure (21 p.)',8,fc='#ffe0b2',ec=G,lw=1.3)
    c.box(4.0,Tl-6.65,2.7,0.65,'Merge → Projection\n→ Classifier (~266k total)',8,fc='#ffccbc',ec=A3)
    c.box(4.0,Tl-7.85,2.7,0.9,'Mutation Pred.\n+ Shapley Values\n+ Interaction Indices',8,fc='#ffccbc',ec=A3)
    c.arrow(4.575,Tl-5.7,5.0,Tl-6.0,G,1.3); c.arrow(6.175,Tl-5.7,5.7,Tl-6.0,G,1.3); c.arrow(5.35,Tl-6.65,5.35,Tl-6.95,G,1.3)
    # branch Emb->Art3
    c.ax.plot([3.62,3.62],[T-1.65,Tl-5.2],color=BL,lw=2.0,zorder=2); c.arrow(3.62,Tl-5.2,3.79,Tl-5.2,BL,2.0)
    c.arrow(6.175,T-3.95,6.175,Tl-4.69,ORG,2.0); c.text(6.3,Tl-4.3,'6-d',8,ha='left',color='#333')
    # bottom
    c.box(1.0,Tl-9.7,5.2,0.7,'LCHAI v2.0 Clinical Decision Support\nSix-level interpretability · Knowledge graph · Confidence labels',8,fc='#c8e6c9',ec='#2e7d32',lw=2)
    c.arrow(1.85,Tl-8.55,2.5,Tl-9.0,G,1.3); c.arrow(5.35,Tl-8.55,4.8,Tl-9.0,G,1.3)
    c.save(OUT+'artifact_pipeline.png'); print(audit(c.fig))

def radar():
    import numpy as np
    W,H=7.2,7.0; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    genes=["TP53","EGFR","KRAS","STK11","KEAP1","RBM10"]
    cond={"B2: ABMIL-emb":[.718,.701,.607,.684,.597,.642],"B3: ABMIL-pat":[.616,.625,.545,.617,.588,.653],"PI-ABMIL (ours)":[.716,.694,.590,.695,.610,.640],"FC-MIL (ours)":[.716,.684,.609,.658,.589,.661]}
    cols=["#1B3A5C","#2E8B57","#E05252","#F5A623"]
    ang=np.linspace(0,2*np.pi,6,endpoint=False).tolist(); ang+=ang[:1]
    c.text(W/2,H-0.25,'AUROC Profile Across Genes',11,weight='bold',w=W-0.4,h=0.4)
    s=5.0; ax=c.fig.add_axes([(W-s)/2/W,1.35/H,s/W,s/H],polar=True); ax.set_axisbelow(False)
    for (n,v),col in zip(cond.items(),cols):
        vv=v+v[:1]; ax.plot(ang,vv,'o-',lw=P(1.8),ms=P(5),color=col,label=n); ax.fill(ang,vv,alpha=.08,color=col)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(genes,fontsize=P(9.5),fontweight='bold'); ax.tick_params(axis='x',pad=P(9))
    ax.set_ylim(0.48,0.75); ax.set_rticks([.5,.55,.6,.65,.7]); ax.set_rlabel_position(30)
    ax.set_yticklabels(['0.50','0.55','0.60','0.65','0.70'],fontsize=P(8.5))
    for l in ax.get_yticklabels(): l.set_bbox(dict(fc='white',ec='none',alpha=.9,pad=1.0))
    ax.grid(lw=P(.6))
    c.fig.legend(loc='lower center',bbox_to_anchor=(0.5,0.02),ncol=2,fontsize=P(8.5),frameon=True,columnspacing=2.0,borderpad=0.7,labelspacing=0.6)
    c.save(OUT+'auroc_radar_profile.png'); print(audit(c.fig))

def abl():
    W,H=7.2,6.45; c=Canvas(W,H,minpt=8.0); G='#6b7280'
    c.text(W/2,H-0.3,'Causal Chain: From Tile Features to $P(\\mathrm{mut})$',10.5,weight='bold',color='#1e293b',w=W-0.4,h=0.4)
    c.text(W/2,H-0.65,'Three independently trained models — not components of a single prediction',8.3,style='italic',color='#64748b',w=W-0.4,h=0.3)
    rows=[(H+0.55-1.95),(H+0.55-3.05),(H+0.55-4.15)]; bh=0.6
    c.box(0.1,(H+0.55-2.85),1.5,0.8,'$\\mathbf{x}_i\\in\\mathbb{R}^{512}$\nCTransPath\nEmbeddings',8,fc='#3b82f6',ec='#374151',tc='white')
    c.box(0.1,(H+0.55-4.05),1.5,0.8,'$\\mathbf{p}_i\\in\\Delta^5$\nFuzzy Pattern\nProbabilities',8,fc='#ef4444',ec='#374151',tc='white')
    xi=((H+0.55-2.45)); pi=((H+0.55-3.65))
    M=[('ABMIL  $[\\mathbf{x}_i\\,\\|\\,\\mathbf{p}_i]$','#2563eb','Model P (Combined, 518-d)','$P_{\\mathrm{comb}}$'),
       ('ABMIL  $\\mathbf{x}_i$ only','#f97316','Model B2 (Emb-only, 512-d)','$P_{\\mathrm{emb}}$'),
       ('ABMIL  $\\mathbf{p}_i$ only','#7c3aed','Model B3 (Pat-only, 6-d)','$P_{\\mathrm{pat}}$')]
    for yc,(t,col,lab,pt) in zip(rows,M):
        c.box(2.0,yc-bh/2,1.9,bh,t,8,fc=col,ec='#374151',tc='white')
        c.text(2.95,yc+bh/2+0.17,lab,8,style='italic',color=col,w=2.4,h=0.25)
        c.box(4.3,yc-bh/2,0.7,bh,'$\\sigma(\\cdot)$',9,fc='#e5e7eb',ec='#374151',tc='#374151')
        c.box(5.4,yc-bh/2,0.95,bh,pt,9,fc=col,ec='#374151',tc='white')
        c.arrow(3.9,yc,4.3,yc,G,1.3); c.arrow(5.0,yc,5.4,yc,G,1.3)
    c.arrow(1.6,xi,2.0,rows[0],G,1.3); c.arrow(1.6,xi,2.0,rows[1],G,1.3)
    c.arrow(1.6,pi,2.0,rows[0]-0.1,G,1.3); c.arrow(1.6,pi,2.0,rows[2],G,1.3)
    ax=c.ax
    from matplotlib.patches import FancyArrowPatch
    ax.add_patch(FancyArrowPatch((5.875,rows[0]-bh/2-0.02),(5.875,rows[1]+bh/2+0.02),arrowstyle='<|-|>',mutation_scale=11,color='#dc2626',lw=1.8))
    c.text(6.75,(rows[0]+rows[1])/2,'$\\Delta_{\\mathrm{pat}}$',10,color='#dc2626',weight='bold')
    c.text(W/2,(H+0.55-5.05),'$\\Delta_{\\mathrm{pat}}=P_{\\mathrm{comb}}-P_{\\mathrm{emb}}$',10,weight='bold',color='#1e293b')
    bb=c.ax.texts[-1]; bb.set_bbox(dict(boxstyle='round,pad=0.4',fc='#fef3c7',ec='#f59e0b',lw=1.2))
    c.text(W/2,(H+0.55-5.75),'$\\Delta_{\\mathrm{pat}}>0$: patterns help (constructive)\n$\\Delta_{\\mathrm{pat}}<0$: patterns hurt (destructive interference)',8,color='#475569',w=6.9,h=0.5)
    c.text(W/2,(H+0.55-6.4),'Note: $P(\\mathrm{mut})$ in the gene header comes from the gene-optimal model, which may be any of these three or a different architecture (FC-MIL).',8,style='italic',color='#64748b',w=6.6,h=0.5)
    c.save(OUT+'ablation_causal_chain.png'); print(audit(c.fig))

def pillars():
    W,H=7.2,9.3; c=Canvas(W,H,minpt=8.0); DK='#1f2937'
    c.box(2.1,H-0.85,3.0,0.65,'LUAD-diagnosed patient',9,fc=DK,ec=DK,tc='white',weight='bold')
    cols=[(0.15,'#7c2d12','#ea580c','#7c2d12','#fff7ed','#7c2d12','Histological information',
           ['Tissue slide\n(H&E-stained section)','Light microscopy\n(pathologist examination)',
            'Predominant growth pattern (1 of 6)\n\nWHO 2021 (5): lepidic · acinar · papillary · micropapillary · solid\n\nANORAK (+1): cribriform','Tumour grade  |  prognosis'],'Universally available'),
          (3.75,'#1e3fae','#2563eb','#1e40af','#eff6ff','#1e3fae','Molecular information',
           ['Tumour DNA\n(somatic, not inherited)','Next-generation sequencing (NGS)\n7–21 day turnaround',
            'Actionable mutations (binary per gene)\n\nTP53 · EGFR · KRAS · STK11 · KEAP1 · RBM10\n\n(panel addressed in this thesis)','Targeted therapy choice'],'Specialised lab; bottleneck')]
    cw=3.3
    for x,hc,bc,lc,fc,ac,title,items,note in cols:
        cx=x+cw/2
        c.box(x+0.15,H-1.85,cw-0.3,0.5,title,9,fc=hc,ec=DK,tc='white',weight='bold')
        c.arrow(cx if False else (3.0 if x<1 else 4.2),H-0.85,cx,H-1.35,DK,1.5)
        c.ax.add_patch(FancyBboxPatch((x,H-7.75),cw,5.7,boxstyle='round,pad=0,rounding_size=0.12',fc=fc,ec='#94a3b8',lw=1.3,zorder=0))
        bx,bw=x+0.2,cw-0.4
        ys=[(H-3.35,0.65),(H-4.35,0.65),(H-6.15,1.5),(H-7.2,0.65)]
        c.arrow(cx,H-1.85,cx,H-2.7,ac,1.5)
        for i,((y,h),t) in enumerate(zip(ys,items)):
            if i==2: c.box(bx,y,bw,h,t,8,fc='white',ec=ac,tc='#1f2937',lw=1.4)
            else: c.box(bx,y,bw,h,t,8.5,fc=bc if i<2 else lc,ec=DK,tc='white',weight='bold')
            if i: c.arrow(cx,ys[i-1][0],cx,y+h,ac,1.6)
        c.text(cx,H-7.5,note,8,style='italic',color=lc,w=cw-0.3,h=0.25)
    c.box(1.9,H-9.05,3.4,0.65,'Treatment decision',9.5,fc='#166534',ec=DK,tc='white',weight='bold')
    c.arrow(1.8,H-7.75,2.7,H-8.4,'#166534',1.6); c.arrow(5.4,H-7.75,4.5,H-8.4,'#166534',1.6)
    c.save(OUT+'luad_two_pillars.png'); print(audit(c.fig))
