from fx import *
import numpy as np
from matplotlib.lines import Line2D
OUT='../man_out/'
D={'Cribriform':(55,7.5,2.2,'#1fb59a'),'Lepidic':(69,1.6,0.9,'#2f80c0'),'Acinar':(145,1.0,0.1,'#ef6351'),'Solid':(85,0.8,-0.4,'#8e44ad'),'Papillary':(100,2.0,-0.8,'#f5a623'),'Micropap.':(55,3.7,-1.1,'#2ca25f')}
def bvs():
    W,H=7.2,9.2; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    def mk(ax):
        ax.tick_params(labelsize=P(8.5),length=P(3)); ax.grid(alpha=.2,lw=P(.6))
        for s in ax.spines.values(): s.set_linewidth(P(.9))
        ax.axhspan(0,3,color='#e9f7ef',zorder=0); ax.axhspan(-1.75,0,color='#fdeeee',zorder=0); ax.axhline(0,color='#aaa',lw=P(1))
        ax.set_ylim(-1.75,3); ax.set_ylabel('V2 advantage over ArcFace (F1 pp)',fontsize=P(9))
    def lab(ax,x,y,t,col,ha='center',va='center'):
        ax.text(x,y,t,fontsize=P(8),ha=ha,va=va,color='#222',bbox=dict(fc='white',ec=col,boxstyle='round,pad=0.2',lw=P(.9)),zorder=6)
    # (a)
    a=c.fig.add_axes([0.85/W,(H-0.55-3.3)/H,5.9/W,3.3/H]); mk(a)
    a.set_xlim(-0.5,8.5)
    xs=np.linspace(0,8,2); a.plot(xs,-0.68+0.2975*xs,'--',color='#aaa',lw=P(1.4),zorder=2)
    for n,(t,am,adv,col) in D.items(): a.scatter([am],[adv],s=P(5.5+t*0.045)**2,color=col,edgecolor='#1b2a41',lw=P(1.2),zorder=5)
    lab(a,7.1,2.62,'Cribriform (55 tiles)','#1fb59a'); lab(a,1.6,1.32,'Lepidic (69 tiles)','#2f80c0')
    lab(a,1.35,0.1,'Acinar (145 tiles)','#ef6351','left'); lab(a,0.8,-0.95,'Solid (85 tiles)','#8e44ad')
    lab(a,2.35,-0.8,'Papillary (100 tiles)','#f5a623','left'); lab(a,4.05,-1.1,'Micropap. (55 tiles)','#2ca25f','left')
    a.text(5.3,1.95,'V2 leads',fontsize=P(8.5),style='italic',color='#2e8b57',ha='center'); a.text(7.4,-0.45,'ArcFace leads',fontsize=P(8.5),style='italic',color='#c0392b',ha='center')
    hs=[Line2D([0],[0],color='#aaa',ls='--',lw=1.4,label='Linear trend (r = 0.61)')]+[Line2D([0],[0],marker='o',ls='',mfc='#c5cad0',mec='#1b2a41',ms=P(5.5+t*0.045),label=f'{t} tiles') for t in (55,100,145)]
    a.legend(handles=hs,title='Bubble = training tiles',loc='upper left',ncol=2,fontsize=P(8),title_fontsize=P(8),frameon=True,framealpha=.95,labelspacing=0.7,borderpad=0.6,columnspacing=1.0)
    a.set_xlabel('Boundary ambiguity (inter-method F1 range, pp)',fontsize=P(9)); a.set_title('(a) V2 advantage vs boundary ambiguity',fontsize=P(9.5),fontweight='bold',pad=P(6))
    # (b)
    b=c.fig.add_axes([0.85/W,0.7/H,5.9/W,3.3/H]); mk(b); b.set_xlim(40,160)
    xs=np.array([40,160]); b.plot(xs,0.55-0.009*(xs-40),'--',color='#aaa',lw=P(1.4),zorder=2)
    for n,(t,am,adv,col) in D.items(): b.scatter([t],[adv],s=P(6.5+am*0.9)**2,color=col,edgecolor='#1b2a41',lw=P(1.2),zorder=5)
    lab(b,41.5,2.72,'Cribriform (ambig. 7.5 pp)','#1fb59a','left'); lab(b,62,1.3,'Lepidic (ambig. 1.6 pp)','#2f80c0','left')
    lab(b,158,0.45,'Acinar (ambig. 1.0 pp)','#ef6351','right'); lab(b,89,-0.47,'Solid (ambig. 0.8 pp)','#8e44ad','left')
    lab(b,104,-1.2,'Papillary (ambig. 2.0 pp)','#f5a623'); lab(b,41.5,-1.5,'Micropap. (ambig. 3.7 pp)','#2ca25f','left')
    b.text(57,0.2,'Same size (55 tiles)\nbut opposite effect!',fontsize=P(8.5),fontweight='bold',color='#c0392b',ha='center',va='center',bbox=dict(fc='#fde8e5',ec='#c0392b',boxstyle='round,pad=0.3',lw=P(1)),zorder=6)
    b.annotate('',xy=(52,0.62),xytext=(53.5,1.9),arrowprops=dict(arrowstyle='-|>',color='#c0392b',lw=P(1.4),connectionstyle='arc3,rad=0.0'),zorder=4)
    b.annotate('',xy=(54,-0.95),xytext=(57,-0.25),arrowprops=dict(arrowstyle='-|>',color='#c0392b',lw=P(1.4)),zorder=4)
    hs=[Line2D([0],[0],marker='o',ls='',mfc='#c5cad0',mec='#1b2a41',ms=P(6.5+am*0.9),label=l) for am,l in ((0.8,'Low ambiguity'),(2.0,'Medium'),(7.5,'High'))]
    b.legend(handles=hs,title='Bubble = boundary ambiguity',loc='upper right',fontsize=P(8),title_fontsize=P(8),frameon=True,framealpha=.95,labelspacing=0.9,borderpad=0.8)
    b.set_xlabel('Training tiles per class',fontsize=P(9)); b.set_title('(b) V2 advantage vs class size (r = −0.25)',fontsize=P(9.5),fontweight='bold',pad=P(6))
    c.save(OUT+'boundary_vs_size_v2.png'); print(audit(c.fig))
bvs()
