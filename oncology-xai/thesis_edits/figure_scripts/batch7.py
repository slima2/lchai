from fx import *
OUT='../man_out/'
GN=('#d5f5e3','#27ae60'); OR=('#fdebd0','#e67e22'); DK='#2c3e50'
def card(c,x,y,w,h,title,body,col):
    c.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=0.08',fc=col[0],ec=col[1],lw=1.4))
    c.text(x+w/2,y+h-0.25,title,8.5,w=w-0.1,h=0.5,weight='bold',color=DK)
    c.text(x+w/2,y+(h-0.5)/2-0.02,body,8,w=w-0.1,h=h-0.5,color='#333')
def contrib():
    W,H=7.2,10.8; c=Canvas(W,H,minpt=8.0)
    c.text(W/2,H-0.3,'Contribution → Research Question → Evaluation Evidence',10.5,weight='bold',color=DK,w=W-0.3,h=0.45)
    c.text(W/2,H-0.82,'Each contribution is anchored in specific RQs and Chapter 6 findings. Colour: status from Table 7.4.',8,style='italic',color=DK,w=W-0.4,h=0.45)
    xs=[0.1,2.75,4.95]; w=1.95
    for x,t in zip(xs,['Contribution','Research Question','Evidence in Chapter 6']):
        c.box(x,H-1.5,w,0.4,t,9,fc=DK,ec=DK,tc='white',weight='bold')
    Yt=H-1.6
    RQ=[('RQ1: Adaptive fuzzy loss','improves pattern classification',GN,'Pattern classification (Sec 6.1)','92.31% F1; p = 0.001 vs SphereFace'),
        ('RQ2: Pattern-informed MIL','improves mutation prediction',OR,'Finding 1 (PI-ABMIL = B2 ceiling)','Finding 3 (fuzzy = crisp); per-slide ablation Tab 6.10'),
        ('RQ3: Choquet captures','inter-pattern interactions',GN,'Finding 6: Choquet branch on KRAS','I(lep,sol) = +0.032; I(KEAP1) ≈ 0; RBM10 null'),
        ('RQ4: Clinically meaningful','explanations',GN,'6-level XAI demonstration','Sec 6.4: LCHAI on 6 TCGA-LUAD slides'),
        ('RQ5: Greater benefit','under data scarcity',OR,'Cross-study comparison (Sec 6.3)','Surpasses Saldanha 2023, Logan 2022 (TP53, EGFR)'),
        ('RQ6: Ontology-grounded','explanations',GN,'KG demo with provenance tags','Sec 6.4; NCIt/MONDO IRIs; edges with PMIDs'),
        ('RQ7: KG enrichment','from literature',OR,'50 DeepSearch relations','PubMed, arXiv; type-constraint validation')]
    h=1.1; p=1.22; cy=[]
    for i,(t,b,col,et,eb) in enumerate(RQ):
        y=Yt-i*p-h; card(c,xs[1],y,w,h,t,b,col); card(c,xs[2],y,w,h,et,eb,col)
        c.ax.plot([xs[1]+w,xs[2]],[y+h/2]*2,color='#999',lw=1.2)
        cy.append(y+h/2)
    C=[('C1: FuzzyArcLoss V2','(Artefact 1)',GN,[0]),('C2: PI-ABMIL','(Artefact 2)',OR,[1,3]),('C3: FC-MIL','(Artefact 3)',GN,[2]),
       ('C4: LCHAI v2.0 prototype','(integrative system)',GN,[3]),('C5: Mechanism-bound fuzzy utility','(analytical insight)',GN,[1,4]),
       ('C6: Ontology explanation layer','(KG + DeepSearch)',OR,[5,6])]
    pc=(7*p-0.12-h)/5
    for j,(t,b,col,rs) in enumerate(C):
        y=Yt-j*pc-h; card(c,xs[0],y,w,h,t,b,col)
        for r in rs: c.ax.plot([xs[0]+w,xs[1]],[y+h/2,cy[r]],color='#999',lw=1.2)
    ly=0.15
    c.ax.add_patch(FancyBboxPatch((0.1,ly),3.2,0.5,boxstyle='round,pad=0,rounding_size=0.05',fc='white',ec=DK,lw=1))
    c.ax.add_patch(FancyBboxPatch((0.25,ly+0.12),0.3,0.26,boxstyle='round,pad=0,rounding_size=0.04',fc=GN[0],ec=GN[1],lw=1.2)); c.text(0.65,ly+0.25,'Met',8.5,ha='left')
    c.ax.add_patch(FancyBboxPatch((1.45,ly+0.12),0.3,0.26,boxstyle='round,pad=0,rounding_size=0.04',fc=OR[0],ec=OR[1],lw=1.2)); c.text(1.85,ly+0.25,'Partially met',8.5,ha='left')
    c.save(OUT+'contribution_evidence_map.png'); print(audit(c.fig))
contrib()
