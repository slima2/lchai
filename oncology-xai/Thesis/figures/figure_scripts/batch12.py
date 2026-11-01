from fx import *
OUT='../man_out/'
DK='#2c3e50'
def kis():
    W,H=7.2,10.4; c=Canvas(W,H,minpt=8.0)
    c.text(W/2,H-0.25,'Closing the population AUROC vs per-slide confidence gap',10.5,weight='bold',color=DK,w=W-0.3,h=0.4)
    c.text(W/2,H-0.58,'Four strategies anchored on the KRAS Inconclusive paradox (future work, Section 7.4.1).',8.3,style='italic',color=DK,w=W-0.3,h=0.3)
    ay=H-1.95; c.ax.add_patch(FancyBboxPatch((0.05,ay),W-0.1,1.25,boxstyle='round,pad=0,rounding_size=0.08',fc='#fdf2e9',ec='#e67e22',lw=1.8))
    c.text(W/2,ay+1.08,'Anchor case: KRAS, slide TCGA-55-7815',9.5,weight='bold',color='#e67e22')
    c.text(W/2,ay+0.72,'Per-slide P(mut) = 0.965 on a morphologically KRAS-consistent slide, yet population-level AUROC = 0.609 (< 0.70 threshold) → labelled Inconclusive.',8.3,w=W-0.4,h=0.4,color='#333')
    c.text(W/2,ay+0.28,'Cohort statistic and per-slide score answer different questions; the four strategies below pull four different levers.',8.3,style='italic',w=W-0.4,h=0.4,color='#333')
    S=[('(i)  Larger and more diverse cohorts','Long-term','#2980b9','#e8f4fc','data scale and source diversity',
        'Multi-institutional cohort of 2,000-5,000 slides (vs current 687) with broader geographic and morphological coverage, including mucinous / IMA cases under-represented in TCGA. Stabilises fold-to-fold variance and is expected to lift KRAS population AUROC above 0.70.',
        'Single-cohort scope of this thesis; cross-institutional acquisition is a data-engineering effort beyond the artefact.'),
       ('(ii)  Expanded pattern taxonomy','Medium-term','#27ae60','#e9f7ef','output space of the pattern classifier',
        'Add a mucinous / invasive-mucinous-adenocarcinoma (IMA) channel to the 6-class softmax. Gives the Choquet aggregator the morphological feature most strongly tied to KRAS in the literature; lifts both population AUROC and per-slide interpretability for KRAS.',
        'Requires new pixel-level annotations on a cohort that includes IMA samples; not available in ANORAK / Zenodo at the time of writing.'),
       ('(iii)  Per-slide confidence calibration','Short-term','#b7950b','#fef9e7','how the prediction is reported, not how it is computed',
        "Replace the gene-wide Conclusive / Inconclusive label with a per-slide confidence score from morphological similarity to KRAS-positive training cases. Lets TCGA-55-7815 surface as 'high individual confidence despite population-level uncertainty'.",
        'Needs a calibration set of pathologist-validated representative slides per gene; the preliminary 5-slide review of Section 7.3.1 is not yet sufficient.'),
       ('(iv)  Per-slide model selection','Medium-term','#8e44ad','#f4ecf7','inference-time routing across the ablation panel',
        'Replace the current gene-optimal-by-population selection (Finding 2) with a learnable meta-learner that, given a slide, routes it to the ablation model expected to perform best on that slide (mixture-of-experts gate over the Level 5 ablation panel).',
        'The label-free MoE gate is already documented as future work (Section 7.4.2); calibrating it on N=687 slides without circularity is the blocker.')]
    top=ay-0.1; ch=1.78
    for t,hz,col,bg,lev,chg,why in S:
        y=top-ch
        c.ax.add_patch(FancyBboxPatch((0.05,y),W-0.1,ch,boxstyle='round,pad=0,rounding_size=0.08',fc=bg,ec=col,lw=1.8))
        c.ax.add_patch(Rectangle((0.08,top-0.38),W-0.16,0.36,fc=col,ec=col))
        c.text(0.2,top-0.2,t,9.5,weight='bold',color='white',ha='left')
        c.box(W-1.45,top-0.34,1.25,0.28,hz,8,fc='white',ec='white',tc=col,weight='bold',round=0.05)
        rows=[('Lever:',lev,0.24),('What changes:',chg,0.52),('Why deferred:',why,0.36)]
        yy=top-0.46
        for lab,tx,hh in rows:
            c.text(0.2,yy-0.11,lab,8,weight='bold',color=col,ha='left')
            c.text(1.35,yy-hh/2,tx,8,w=5.75,h=hh,ha='left',color='#2c3e50')
            yy-=hh+0.04
        top=y-0.08
    by=0.08; c.ax.add_patch(Rectangle((0.05,by),W-0.1,0.8,fc='#eaeff2',ec=DK,lw=1.2))
    c.text(W/2,by+0.64,'What each strategy fixes (and what it does not)',9,weight='bold',color=DK)
    c.text(W/2,by+0.3,'(i)-(ii) move cohort AUROC. (iii)-(iv) leave AUROC unchanged but make the per-slide signal actionable for clinicians. None of the four resolves the AUPRC gap of Section 7.3.2 (low-prevalence ranking) on its own.',8,w=W-0.4,h=0.45,color='#333')
    c.save(OUT+'kras_inconclusive_strategies.png'); print(audit(c.fig),top)
kis()
