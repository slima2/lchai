from fx import *
import numpy as np
OUT='../man_out/'
def pen():
    W,H=7.2,9.8; c=Canvas(W,H,minpt=8.0)
    c.box(0.6,H-0.75,W-1.2,0.55,'Stage 2: Clinical slide pen marker and artefact rejection (hospital slides only; TCGA slides use Stages 0+1)',8.5,fc='#e4e4e4',ec='#bbb',round=0.15)
    c.box(2.3,H-1.85,2.6,0.8,'Tiles passing Stages 0+1 (tissue mask + quality checks)',8.5,fc='#d9f7e8',ec='#1a9a63',round=0.12)
    # blue cluster
    by=H-5.4
    c.ax.add_patch(FancyBboxPatch((0.15,by),W-0.3,3.05,boxstyle='round,pad=0,rounding_size=0.12',fc='#eef4ff',ec='#3b82f6',lw=1.4))
    c.text(W/2,by+2.85,'Colour-specific pen filters',9.5,weight='bold',color='#1e40af')
    items=[('Green marker','G > R+30, G > B+30\nReject if > 25% pixels','#8fe3a0','#2f9e4f'),
           ('Blue pen','B > R+40, B > G+30, B > 120\nReject if > 10% pixels','#8db8f5','#2f6fd0'),
           ('Red pen','R > 180, R > G+50, R > B+50\nReject if > 15% pixels','#f59a9a','#c0392b'),
           ('Olive / yellow','R > 150, G > 140, B < 80, R+G > 3.0B\nReject if > 20% pixels','#fbe08a','#c8a000'),
           ('Light blue / teal','Hue-specific\nReject if 20-50% pixels','#a8dcf5','#2a8fbf'),
           ('India ink','Intensity < 60, B > 0.8R\nReject if > 12% pixels','#a8abb3','#555')]
    bw=(W-0.3-0.4)/3
    for i,(t,d,fc,ec) in enumerate(items):
        r,cc=divmod(i,3)
        x=0.15+0.1+cc*(bw+0.1); y=by+1.4-r*1.3
        c.ax.add_patch(FancyBboxPatch((x,y),bw,1.2,boxstyle='round,pad=0,rounding_size=0.08',fc=fc,ec=ec,lw=1))
        c.text(x+bw/2,y+1.0,t,8.5,weight='bold',w=bw,h=0.3)
        c.text(x+bw/2,y+0.45,d,8,w=bw,h=0.85)
    # amber cluster
    ay=by-1.95
    c.ax.add_patch(FancyBboxPatch((0.15,ay),W-0.3,1.75,boxstyle='round,pad=0,rounding_size=0.12',fc='#fff3cc',ec='#e8a317',lw=1.4))
    c.text(W/2,ay+1.55,'Structural artefact filters',9.5,weight='bold',color='#92580a')
    bw2=(W-0.3-0.3)/2
    c.box(0.15+0.1,ay+0.15,bw2,1.1,'Straight-edge detection: gradient asymmetry > 3.0 (barcodes, labels, coverslip edges)',8.2,fc='#fdd35c',ec='#c8860a')
    c.box(0.15+0.2+bw2,ay+0.15,bw2,1.1,'Non-H&E colour cast: < 30% pixels with R > B+30 (incompatible stain)',8.2,fc='#fdd35c',ec='#c8860a')
    c.arrow(W/2,H-1.85,W/2,by+3.05+0.02,color='#3b82f6')
    # outputs
    oy=0.95
    c.box(0.6,oy,2.7,0.9,'Accepted tissue tiles (clean H&E only)',8.8,fc='#d9f7e8',ec='#1a9a63',weight='bold',tc='#0b5d3b')
    c.box(3.9,oy,2.7,0.9,'Rejected (pen / artefact)',8.8,fc='#fde2e2',ec='#c0392b',weight='bold',tc='#8b1d1d')
    c.arrow(1.95,ay,1.95,oy+0.92,color='#1a9a63'); c.arrow(5.25,ay,5.25,oy+0.92,color='#c0392b')
    c.text(2.45,(ay+oy+0.9)/2,'pass',8,color='#1a9a63',weight='bold'); c.text(5.75,(ay+oy+0.9)/2,'fail',8,color='#c0392b',weight='bold')
    c.text(W/2,0.45,'Calibrated on 12 hospital slides: < 1% false rejection of tissue tiles; rejects 25-40% additional tile candidates.',8.2,style='italic',color='#444',w=W-0.4,h=0.6)
    c.save(OUT+'pen_marker_filters.png')
def stk():
    W,H=7.2,9.9; c=Canvas(W,H,minpt=8.0)
    c.text(W/2,H-0.3,'Where does the STK11 signal go in LCHAI v2.0?',11.5,weight='bold',w=W-0.3)
    c.text(W/2,H-0.85,'STK11 biology splits into two routes: one captured weakly, one not at all; on a near-homogeneous slide the second route adds noise.',8.5,style='italic',color='#555',w=W-0.4,h=0.7)
    c.box(2.1,H-1.95,3.0,0.75,'STK11 mutation (LKB1 / immune modulator)',9,fc='#fff6d6',ec='#b8921a',weight='bold')
    LX,RX,CW=0.15,3.75,3.3
    c.arrow(3.2,H-1.95,LX+CW/2,H-2.5); c.arrow(4.0,H-1.95,RX+CW/2,H-2.5)
    c.text(LX+1.0,H-2.2,'Route 1:\nmicroenvironment',8.5,weight='bold',color='#1f3a5f',w=1.9)
    c.text(RX+CW-1.0,H-2.2,'Route 2: growth-pattern\nreorganisation',8.5,weight='bold',color='#1f3a5f',w=2.2)
    c.box(LX,H-3.7,CW,1.1,'Tumour-infiltrating lymphocytes decrease; stromal / supporting-tissue texture changes',8.5,fc='#fff6d6',ec='#b8921a')
    c.box(RX,H-3.7,CW,1.1,'STK11 does NOT reorganise tissue into any of the 6 ANORAK patterns (unlike TP53 / EGFR)',8.5,fc='#fbeceb',ec='#c0392b')
    c.arrow(LX+CW/2,H-3.7,LX+CW/2,H-3.95,color='#1f3a5f'); c.arrow(RX+CW/2,H-3.7,RX+CW/2,H-3.95,color='#c0392b')
    c.box(LX,H-5.15,CW,1.2,'CTransPath embedding (512-d tile features) captures fine-grained texture',8.5,fc='#eaf5ec',ec='#1f3a5f')
    c.box(RX,H-5.15,CW,1.2,'ANORAK 6-d vector on TCGA-49-AAR0: 98.68% micropapillary, so vector ~ one-hot and adds noise',8.5,fc='#fbeceb',ec='#c0392b')
    c.arrow(LX+CW/2,H-5.15,LX+CW/2,H-5.5,color='#b8921a'); c.arrow(RX+CW/2,H-5.15,RX+CW/2,H-5.5,color='#c0392b')
    c.box(LX+0.7,H-6.1,1.9,0.55,'PARTIAL',9.5,fc='#b8921a',ec='#b8921a',tc='white',weight='bold')
    c.box(RX+0.7,H-6.1,1.9,0.55,'CLOSED',9.5,fc='#c0392b',ec='#c0392b',tc='white',weight='bold')
    c.text(LX+CW/2,H-6.55,'faint STK11 signal preserved (Emb-only = 10.1%)',8.2,style='italic',color='#555',w=CW,h=0.6)
    c.text(RX+CW/2,H-6.55,'adds noise to the Choquet aggregator (Combined = 4.6%)',8.2,style='italic',color='#555',w=CW,h=0.6)
    c.ax.add_patch(FancyBboxPatch((0.15,1.55),W-0.3,1.15,boxstyle='round,pad=0,rounding_size=0.08',fc='#f5eddc',ec='#b8921a'))
    c.text(0.3,2.38,'Population level (cohort AUROC)',8.5,weight='bold',color='#6b5200',ha='left',w=3.0)
    c.text(0.3,1.98,'STK11 mean 5-fold AUROC = 0.658 (< 0.70)',8.5,ha='left',w=4.2)
    c.box(5.0,1.75,1.95,0.45,'Inconclusive',9,fc='#b8921a',ec='#b8921a',tc='white',weight='bold')
    c.ax.add_patch(FancyBboxPatch((0.15,0.25),W-0.3,1.15,boxstyle='round,pad=0,rounding_size=0.08',fc='#f6f6f6',ec='#bbb'))
    c.text(0.3,1.08,'This slide (mechanism, post hoc)',8.5,weight='bold',color='#1f3a5f',ha='left',w=3.2)
    c.text(0.3,0.68,'$\\Delta P$(mut) = $-$5.5 pp on TCGA-49-AAR0: explains the cohort AUROC, does not produce the label',8.3,ha='left',w=W-0.6,h=0.6)
    c.save(OUT+'stk11_signal_routes.png')
pen(); stk()
