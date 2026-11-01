"""Generate Visual Summary of the Thesis — Graphviz version with large fonts."""
import subprocess, pathlib

DOT = r"""
digraph thesis_summary {
    rankdir=LR;
    fontname="Helvetica"; fontsize=14;
    node [fontname="Helvetica", fontsize=13, style="filled,rounded", shape=box, margin="0.15,0.08"];
    edge [fontname="Helvetica", fontsize=10, color="#94A3B8"];
    newrank=true;
    ranksep=0.6;
    nodesep=0.35;
    splines=polyline;
    labeljust=c;

    // ══════════ HYPOTHESIS (top) ══════════
    subgraph cluster_hyp {
        label=""; style=invis;
        hyp [label="H: Structured domain knowledge — histological growth patterns encoded through fuzzy set theory —\ncan achieve (a) competitive performance under data scarcity (<700 slides)\nand (b) multi-level, clinically verifiable explanations.\nVerdict: partially supported — pattern utility is gene-dependent (Finding 2)",
             shape=box, fillcolor="#F8FAFC", color="#1E40AF", penwidth=2.5,
             fontsize=12, fontcolor="#1E293B"];
    }

    // ══════════ COL 1: Research Questions ══════════
    subgraph cluster_rqs {
        label="Research Questions"; labeljust=c;
        style="filled,rounded"; fillcolor="#EFF6FF"; color="#1E40AF";
        fontsize=15; fontcolor="#1E40AF";

        rq1 [label="RQ1\nFuzzy repr.\nlearning",     fillcolor="#3B82F6", fontcolor="white"];
        rq2 [label="RQ2\nPattern-informed\nMIL",      fillcolor="#2563EB", fontcolor="white"];
        rq3 [label="RQ3\nFuzzy Choquet\naggregation",  fillcolor="#1D4ED8", fontcolor="white"];
        rq4 [label="RQ4\nSix-level\ninterpretability", fillcolor="#7C3AED", fontcolor="white"];
        rq5 [label="RQ5\nData scarcity\nutility",      fillcolor="#6D28D9", fontcolor="white"];
        rq6 [label="RQ6\nOntology\nexplanations",     fillcolor="#0891B2", fontcolor="white"];
        rq7 [label="RQ7\nKG enrichment",              fillcolor="#0E7490", fontcolor="white"];

        rq1 -> rq2 -> rq3 -> rq4 -> rq5 -> rq6 -> rq7 [style=invis];
    }

    // ══════════ COL 2: Chapters ══════════
    subgraph cluster_chs {
        label="Chapters"; labeljust=c;
        style="filled,rounded"; fillcolor="#F0FDF4"; color="#166534";
        fontsize=15; fontcolor="#166534";

        ch2 [label="Ch. 2 — Background\nFuzzy sets, MIL, Choquet,\nCTransPath",           fillcolor="#16A34A", fontcolor="white"];
        ch3 [label="Ch. 3 — Use Case\nLUAD, 6 patterns,\n6 genes, TCGA",                  fillcolor="#15803D", fontcolor="white"];
        ch4 [label="Ch. 4 — Methodology\nFuzzyArcLoss V2, ABMIL,\nChoquet, 6-level",      fillcolor="#166534", fontcolor="white"];
        ch5 [label="Ch. 5 — Implementation\nLCHAI v2.0, fuzzy labels,\nKG, active learning", fillcolor="#14532D", fontcolor="white"];
        ch6 [label="Ch. 6 — Evaluation\n18-loss benchmark,\n6-gene AUROC, ablation",       fillcolor="#0F766E", fontcolor="white"];
        ch7 [label="Ch. 7 — Discussion\nRQ answers, limitations,\nfuzzy coherence",        fillcolor="#115E59", fontcolor="white"];

        ch2 -> ch3 -> ch4 -> ch5 -> ch6 -> ch7 [style=invis];
    }

    // ══════════ COL 3: Contributions ══════════
    subgraph cluster_contribs {
        label="Contributions"; labeljust=c;
        style="filled,rounded"; fillcolor="#FFF7ED"; color="#7C2D12";
        fontsize=15; fontcolor="#7C2D12";

        c1 [label="C1: FuzzyArcLoss V2\n(Artefact 1)",           fillcolor="#DC2626", fontcolor="white"];
        c2 [label="C2: PI-ABMIL\n(Artefact 2, ours)",            fillcolor="#EA580C", fontcolor="white"];
        c3 [label="C3: FC-MIL\n(Artefact 3, ours)",              fillcolor="#D97706", fontcolor="white"];
        c4 [label="C4: LCHAI v2.0\nPrototype",                   fillcolor="#0D9488", fontcolor="white"];
        c5 [label="C5: Gene-Dependent\nUtility (analytical)",     fillcolor="#CA8A04", fontcolor="white"];
        c6 [label="C6: Ontology\nExplanation Layer",              fillcolor="#65A30D", fontcolor="white"];

        c1 -> c2 -> c3 -> c4 -> c5 -> c6 [style=invis];
    }

    // ══════════ COL 4: Publications ══════════
    subgraph cluster_pubs {
        label="Publications"; labeljust=c;
        style="filled,rounded"; fillcolor="#F5F3FF"; color="#7C3AED";
        fontsize=15; fontcolor="#7C3AED";

        p1 [label="Lima et al.\n(2025) ESWA\nFuzzyArcLoss", fillcolor="#7C3AED", fontcolor="white"];
        p2 [label="Lima et al.\n(2020) IEEE\nExplainable\nfuzzy DL",   fillcolor="#6D28D9", fontcolor="white"];
        p3 [label="Lima et al.\n(2025) IEEE\nOntology\nretrieval",     fillcolor="#5B21B6", fontcolor="white"];

        p1 -> p2 -> p3 [style=invis];
    }

    // ══════════ EDGES: RQ → Chapters ══════════
    rq1 -> ch4 [color="#3B82F6"];
    rq2 -> ch4 [color="#2563EB"];
    rq3 -> ch4 [color="#1D4ED8"];
    rq4 -> ch5 [color="#7C3AED"];
    rq4 -> ch6 [color="#7C3AED", style=dashed];
    rq5 -> ch6 [color="#6D28D9"];
    rq5 -> ch7 [color="#6D28D9", style=dashed];
    rq6 -> ch4 [color="#0891B2"];
    rq6 -> ch5 [color="#0891B2"];
    rq7 -> ch5 [color="#0E7490"];
    rq7 -> ch6 [color="#0E7490", style=dashed];

    // ══════════ EDGES: Chapters → Contributions ══════════
    ch4 -> c1 [color="#DC2626"];
    ch4 -> c2 [color="#EA580C"];
    ch4 -> c3 [color="#D97706"];
    ch5 -> c4 [color="#0D9488"];
    ch6 -> c5 [color="#CA8A04"];
    ch5 -> c6 [color="#65A30D"];

    // ══════════ EDGES: Contributions → Publications ══════════
    c1 -> p1 [color="#7C3AED"];
    c2 -> p2 [color="#6D28D9"];
    c3 -> p2 [color="#6D28D9"];
    c6 -> p3 [color="#5B21B6"];

    // ══════════ ALIGNMENT ══════════
    {rank=same; rq1; ch2; c1; p1;}
    {rank=same; rq3; ch4; c3; p2;}
    {rank=same; rq5; ch6; c5; p3;}

    // ══════════ BOTTOM ══════════
    lchai [label="LCHAI v2.0: Lung Cancer Histologic Analysis with AI\nServio F. Lima Reina — University of Fribourg, Switzerland",
           fillcolor="#F0F9FF", color="#3B82F6", penwidth=1.5, fontsize=13, fontcolor="#1E293B"];

    ch7 -> lchai [style=invis];
    c6 -> lchai [style=invis];
}
"""

out = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\thesis_visual_summary.png"
dot_path = out.replace(".png", ".dot")

pathlib.Path(dot_path).write_text(DOT, encoding="utf-8")
subprocess.run(["dot", "-Tpng", "-Gdpi=200", dot_path, "-o", out], check=True)
print(f"Done: {out}")
