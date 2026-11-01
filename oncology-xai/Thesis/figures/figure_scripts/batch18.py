from fx import *
import numpy as np, re
OUT='../man_out/'
LOG='/home/claude/slima2/lchai/oncology-xai/Thesis/logs/pattern_classifier_results/output_optuna_fuzzyarcloss_search.txt'
fin={};pr=[]
for l in open(LOG):
    m=re.search(r'Trial (\d+) finished with value: ([\d.]+) and parameters: (\{.*?\})\.',l)
    if m: fin[int(m[1])]=(float(m[2]),eval(m[3]))
    m=re.search(r'Trial (\d+) pruned',l)
    if m: pr.append(int(m[1]))
best=max(fin,key=lambda i:fin[i][0]); bv=fin[best][0]; bp=fin[best][1]
def optuna():
    W,H=7.2,8.1; c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
    BL='#3a97d9'; RD='#e5533d'; PU='#a56cc1'
    def style(ax):
        ax.tick_params(labelsize=P(8.5),length=P(3)); ax.grid(alpha=.25,lw=P(.6))
        for s in ax.spines.values(): s.set_linewidth(P(.9))
    pw,ph=2.85,3.0
    pos=[(0.75,H-0.45-ph),(4.25,H-0.45-ph),(0.75,H-0.45-ph-1-ph),(4.25,H-0.45-ph-1-ph)]
    # (a)
    ax=c.fig.add_axes([pos[0][0]/W,pos[0][1]/H,pw/W,ph/H]); style(ax)
    ids=sorted(fin); ax.scatter(pr,[0.8815]*len(pr),marker='x',color='#c8c8c8',s=P(4.5)**2,lw=P(1),label='Pruned (40)',zorder=1)
    run=[];b=0
    for i in range(50):
        if i in fin and fin[i][0]>b: b=fin[i][0]
        run.append(b)
    ax.step(range(50),run,where='post',color=PU,lw=P(1.8),label='Best so far')
    ax.scatter(ids,[fin[i][0] for i in ids],color=BL,s=P(5.5)**2,zorder=3,label='Completed (10)')
    ax.scatter([best],[bv],color=RD,s=P(8)**2,edgecolor='#333',lw=P(1.2),zorder=4,label='Best (#30)')
    ax.set_ylim(0.878,0.972); ax.set_yticks([0.88,0.90,0.92,0.94]); ax.set_xlim(-2,51); ax.set_xlabel('Trial number',fontsize=P(9)); ax.set_ylabel('avgPR (validation)',fontsize=P(9))
    ax.legend(fontsize=P(8),loc='upper center',ncol=2,frameon=True,framealpha=.95,columnspacing=0.8,handletextpad=0.3,borderpad=0.4)
    ax.annotate('Best: trial #30\navgPR = 0.9306',xy=(best,bv),xytext=(31,0.9005),fontsize=P(8),color=RD,ha='center',va='center',bbox=dict(fc='#fde8e5',ec=RD,boxstyle='round,pad=0.25',lw=P(.8)),arrowprops=dict(arrowstyle='-|>',color=RD,lw=P(1)))
    ax.set_title('(a) Optuna search: 50 trials (TPE)',fontsize=P(9.5),fontweight='bold',pad=P(6))
    def sc(idx,key,ttl,xl,xlim,default,dlab,lab_txt,lab_pos,xt=None):
        ax=c.fig.add_axes([pos[idx][0]/W,pos[idx][1]/H,pw/W,ph/H]); style(ax)
        xs=[fin[i][1][key] for i in ids]; ys=[fin[i][0] for i in ids]
        ax.axvline(default,color='#999',ls=':',lw=P(1)); ax.axvline(bp[key],color='#f0a89d',ls='--',lw=P(1))
        ax.scatter(xs,ys,color=BL,s=P(5.5)**2,zorder=3); ax.scatter([bp[key]],[bv],color=RD,s=P(8)**2,edgecolor='#333',lw=P(1.2),zorder=4)
        ax.set_xlim(*xlim); ax.set_ylim(0.885,0.9395); ax.set_xlabel(xl,fontsize=P(9)); ax.set_ylabel('avgPR',fontsize=P(9))
        if xt is not None: ax.set_xticks(xt)
        ax.set_title(ttl,fontsize=P(9.5),fontweight='bold',pad=P(6))
        return ax
    ax=sc(1,'S_SCALE','(b) Scale s: high values work\nwith the fuzzy safety valve','Scale s',(10,55),30,'',None,None,[10,20,30,40,50])
    ax.text(29,0.937,'ArcFace\ndefault',fontsize=P(8),color='#666',ha='right',va='top')
    ax.text(44.5,0.9345,'s* = 46.1',fontsize=P(8),color=RD,ha='right',va='center',bbox=dict(fc='#fde8e5',ec=RD,boxstyle='round,pad=0.2',lw=P(.8)))
    ax=sc(2,'M_MARGIN','(c) Margin m: optimum near\nthe ArcFace default','Margin m (radians)',(0.05,0.85),0.5,'',None,None,[0.1,0.3,0.5,0.7])
    ax.text(0.49,0.8865,'ArcFace\ndefault',fontsize=P(8),color='#666',ha='right',va='bottom')
    ax.text(0.80,0.9345,'m* = 0.518',fontsize=P(8),color=RD,ha='right',va='center',bbox=dict(fc='#fde8e5',ec=RD,boxstyle='round,pad=0.2',lw=P(.8)))
    ax.annotate('m* close to\ndefault:\nmechanism,\nnot magnitude',xy=(0.505,0.9303),xytext=(0.24,0.9275),fontsize=P(8),color='#223',ha='center',va='center',bbox=dict(fc='#eef2f5',ec='#8a98a5',boxstyle='round,pad=0.25',lw=P(.8)),arrowprops=dict(arrowstyle='-|>',color='#223',lw=P(1)))
    ax=sc(3,'TAU','(d) Threshold τ: convergence\nto 0.448','Threshold τ',(0.1,0.9),0.5,'',None,None,[0.2,0.4,0.6,0.8])
    ax.text(0.505,0.9385,'Default',fontsize=P(8),color='#666',ha='left',va='top')
    ax.text(0.40,0.9345,'τ* = 0.448',fontsize=P(8),color=RD,ha='right',va='center',bbox=dict(fc='#fde8e5',ec=RD,boxstyle='round,pad=0.2',lw=P(.8)))
    ax.annotate('Top 2 trials:\nτ ≈ 0.44–0.45',xy=(0.44,0.9232),xytext=(0.27,0.9265),fontsize=P(8),color='#223',ha='center',va='center',bbox=dict(fc='#eef2f5',ec='#8a98a5',boxstyle='round,pad=0.25',lw=P(.8)),arrowprops=dict(arrowstyle='-|>',color='#223',lw=P(1)))
    c.save(OUT+'optuna_search_fuzzyarcloss_v2.png'); print(audit(c.fig))
optuna()
