from fx import *
OUT='../man_out/'
DK='#2c3e50'
TH={'D':('#16a085','#e8f6f3'),'M':('#8e44ad','#f4ecf7'),'S':('#d35400','#fae5d3'),'P':('#2980b9','#d6eaf8')}
def card(c,x,y,w,h,title,body,th):
    ec,fc=TH[th]
    c.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=0.07',fc=fc,ec=ec,lw=1.5))
    c.text(x+w/2,y+h-0.21,title,8.3,w=w-0.1,h=0.38,weight='bold',color=ec)
    c.text(x+w/2,y+0.23,body,8,w=w-0.12,h=0.42,color='#333')
def rm():
    W,H=7.2,10.8; c=Canvas(W,H,minpt=8.0)
    c.text(W/2,H-0.25,'Future-work roadmap (Section 7.4)',10.5,weight='bold',color=DK,w=W-0.3,h=0.4)
    c.text(W/2,H-0.7,'Concrete extensions organised by feasibility and time horizon. Themes are colour-coded: data, methodology, system, deployment.',8.3,style='italic',color=DK,w=W-0.3,h=0.5)
    S=[('Short-term: post-thesis (months), starting now',('#d5f5e3','#27ae60'),[
        ('External validation','CPTAC-3, APOLLO, EAGLE cohorts','D'),('Pathologist concordance','2-3 raters × 50 slides; incl. AL-loop eval (SOLCA Guayaquil)','D'),('Threshold calibration','Platt / temperature scaling','M'),
        ('Deterministic training','+3 seeds; tighter CIs for mutation benchmark','M'),('V2 coefficient sensitivity','9 configs (a_H, b_L/b_H); 5×3 protocol','M'),('vs CurricularFace','per-sample adaptive margin baseline','M'),
        ('High-P Inconclusive genes strategy','4 levers (data, taxonomy, calibration, MoE)','S')]),
       ('Medium-term: 1-2 years (+12-24 months)',('#fdebd0','#e67e22'),[
        ('Foundation embeddings','UNI / CONCH / GigaPath / Virchow encoders','M'),('Pure Choquet ablation','isolate fuzzy aggregator from embedding pathway','M'),('MoE gate (label-free)','softmax over 3 experts; frozen ablation models','M'),
        ('Multi-task MIL','joint 6-gene prediction; co-occurrence priors','M'),('Expanded pattern set','+stroma, +TSR, +TILs, +budding, +IMA (KRAS)','D'),('Fuzzy IF-THEN priors','Mamdani rule-based mutation prior','M'),
        ('KG triplestore','Fuseki / GraphDB; OWL + SHACL + federated','S'),('DeepSearch scale + HITL','more queries/sources; entity linking','S'),('KG explanation eval','blinded clinician test; KG vs no-KG hallucination','S'),
        ('Cross-tumour extension','LUSC, colorectal, gastric (WHO taxonomy)','D'),('Multi-centre retrospective','2-5k slides; domain-shift study','P')]),
       ('Long-term: multi-year vision',('#d6eaf8','#2980b9'),[
        ('Prospective silent trial','partner hospital; EAGLE-style OOD validation','P'),('Neuro-symbolic pipeline','labels → fuzzy engine → learned rules','M')])]
    y=H-1.1; h=0.84; w=2.3
    for name,col,items in S:
        c.ax.add_patch(FancyBboxPatch((0.05,y-0.42),W-0.1,0.42,boxstyle='round,pad=0,rounding_size=0.07',fc=col[0],ec=col[1],lw=1.8))
        c.text(W/2,y-0.21,name,9.5,weight='bold',color=col[1],w=W-0.3,h=0.4)
        y-=0.5
        for i,(t,b,th) in enumerate(items):
            r,cc=divmod(i,3); card(c,0.05+cc*2.38,y-r*0.9-h,w,h,t,b,th)
        y-=((len(items)+2)//3)*0.9+0.06
    ly=0.1; c.ax.add_patch(FancyBboxPatch((0.05,ly),W-0.1,0.42,boxstyle='round,pad=0,rounding_size=0.06',fc='white',ec=DK,lw=1.2))
    c.text(0.15,ly+0.21,'Theme:',8.3,weight='bold',ha='left',color=DK)
    for xx,(k,t) in zip((0.85,2.35,3.95,5.45),(('D','Data / cohorts'),('M','Methodology'),('S','System / KG'),('P','Deployment'))):
        c.ax.add_patch(Rectangle((xx,ly+0.11),0.2,0.2,fc=TH[k][0],ec=TH[k][0])); c.text(xx+0.28,ly+0.21,t,8.3,ha='left')
    c.save(OUT+'future_work_roadmap.png'); print(audit(c.fig), y)
rm()
