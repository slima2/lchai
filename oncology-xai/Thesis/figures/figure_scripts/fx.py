import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
PRINT_W=6.1
class Canvas:
    def __init__(s,W,H,frac=1.0,minpt=8.0):
        s.W,s.H=W,H; s.fig=plt.figure(figsize=(W,H),dpi=100)
        s.ax=s.fig.add_axes([0,0,1,1]); s.ax.set_xlim(0,W); s.ax.set_ylim(0,H); s.ax.axis('off')
        s.k=PRINT_W*frac/W   # printed pt per fig pt
        s.minfs=minpt/s.k; s.issues=[]
        s.fig.canvas.draw(); s.r=s.fig.canvas.get_renderer()
    def fs(s,printed): return printed/s.k
    def _wrap(s,line,maxw,fp):
        out=[];cur=''
        for w in line.split(' '):
            c=(cur+' '+w).strip() if cur else w
            if cur and s.r.get_text_width_height_descent(c,fp,False)[0]/s.fig.dpi>maxw: out.append(cur);cur=w
            else: cur=c
        out.append(cur);return out
    def text(s,x,y,txt,printed=8.5,w=None,h=None,ha='center',va='center',color='#222',weight='normal',style='normal',ls=1.15,pad=0.06,name=''):
        """printed = desired printed pt; auto-wrap to width w, shrink (not below minpt) to fit h."""
        f=max(s.fs(printed),s.minfs)
        while True:
            t=s.ax.text(x,y,txt,fontsize=f,ha=ha,va=va,color=color,fontweight=weight,fontstyle=style,linespacing=ls)
            if w is None: 
                s.fig.canvas.draw(); return t
            fp=t.get_fontproperties(); lines=[]
            for ln in txt.split('\n'): lines+=s._wrap(ln,w-2*pad,fp) if ln.strip() else ['']
            t.set_text('\n'.join(lines)); s.fig.canvas.draw()
            b=t.get_window_extent(s.r); bw=b.width/s.fig.dpi; bh=b.height/s.fig.dpi
            ok=bw<=w-2*pad+1e-3 and (h is None or bh<=h-2*pad+1e-3)
            if ok: return t
            t.remove()
            if f-0.5<s.minfs:
                t=s.ax.text(x,y,'\n'.join(lines),fontsize=s.minfs,ha=ha,va=va,color=color,fontweight=weight,fontstyle=style,linespacing=ls)
                s.issues.append((name or txt[:30],'overflow at min size')); return t
            f-=0.5
    def box(s,x,y,w,h,txt,printed=8.5,fc='#f3efe9',ec='#1f3a5f',tc='#222',weight='normal',lw=1.0,style='normal',ls='-',round=0.08,ha='center'):
        s.ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={round}',fc=fc,ec=ec,lw=lw,ls=ls))
        tx={'center':x+w/2,'left':x+0.1}[ha]
        return s.text(tx,y+h/2,txt,printed,w=w-(0 if ha=='center' else 0.0),h=h,color=tc,weight=weight,style=style,ha=ha,name=txt[:30])
    def arrow(s,x0,y0,x1,y1,color='#1f3a5f',lw=1.4):
        s.ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle='-|>',mutation_scale=11,color=color,lw=lw))
    def save(s,path,dpi=250):
        s.fig.savefig(path,dpi=dpi,facecolor='white'); 
        print(path,'issues:',s.issues)

import itertools
from matplotlib.text import Text
def audit(fig,minpt=None,k=None,tol=2):
    """report text overlaps, out-of-figure text and (optionally) texts below minpt printed"""
    fig.canvas.draw(); r=fig.canvas.get_renderer(); issues=[]
    ts=[]
    for t in fig.findobj(Text):
        if not(t.get_visible() and t.get_text().strip()): continue
        ax=getattr(t,'axes',None)
        if ax is not None and not ax.axison and t in (ax.get_xticklabels()+ax.get_yticklabels()): continue
        ts.append((t,t.get_window_extent(r)))
    W,H=fig.bbox.width,fig.bbox.height
    tl=set()
    for ax in fig.axes: tl|=set(ax.get_xticklabels())|set(ax.get_yticklabels())
    for t,b in ts:
        if t in tl: continue
        if b.x0<-1 or b.y0<-1 or b.x1>W+1 or b.y1>H+1: issues.append(('OUT',t.get_text()[:25]))
        if minpt and k and t.get_fontsize()*k<minpt-0.05: issues.append(('SMALL',t.get_text()[:20],round(t.get_fontsize()*k,1)))
    for (a,ba),(b,bb) in itertools.combinations(ts,2):
        w=min(ba.x1,bb.x1)-max(ba.x0,bb.x0); h=min(ba.y1,bb.y1)-max(ba.y0,bb.y0)
        if w>tol and h>tol: issues.append(('OVERLAP',a.get_text()[:20],b.get_text()[:20]))
    return issues
def _save(s,path,dpi=250):
    iss=audit(s.fig,8.0,s.k)
    s.fig.savefig(path,dpi=dpi,facecolor='white'); print(path,'fit-issues:',s.issues,'audit:',iss[:12])
Canvas.save=_save
