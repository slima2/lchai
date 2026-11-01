from fx import *
from matplotlib.patches import Circle
OUT='../man_out/'
DK='#34495e'
def gp():
    W,H=7.2,9.3; c=Canvas(W,H,minpt=8.0)
    c.text(W/2,H-0.28,'Four mechanisms of the genotype-phenotype mismatch in H&E-based mutation prediction',10,weight='bold',color=DK,w=W-0.3,h=0.5)
    c.text(W/2,H-0.75,'Each mechanism removes information at a different point along the DNA-to-prediction chain.',8.5,style='italic',color=DK,w=W-0.2,h=0.35)
    cols=[('#e67e22','#fdebd0'),('#2471a3','#d6eaf8'),('#7d3c98','#e8daef'),('#c0392b','#fadbd8')]
    names=['DNA / RNA','Protein function','Tissue morphology','Sequenced fragment','Model output']
    bw,gap,x0=0.98,0.55,0.05; cy=H-1.4
    for i,n in enumerate(names):
        c.box(x0+i*(bw+gap),cy-0.35,bw,0.7,n,8.5,fc=DK,ec=DK,tc='white',weight='bold')
        if i<4:
            xa=x0+i*(bw+gap)+bw; c.arrow(xa,cy+0.05,xa+gap,cy+0.05,DK,1.5)
            gx=xa+gap/2; c.ax.add_patch(Circle((gx,cy-0.2),0.12,fc=cols[i][0],ec='white',lw=1,zorder=5)); c.ax.text(gx,cy-0.2,str(i+1),fontsize=c.fs(8.5),color='white',weight='bold',ha='center',va='center',zorder=7)
    M=[('Incomplete morphological penetrance','DNA → tissue','A missense mutation alters protein function without reorganising tissue architecture.','EGFR exon 19 in-frame deletion (non-canonical site)'),
       ('Morphological convergence','tissue → class','Different mutations produce similar tissue. Solid pattern shared by TP53, KRAS, poor differentiation.','Solid growth → TP53 OR KRAS, no unique attribution'),
       ('Intra-tumoural heterogeneity','WSI → fragment','Subclones with different mutations coexist in the WSI. The MAF label applies to the sequenced fragment only.','STK11 sub-clone outside the ABMIL-attended tiles'),
       ('Co-mutation interference','model output','Slides carry multiple drivers; marginal single-gene classifiers cannot exploit known co-occurrence (KRAS+STK11 cold).','TCGA-49-AAR0: TP53 + STK11 + KEAP1 (triple driver)')]
    cw,ch=3.5,2.7
    for i,(t,tag,body,ex) in enumerate(M):
        col,bg=cols[i]; x=0.05+(i%2)*(cw+0.1); top=H-2.0-(i//2)*(ch+0.15); y=top-ch
        c.ax.add_patch(FancyBboxPatch((x,y),cw,ch,boxstyle='round,pad=0,rounding_size=0.1',fc=bg,ec=col,lw=1.8))
        c.box(x+0.1,top-0.5,0.4,0.4,str(i+1),11,fc=col,ec=col,tc='white',weight='bold',round=0.05)
        c.text(x+0.6+1.45,top-0.3,t,9.5,w=2.8,h=0.5,weight='bold',color=col)
        c.box(x+0.1,top-0.88,1.4,0.3,tag,8,fc='white',ec=col,tc=col,weight='bold',round=0.04)
        if i==3: c.box(x+1.6,top-0.88,1.8,0.3,'OBSERVED, NOT TESTED',8,fc=col,ec=col,tc='white',weight='bold',round=0.04)
        c.text(x+cw/2,top-1.4,body,8.5,w=cw-0.3,h=0.8,color='#2c3e50')
        c.ax.add_patch(FancyBboxPatch((x+0.1,y+0.1),cw-0.2,0.85,boxstyle='round,pad=0,rounding_size=0.05',fc='white',ec=col,lw=1))
        c.text(x+0.2,y+0.8,'Example:',8,weight='bold',color=col,ha='left',va='center')
        c.text(x+cw/2,y+0.4,ex,8.3,w=cw-0.4,h=0.5,style='italic',color='#2c3e50')
    ay=0.1; c.ax.add_patch(Rectangle((0.05,ay),W-0.1,1.5,fc='#f4f6f7',ec=DK,lw=1.2))
    c.text(W/2,ay+1.3,'Aggregate effect on the field',9,weight='bold',color=DK)
    c.text(W/2,ay+0.62,'Mechanisms (1)-(3) jointly explain why the best AUROCs for single-gene H&E mutation prediction plateau at ≈ 0.80-0.90 even on cohorts of thousands of slides (EAGLE 8,461; DeepGEM 3,637; CHIEF 60,530). Mechanism (4) is consistent with the same plateau but its specific predictive contribution remains an open empirical question (future-work test in Section 7.4.2).',8.3,w=W-0.5,h=1.1,color='#2c3e50')
    c.save(OUT+'genotype_phenotype_mismatch.png'); print(audit(c.fig))
gp()
