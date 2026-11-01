import sys,os,glob
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
S=os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '.'
src=sys.argv[1:] or sorted(glob.glob('h/man_out/*.png'))
n=0
for p in src:
    name=os.path.basename(p)
    im=Image.open(p).convert('RGB')
    if im.width>2400: im=im.resize((2400,round(im.height*2400/im.width)),Image.LANCZOS)
    for tree in ('fullc','ovl'):
        d=f'{tree}/chapters/figures/'
        if not os.path.exists(d+name): print('NOT IN TREE',tree,name); continue
        im.save(d+name,optimize=True); n+=1
    # full-quality tree keeps the source-of-truth figure
    if os.path.exists('full/chapters/figures/'+name): Image.open(p).convert('RGB').save('full/chapters/figures/'+name,optimize=True)
print('installed',n)
