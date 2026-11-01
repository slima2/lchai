from fx import *
import numpy as np
OUT='../man_out/'
def keap1():
    W,H=7.2,6.6; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    c.text(W/2,H-0.25,'Pattern attention $\\neq$ pattern usefulness',11,weight='bold',w=W-0.3)
    c.text(W/2,H-0.65,'SHAP attribution to the pattern channel does not predict whether patterns help or hurt the slide-level prediction.',8.3,style='italic',color='#555',w=W-0.4,h=0.6)
    ax=c.fig.add_axes([0.11,0.30,0.86,0.55])
    ax.axhspan(0,16,color='#e8f3ea',alpha=.7,lw=0); ax.axhspan(-50,0,color='#fbe9e6',alpha=.7,lw=0)
    ax.axhline(0,color='#888',ls='--',lw=P(1))
    xs=np.array([0,70]); ax.plot(xs,xs*0.18,color='#999',ls=':',lw=P(1.2))
    pts=[('KRAS (41%, +7.6 pp)',41,7.6,'#c0392b',True,(41,12.4,'center')),('RBM10 (21%, +0.3 pp)',21,0.3,'#c0392b',False,(13.5,8.2,'center')),
         ('EGFR (24%, $-$0.5 pp)',24,-0.5,'#2e8b57',False,(26,-4.0,'left')),('STK11 (10%, $-$5.5 pp)',10,-5.5,'#c0392b',False,(10,-10.5,'center')),
         ('TP53 (39%, $-$16.1 pp)',39,-16.1,'#2e8b57',True,(41.5,-16.1,'left')),('KEAP1 (60%, $-$44.7 pp)',60,-44.7,'#c0392b',False,(58,-40.8,'right'))]
    for n,x,y,col,filled,(tx,ty,ha) in pts:
        ax.plot(x,y,'o',ms=P(9),mfc=col if filled else 'white',mec=col,mew=P(1.8),zorder=4)
        ax.text(tx,ty,n,fontsize=P(8.2),ha=ha,va='center',zorder=5)
    ax.set_xlim(0,70); ax.set_ylim(-50,16)
    ax.text(1,13.6,'PATTERNS HELP ($\\Delta_{pat}$ > 0)',fontsize=P(8.5),color='#2e8b57',fontweight='bold')
    ax.text(1,-47.5,'PATTERNS HURT ($\\Delta_{pat}$ < 0)',fontsize=P(8.5),color='#c0392b',fontweight='bold')
    ax.text(55,4.8,'expected if attention $\\Rightarrow$ utility',fontsize=P(8),color='#777',rotation=0,style='italic',ha='center')
    ax.text(3,-28,'KEAP1: most extreme attention-utility divergence.\nChoquet pair-bias mismatch on a spread profile:\nno superadditive pair to lock onto, so the pattern\nchannel adds noise that drowns the embedding signal.',fontsize=P(8.2),color='#c0392b',va='center',bbox=dict(boxstyle='round,pad=0.4',fc='#fdf1ef',ec='#c0392b',lw=1))
    ax.set_xlabel('SHAP attribution to pattern channel (% of total)',fontsize=P(8.8)); ax.set_ylabel('$\\Delta_{pat}$ = $P_{combined}$ $-$ $P_{emb\\text{-}only}$ (pp)',fontsize=P(8.8))
    ax.tick_params(labelsize=P(8.5))
    for s_ in ('top','right'): ax.spines[s_].set_visible(False)
    def mk(x,y,col,filled,lab):
        c.ax.plot(x,y,'o',ms=P(8),mfc=col if filled else 'white',mec=col,mew=P(1.6)); c.text(x+0.17,y,lab,8.2,ha='left')
    c.text(0.3,0.78,'Population label:',8.2,ha='left',weight='bold'); mk(2.1,0.78,'#2e8b57',True,'Conclusive'); mk(3.5,0.78,'#c0392b',True,'Inconclusive')
    c.text(0.3,0.38,'Slide outcome:',8.2,ha='left',weight='bold'); mk(2.1,0.38,'#444',True,'True positive'); mk(3.8,0.38,'#444',False,'False negative')
    c.save(OUT+'keap1_attention_vs_utility.png')
keap1()
