from fx import *
import numpy as np
W,H=7.2,8.6
c=Canvas(W,H,minpt=8.0); k=c.k; P=lambda p:p/k
# (a) membership functions
axa=c.fig.add_axes([0.11,0.585,0.84,0.34])
x=np.linspace(0,1,400)
def mu(x,tau): 
    return np.where(x<tau, 0.3+ (0.48-0.3)/0.448*x if tau==0.448 else 0.3+(0.9-0.3)/tau*x*0.0+ (0.5)*x/tau*0.0+0.3+0.5*x/tau*0.0, 0)
base=np.where(x<0.448,0.3+0.18*x/0.448,0.9+0.1*(x-0.448)/0.552)
axa.plot(x,base,color='#2c3e50',lw=P(2.2),label='V2 global ($\\tau$ = 0.448)')
for n,t,col,ls in [('Solid',0.55,'#8e44ad','--'),('Acinar',0.35,'#e74c3c','-.'),('Micropap.',0.30,'#27ae60',':'),('Cribriform',0.30,'#16a085',':')]:
    axa.axvline(t,color=col,ls=ls,lw=P(1.3),label=f'{n} ($\\tau_k$ = {t:.2f})')
axa.set_xlim(0,1); axa.set_ylim(0.25,1.08)
axa.set_xlabel('$|\\cos\\theta_{y_i}|$',fontsize=P(9)); axa.set_ylabel('Membership $\\mu_i$',fontsize=P(9)); axa.tick_params(labelsize=P(8.5))
axa.legend(fontsize=P(8.2),loc='lower right',frameon=True,framealpha=.95,borderpad=0.4)
axa.set_title('(a) Global V2 threshold vs per-class thresholds $\\tau_k$ (hard classes: lower $\\tau_k$)',fontsize=P(9),fontweight='bold',loc='left')
# (b)
axb=c.fig.add_axes([0.12,0.19,0.34,0.27])
axb.bar([0,1],[3,15],color=['#8e44ad','#e67e22'],width=0.55)
axb.set_xticks([0,1]); axb.set_xticklabels(['V2 (Optuna)\n3 params,\n50 trials','V2 ClassParams\n15 params,\n~300 trials'],fontsize=P(8.2))
axb.set_ylabel('Hyperparameters to optimise',fontsize=P(8.5)); axb.tick_params(axis='y',labelsize=P(8.5)); axb.set_ylim(0,18)
axb.text(0,3.4,'3',ha='center',fontsize=P(9.5),fontweight='bold'); axb.text(1,15.4,'15',ha='center',fontsize=P(9.5),fontweight='bold')
axb.text(1,8,'5x more',ha='center',fontsize=P(10),fontweight='bold',color='white')
axb.set_title('(b) Search space complexity',fontsize=P(9.2),fontweight='bold',loc='left')
for s_ in ('top','right'): axb.spines[s_].set_visible(False)
# (c)
axc=c.fig.add_axes([0.66,0.19,0.30,0.27])
names=['V2 (Optuna)','V1','ArcFace','V2 ClassParams','Softmax CE','SphereFace']; vals=[95.31,94.53,93.75,93.92,93.75,92.97]
cols=['#8e44ad','#9b59b6','#7f8c8d','#e67e22','#7f8c8d','#7f8c8d']
axc.barh(range(6)[::-1],vals,color=cols,height=0.6)
axc.set_yticks(range(6)[::-1]); axc.set_yticklabels([f'#{i+1} {n}' for i,n in enumerate(names)],fontsize=P(8.2))
axc.set_xlim(91,97.2); axc.set_xlabel('Macro-F1 (%), single run',fontsize=P(8.5)); axc.tick_params(axis='x',labelsize=P(8.5))
for i,v in enumerate(vals): axc.text(v+0.08,5-i,f'{v:.2f}',va='center',fontsize=P(8.2),fontweight='bold')
axc.set_title('(c) Single-run screening\n(top 6 of 18)',fontsize=P(9.2),fontweight='bold',loc='left')
for s_ in ('top','right'): axc.spines[s_].set_visible(False)
c.text(W/2,0.15,'V2 ClassParams (orange) is excluded from K-fold: 5x larger search space.',8.5,style='italic',color='#c0392b',w=6.8,h=0.4)
c.save('../man_out/fuzzyarcloss_v2_classparams.png')
