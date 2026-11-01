from fx import *
OUT='../man_out/'
DK='#2c3e50'; GN=('#d5f5e3','#27ae60'); RD=('#fadbd8','#c0392b')
def card(c,x,y,w,h,title,body,col):
    c.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=0.08',fc=col[0],ec=col[1],lw=1.5))
    c.text(x+w/2,y+h-0.27,title,8.5,w=w-0.1,h=0.5,weight='bold',color=DK)
    c.text(x+w/2,y+(h-0.5)/2-0.02,body,8.2,w=w-0.15,h=h-0.5,color='#333')
def bd():
    W,H=7.2,8.85; c=Canvas(W,H,minpt=8.0)
    c.text(W/2,H-0.28,'Boundary-dependent benefit of FuzzyArcLoss V2 generalises beyond LUAD',10,weight='bold',color=DK,w=W-0.3,h=0.45)
    c.text(W/2,H-0.78,"V2's adaptive margin targets ambiguous class boundaries (low inter-observer κ), not class rarity. Empirical anchor: LUAD cribriform vs acinar.",8.3,style='italic',color=DK,w=W-0.3,h=0.5)
    xl,xr,w=0.05,3.95,3.2
    for x,t,col in ((xl,'Ambiguous boundary (V2 expected to help)',GN),(xr,'Crisp boundary (V2 neutral or slight penalty)',RD)):
        c.ax.add_patch(Rectangle((x,H-1.7),w,0.6,fc=col[0],ec=col[1],lw=1.8)); c.text(x+w/2,H-1.4,t,9,weight='bold',color=col[1],w=w-0.1,h=0.55)
    rows=[('LUAD (this thesis)',('cribriform vs acinar','κ = 0.38 (Thunnissen et al., 2012)\nV2: +2.2 pp F1 over ArcFace'),('micropapillary vs others','visually distinctive floating clusters\nV2: −1.1 pp vs ArcFace')),
          ('Dermatopathology',('moderately dysplastic naevus vs MIS','Class II concordance ~35% (Elmore et al., BMJ 2017)'),('benign naevus (Class I) vs invasive melanoma (Class V)','higher Class I/V concordance (Elmore 2017)')),
          ('Prostate (Gleason)',('Gleason 3 vs Gleason 4','well-formed → fused glands; high inter-rater variability (Bulten et al., 2020)'),('Gleason 3 vs Gleason 5','glands vs sheets (no glandular formation); morphological consensus (textbook)')),
          ('Cervical cytology',('ASC-US vs LSIL','κ = 0.46, ASC-US largest source of disagreement (Stoler & Schiffman 2001)'),('HSIL vs invasive carcinoma','intra-epithelial lesion vs stromal invasion; morphological consensus (textbook)'))]
    top=H-1.9; h=0.95
    for i,(lab,L,R) in enumerate(rows):
        y=top-0.28-h
        c.text(xl+0.05,top-0.12,lab,8.5,weight='bold',color=DK,ha='left')
        if i==0:
            c.box(1.85,top-0.25,1.4,0.24,'EMPIRICAL',8,fc=GN[1],ec=GN[1],tc='white',weight='bold',round=0.04)
        card(c,xl,y,w,h,*L,GN); card(c,xr,y,w,h,*R,RD)
        c.arrow(xl+w+0.03,y+h/2,xr-0.03,y+h/2,DK,1.4); c.text((xl+w+xr)/2,y+h/2+0.17,'vs',8.5,style='italic',color=DK)
        top=y-0.15
    by=0.1; c.ax.add_patch(Rectangle((0.05,by),W-0.1,1.3,fc='#eaeff2',ec=DK,lw=1.2))
    c.text(W/2,by+1.1,'Mechanism (Section 7.2.4)',9,weight='bold',color=DK)
    c.text(W/2,by+0.52,"V2's fuzzy membership reduces the angular margin only at boundary-ambiguous samples, preventing the model from memorising arbitrary labels at gradual class transitions. When boundaries are crisp, the full margin of ArcFace is appropriate and V2's gentle margin yields no gain.",8.3,w=W-0.5,h=0.9,color='#333')
    c.save(OUT+'boundary_dependent_generalization.png'); print(audit(c.fig))
bd()
