from fx import *
import numpy as np
from matplotlib.patches import Circle
OUT='../man_out/'
CP,CG,CT,CD,CC,CPV,CF='#F5A623','#E74C3C','#9B59B6','#27AE60','#3498DB','#6b7b83','#D5D5D5'
def kg():
    W,H=7.2,10.75; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    def band(top,h,fc,ec,title,tc):
        c.ax.add_patch(FancyBboxPatch((0.1,top-h),7.0,h,boxstyle='round,pad=0,rounding_size=0.1',fc=fc,ec=ec,lw=1.5,zorder=0))
        c.text(0.25,top-0.25,title,10.5,weight='bold',color=tc,ha='left')
    def node(x,y,l,col,r=0.2,sub=None,alpha=1.0,above=False,subw=1.3):
        c.ax.add_patch(Circle((x,y),r,fc=col,ec='white',lw=1.5,alpha=alpha,zorder=3))
        c.text(x,y,l,8,weight='bold',color='white')
        if sub:
            c.text(x,y+(r+0.14 if above else -(r+0.14)),sub,8,color='#222',w=subw)
    def edge(p0,p1,r0=0.2,r1=0.2,col='#555',dash=False,lw=1.3):
        p0=np.array(p0,float);p1=np.array(p1,float);u=(p1-p0)/np.linalg.norm(p1-p0)
        a=p0+u*(r0+0.03);b=p1-u*(r1+0.06)
        c.ax.add_patch(FancyArrowPatch(tuple(a),tuple(b),arrowstyle='-|>',mutation_scale=10,color=col,lw=lw,ls='--' if dash else '-',zorder=2))
    def lab(x,y,t,col='#555'): c.text(x,y,t,8,style='italic',color=col,w=1.9)
    # ---- Layer 1
    t1=H-0.2; band(t1,4.05,'#EDE7F6','#B39DDB','Layer 1: Curated Assertions','#4527A0')
    r1,r2,r3=t1-1.0,t1-1.95,t1-2.9
    for y,s in ((r1,'Solid'),(r2,'Lepidic'),(r3,'Acinar')): node(0.9,y,'P',CP,sub=s,above=True)
    node(2.9,r2,'D',CD,r=0.25,sub='Adenocarcinoma',subw=1.6)
    for y,s in ((r1,'KRAS'),(r2,'EGFR'),(r3,'TP53')): node(4.7,y,'G',CG,sub=s)
    node(6.4,r1,'T',CT,sub='Sotorasib'); node(6.4,r2,'T',CT,sub='Osimertinib')
    for y in (r1,r2,r3): edge((0.9,y),(2.9,r2),0.2,0.25,lw=1.1)
    for y in (r1,r2,r3): edge((2.9,r2),(4.7,y),0.25,0.2,lw=1.1)
    edge((0.9,r1),(4.7,r1),dash=True,col='#999',lw=1.0); edge((0.9,r3),(4.7,r3),dash=True,col='#999',lw=1.0)
    edge((4.7,r1),(6.4,r1),col='#7B1FA2',lw=1.1); edge((4.7,r2),(6.4,r2),col='#7B1FA2',lw=1.1)
    lab(1.85,r2+0.17,'subtypeOf'); lab(3.8,r2+0.17,'mutatedIn')
    lab(2.9,r1+0.17,'associatedWithMutation','#777'); lab(2.9,r3-0.17,'associatedWithMutation','#777')
    lab(5.55,r1+0.17,'treatedWith','#7B1FA2'); lab(5.55,r2+0.17,'treatedWith','#7B1FA2')
    c.text(3.6,t1-3.72,'Provenance: patterns from WHO-2021; mutations from TCGA/CIViC/COSMIC;\ntreatments from OncoKB/FDA.',8,color=CPV,w=6.6,h=0.5)
    # ---- Layer 2
    t2=t1-4.05-0.15; band(t2,2.45,'#E8F5E9','#81C784','Layer 2: Dynamic Case Filtering','#2E7D32')
    c.text(7.0,t2-0.25,'faded nodes = filtered out for this case',8,style='italic',color=CPV,ha='right')
    u,d=t2-1.0,t2-1.85; m=(u+d)/2
    node(0.95,m,'C',CC,r=0.25,sub='Case TCGA-55-7815',subw=1.6)
    node(2.5,u,'P',CP,sub='Acinar 81.8%',subw=1.2); node(2.5,d,'P',CP,sub='Solid 14.1%',subw=1.2)
    node(4.0,u,'G',CG,sub='TP53'); node(4.0,d,'G',CG,sub='EGFR')
    node(5.5,d,'T',CT,sub='Osimertinib')
    node(5.5,u,'G',CF,alpha=.5,sub='KRAS'); node(6.5,u,'T',CF,alpha=.5,sub='Sotorasib'); node(6.5,d,'P',CF,alpha=.5,sub='Lepidic')
    edge((0.95,m),(2.5,u),0.25,0.2,col=CC,lw=1.5); edge((0.95,m),(2.5,d),0.25,0.2,col=CC,lw=1.5)
    edge((2.5,u),(4.0,u)); edge((2.5,d),(4.0,d)); edge((4.0,d),(5.5,d),col='#7B1FA2',lw=1.1)
    lab(4.75,d+0.17,'treatedWith','#7B1FA2')
    # ---- Layer 3
    t3=t2-2.45-0.15; band(t3,3.6,'#E3F2FD','#64B5F6','Layer 3: Literature DeepSearch','#1565C0')
    by,bh=t3-2.0,1.5
    c.box(0.2,by,1.1,bh,'PubMed\n\nSemantic Scholar\n\narXiv',8,fc='white',ec='#90A4AE',weight='bold')
    c.box(1.55,by,1.0,bh,'LLM Extraction',8,fc='#FFF9C4',ec='#FBC02D',weight='bold')
    c.ax.add_patch(FancyBboxPatch((2.8,by),2.6,bh,boxstyle='round,pad=0,rounding_size=0.08',fc='white',ec='#90A4AE',lw=1.0))
    c.text(4.1,by+bh-0.2,'new relation triples',8,weight='bold')
    for yy,tx in ((by+bh-0.5,'(KRAS, treatedWith, Adagrasib)'),(by+bh-0.88,'(Acinar, associatedWith\n Mutation, TP53)'),(by+bh-1.27,'(Lepidic, associatedWith\n Mutation, EGFR)')):
        t=c.ax.text(4.1,yy,tx,fontsize=c.fs(8),ha='center',va='center',family='monospace',color='#444',linespacing=1.1)
    c.box(5.65,by,1.3,bh,'Entity Linking + Validation',8,fc='#E8F5E9',ec='#66BB6A',weight='bold')
    for xa,xb in ((1.3,1.55),(2.55,2.8),(5.4,5.65)): c.arrow(xa+0.01,by+bh/2,xb-0.01,by+bh/2,'#555',1.4)
    ry=t3-2.55
    for (xa,la,ca,xb,lb,cb) in ((0.9,'Solid',CP,2.3,'KRAS',CG),(3.1,'Adenoca.',CD,4.5,'EGFR',CG),(5.3,'Acinar',CP,6.7,'TP53',CG)):
        node(xa,ry,'P' if la in('Solid','Acinar') else 'D',ca,r=0.17,sub=la,subw=1.0); node(xb,ry,'G',cb,r=0.17,sub=lb,subw=1.0)
        edge((xa,ry),(xb,ry),0.17,0.17,col='#999',dash=True,lw=1.0)
    c.text(3.6,t3-3.35,'Validated new edges (dashed) are added to Layer 1 with provenance, e.g. PMID:39284611.',8,color=CPV,w=6.6,h=0.3)
    c.save(OUT+'kg_three_layer_architecture.png'); print(audit(c.fig))
kg()
