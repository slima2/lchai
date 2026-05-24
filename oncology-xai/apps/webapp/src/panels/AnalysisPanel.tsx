import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  api,
  getImages,
  uploadImage,
  processImage,
  getJob,
  getLatestResults,
  getResultBundle,
  getArtifacts,
  getArtifactUrl,
  getGeneAssociations,
  createPatient,
  createCase,
  deletePatient,
  deleteCase,
} from '../api';
import { clinicalAssocForGene } from '../data/geneClinicalAssociations';
import { useAuth } from '../auth/AuthProvider';
import {
  classifyInteraction,
  classifyShapleyProfile,
  classifyShapleyIndividual,
  classifySHAPBalance,
  classifyAttention,
  shapleyProfilePromptFragment,
  interactionPromptFragment,
  shapBalancePromptFragment,
} from '../fuzzyLabels';
import {
  PATTERN_COLORS,
  ANORAK_PATTERN_ORDER,
  patternColor,
  filterAllowedPatternResults,
  predominantPatternForDisplay,
  isDisallowedPatternName,
} from '../patternConstants';

/* ─────────────────────── constants ─────────────────────── */

const GENES_V2 = ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10'];

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English', es: 'Spanish', de: 'German', fr: 'French', pt: 'Portuguese',
};

const PMID_REFS: Record<string, { short: string; full: string }> = {
  'PMID:27738759': {
    short: 'Xu et al., 2017',
    full: 'Xu Y et al. Comprehensive study of mutational and clinicopathologic characteristics of adenocarcinoma with lepidic pattern in surgical resected lung adenocarcinoma. J Cancer Res Clin Oncol. 2017;143(12):2413–2421.',
  },
  'PMID:21252858': {
    short: 'Yoshizawa et al., 2011',
    full: 'Yoshizawa A et al. Impact of proposed IASLC/ATS/ERS classification of lung adenocarcinoma: prognostic subgroups and implications for further revision of staging. Mod Pathol. 2011;24(5):653–664.',
  },
  'PMID:36457500': {
    short: 'Zhang et al., 2022',
    full: 'Zhang Y et al. Genomic and clinicopathological features of lung adenocarcinomas with micropapillary component. Front Oncol. 2022;12:1004994.',
  },
  'PMID:21753699': {
    short: 'Yoshida et al., 2011',
    full: 'Yoshida A et al. Comprehensive histologic analysis of ALK-rearranged lung carcinomas. Am J Surg Pathol. 2011;35(8):1226–1234.',
  },
  'PMID:23619604': {
    short: 'Rekhtman et al., 2013',
    full: 'Rekhtman N et al. KRAS mutations are associated with solid growth pattern and tumor-infiltrating leukocytes in lung adenocarcinoma. Mod Pathol. 2013;26(10):1307–1319.',
  },
  'PMID:25079552': {
    short: 'TCGA Network, 2014',
    full: 'Cancer Genome Atlas Research Network. Comprehensive molecular profiling of lung adenocarcinoma. Nature. 2014;511:543–550.',
  },
  'PMID:24061507': {
    short: 'Kamata et al., 2013',
    full: 'Kamata T et al. Cribriform component in invasive lung adenocarcinoma is a recurrence-associated histological feature. Am J Surg Pathol. 2013;37(6):828–837.',
  },
};

const _explanationCache: Record<string, string> = {};

/* ─────────────────────── helpers ─────────────────────── */

const GENE_CURATED_PMIDS: Record<string, { pattern: string; pmid: string }[]> = {
  TP53: [
    { pattern: 'micropapillary', pmid: 'PMID:36457500' },
    { pattern: 'solid', pmid: 'PMID:25079552' },
  ],
  EGFR: [
    { pattern: 'lepidic', pmid: 'PMID:27738759' },
    { pattern: 'papillary', pmid: 'PMID:21252858' },
  ],
  KRAS: [
    { pattern: 'solid', pmid: 'PMID:23619604' },
  ],
  ALK: [
    { pattern: 'micropapillary', pmid: 'PMID:21753699' },
  ],
};

interface KgGeneInfo {
  gene: string;
  patternAssociation: string;
  treatmentImplications: string;
  citationNote: string;
  citations: { pattern: string; pmid: string; source: string }[];
}

function buildKgGeneInfo(gene: string, kgAssocData: any): KgGeneInfo {
  const assocs = kgAssocData?.associations as any[] | undefined;
  const fallback = clinicalAssocForGene(gene);
  const curatedFallback = (GENE_CURATED_PMIDS[gene] || []).map((c) => ({
    ...c, source: 'curated',
  }));

  if (!assocs) {
    return {
      gene,
      patternAssociation: fallback?.patternAssociation || 'Unknown',
      treatmentImplications: fallback?.treatmentImplications || 'Unknown',
      citationNote: fallback?.citationNote || '',
      citations: curatedFallback,
    };
  }

  const match = assocs.find((a: any) => a.gene === gene);
  if (!match) {
    return {
      gene,
      patternAssociation: fallback?.patternAssociation || 'Unknown',
      treatmentImplications: fallback?.treatmentImplications || 'Unknown',
      citationNote: fallback?.citationNote || '',
      citations: curatedFallback,
    };
  }

  const patterns = (match.patterns || []) as { pattern: string; provenance: string; source: string }[];
  const treatments = (match.treatments || []) as { treatment: string; provenance: string; source: string }[];

  let citations = patterns
    .filter((p) => p.provenance?.startsWith('PMID:'))
    .map((p) => ({ pattern: p.pattern, pmid: p.provenance, source: p.source }));

  if (citations.length === 0) {
    citations = curatedFallback;
  }

  return {
    gene,
    patternAssociation: patterns.map((p) => p.pattern).join(', ') || fallback?.patternAssociation || 'Unknown',
    treatmentImplications: treatments.map((t) => t.treatment).join(', ') || fallback?.treatmentImplications || 'Unknown',
    citationNote: 'Knowledge Graph (curated + DeepSearch)',
    citations,
  };
}

function buildNumberedRefs(citations: { pattern: string; pmid: string }[]): { refMap: Map<string, number>; refList: { num: number; pmid: string; full: string }[] } {
  const seen = new Map<string, number>();
  const refList: { num: number; pmid: string; full: string }[] = [];

  for (const c of citations) {
    if (!seen.has(c.pmid)) {
      const num = seen.size + 1;
      seen.set(c.pmid, num);
      const info = PMID_REFS[c.pmid];
      refList.push({
        num,
        pmid: c.pmid,
        full: info?.full || `${c.pmid}`,
      });
    }
  }
  return { refMap: seen, refList };
}

/* ─────────────────────── ArtifactImage ─────────────────────── */

function ArtifactImage({ uri, alt, className }: { uri: string; alt: string; className?: string }) {
  const [error, setError] = useState(false);
  const imgUrl = getArtifactUrl(uri);

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-50 text-gray-400 text-xs ${className || ''}`}>
        <div className="text-center">
          <svg className="w-8 h-8 mx-auto mb-1 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p>Image not available</p>
        </div>
      </div>
    );
  }

  return <img src={imgUrl} alt={alt} className={className} onError={() => setError(true)} />;
}

/* ─────────────────────── InteractiveOverlayImage ─────────────────────── */

function InteractiveOverlayImage({
  imageUri,
  regionMapUri,
  mode,
  patterns,
  className,
}: {
  imageUri: string;
  regionMapUri?: string;
  mode: 'pattern' | 'attention';
  patterns?: any[];
  className?: string;
}) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [regionMap, setRegionMap] = useState<any[] | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; data: any } | null>(null);
  const [imgError, setImgError] = useState(false);
  const imgUrl = getArtifactUrl(imageUri);

  useEffect(() => {
    if (regionMapUri) {
      const url = getArtifactUrl(regionMapUri);
      fetch(url)
        .then((r) => r.json())
        .then((data) => setRegionMap(data))
        .catch(() => setRegionMap(null));
    }
  }, [regionMapUri]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLImageElement>) => {
      if (!regionMap || !imgRef.current) {
        setTooltip(null);
        return;
      }
      const rect = imgRef.current.getBoundingClientRect();
      const xn = (e.clientX - rect.left) / rect.width;
      const yn = (e.clientY - rect.top) / rect.height;
      const hit = regionMap.find(
        (r: any) => xn >= r.xn && xn <= r.xn + r.wn && yn >= r.yn && yn <= r.yn + r.hn,
      );
      if (hit) {
        setTooltip({ x: e.clientX, y: e.clientY, data: hit });
      } else {
        setTooltip(null);
      }
    },
    [regionMap],
  );

  if (imgError) {
    return (
      <div className={`flex items-center justify-center bg-gray-50 text-gray-400 text-xs ${className || ''}`}>
        <div className="text-center">
          <svg className="w-8 h-8 mx-auto mb-1 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p>Image not available</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <img
        ref={imgRef}
        src={imgUrl}
        alt={mode === 'pattern' ? 'Pattern overlay' : 'ABMIL attention'}
        className={`${className || ''} cursor-crosshair`}
        onError={() => setImgError(true)}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
      />
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none shadow-lg rounded px-3 py-1.5 text-xs font-bold"
          style={{ left: tooltip.x + 14, top: tooltip.y - 34, backgroundColor: 'rgba(0,0,0,0.88)', color: '#fff' }}
        >
          {mode === 'pattern' && (() => {
            const p = tooltip.data.pattern;
            const pResult = patterns?.find((pr: any) => (pr.pattern || '').toLowerCase() === (p || '').toLowerCase());
            const pct = pResult?.percentage;
            return (
              <>
                <span className="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle" style={{ backgroundColor: patternColor(p) }} />
                <span className="capitalize">{p}</span>
                {pct != null && <span className="ml-1.5 font-mono text-gray-300">{pct.toFixed(1)}%</span>}
              </>
            );
          })()}
          {mode === 'attention' && (() => {
            const pct = tooltip.data.attention_percentile;
            const rank = tooltip.data.attention_rank;
            if (pct == null) return <span>Attention data unavailable</span>;
            const cl = classifyAttention(pct);
            return (
              <>
                <span className="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle" style={{ backgroundColor: cl.color }} />
                <span>{cl.label}</span>
                <span className="ml-1.5 font-mono text-gray-300">p{pct.toFixed(0)}</span>
                {rank != null && <span className="ml-1 text-gray-400">#{rank}</span>}
              </>
            );
          })()}
        </div>
      )}
    </>
  );
}

/* ─────────────────────── Citation rendering ─────────────────────── */

function renderExplanationWithCitations(
  text: string,
  refList: { num: number; pmid: string; full: string }[],
): React.ReactNode {
  if (!refList.length) return text;

  const pmidByNum = new Map(refList.map((r) => [r.num, r]));

  const parts = text.split(/(\[\d+(?:[,\s]*\d+)*\])/g);

  return parts.map((part, i) => {
    const match = part.match(/^\[([\d,\s]+)\]$/);
    if (!match) return <React.Fragment key={i}>{part}</React.Fragment>;

    const nums = match[1].split(/[,\s]+/).filter(Boolean).map(Number);
    return (
      <React.Fragment key={i}>
        {nums.map((n, j) => {
          const ref = pmidByNum.get(n);
          if (!ref) {
            return <sup key={`${i}-${n}`} className="text-blue-600 font-bold">[{n}]</sup>;
          }
          const pubmedUrl = `https://pubmed.ncbi.nlm.nih.gov/${ref.pmid.replace('PMID:', '')}/`;
          return (
            <React.Fragment key={`${i}-${n}`}>
              {j > 0 && <sup className="text-gray-400">,</sup>}
              <a
                href={pubmedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex text-blue-600 hover:text-blue-800 cursor-pointer"
                title={ref.full}
                style={{ textDecoration: 'none' }}
              >
                <sup className="font-bold hover:underline">[{n}]</sup>
              </a>
            </React.Fragment>
          );
        })}
      </React.Fragment>
    );
  });
}

/* ─────────────────────── LLM Explanation ─────────────────────── */

function AutoExplanation({
  gene,
  geneResult,
  language,
  patternResults,
  shapDecomp,
  kgInfo,
  morphProfile,
}: {
  gene: string;
  geneResult: any;
  language: string;
  patternResults: any[];
  shapDecomp: any;
  kgInfo: KgGeneInfo;
  morphProfile: any;
}) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const abl = geneResult?.ablation;
  const perm = geneResult?.permutation;
  const citationIds = kgInfo.citations.map((c) => c.pmid).sort().join(',');
  const cacheKey = `analysis_${gene}_${abl?.p_proposed}_${abl?.p_emb_only}_${language}_${citationIds}`;

  const { refMap, refList } = buildNumberedRefs(kgInfo.citations);

  useEffect(() => {
    if (!abl) return;
    if (_explanationCache[cacheKey]) {
      setExplanation(_explanationCache[cacheKey]);
      return;
    }

    setLoading(true);
    setExplanation(null);

    const score = ((geneResult.score || 0) * 100).toFixed(1);
    const pComb = ((abl.p_proposed || 0) * 100).toFixed(1);
    const pEmb = ((abl.p_emb_only || 0) * 100).toFixed(1);
    const pPat = ((abl.p_pat_only || 0) * 100).toFixed(1);
    const delta = (((abl.p_proposed || 0) - (abl.p_emb_only || 0)) * 100).toFixed(1);
    const patternsHelp = (abl.p_proposed || 0) > (abl.p_emb_only || 0);

    const topPatterns = [...patternResults]
      .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
      .slice(0, 4);
    const patternSummary = topPatterns
      .map((p: any) => `${p.pattern} (${(p.percentage || 0).toFixed(1)}%)`)
      .join(', ');

    const shapEmbPct = shapDecomp?.embedding_contribution_pct?.toFixed(1) ?? '?';
    const shapPatPct = shapDecomp?.pattern_contribution_pct?.toFixed(1) ?? '?';
    const topShapPatterns = (shapDecomp?.top_pattern_dims || [])
      .filter((p: string) => !isDisallowedPatternName(p))
      .join(', ');

    const litLines = kgInfo.citations.length > 0
      ? kgInfo.citations.map((c) => {
          const refNum = refMap.get(c.pmid) || '?';
          return `- ${c.pattern} is associated with ${gene} mutations [${refNum}]`;
        }).join('\n')
      : `No specific pattern–${gene} associations in the current knowledge graph.`;

    const refsText = refList.map((r) => `[${r.num}] ${r.full}`).join('\n');

    const shapBalLabel = shapDecomp ? classifySHAPBalance(shapDecomp.pattern_contribution_pct || 0).label : 'Unknown';

    const langInstruction = language !== 'en'
      ? `\n\nCRITICAL: Respond ENTIRELY in ${LANGUAGE_NAMES[language] || language}. All text, including the disclaimer, must be in ${LANGUAGE_NAMES[language] || language}.`
      : '';

    const prompt = `You are an expert computational pathologist explaining AI mutation prediction results for lung adenocarcinoma to a clinician. Generate a structured, evidence-based explanation (8–12 sentences).

Gene: ${gene}
Mutation probability: P(mut) = ${score}%
Confidence: ${geneResult.confidence_label || 'unknown'} (model AUROC = ${(abl.proposed_auroc || 0).toFixed(3)})
Prediction method: ${geneResult.prediction_method || 'unknown'}

KNOWLEDGE GRAPH — LITERATURE ASSOCIATIONS:
${litLines}

THIS SLIDE'S MORPHOLOGY:
Pattern composition: ${patternSummary}

${shapDecomp ? shapBalancePromptFragment(shapDecomp.pattern_contribution_pct || 0) : ''}

SHAP DECOMPOSITION (attribution analysis):
- Embedding features (512-d CTransPath): ${shapEmbPct}%
- Pattern features (6-class histological): ${shapPatPct}%
- System classification: "${shapBalLabel}" (fuzzy logic — use this exact label)
${topShapPatterns ? `- Top contributing pattern dims: ${topShapPatterns}` : ''}
IMPORTANT — EXPLAIN EMBEDDINGS TO THE READER: The 512-dimensional embedding is a compact numerical representation of each tissue tile extracted by CTransPath, a deep learning model pretrained on 15 million histopathological image patches. These 512 numbers encode visual features that a pathologist would recognize: nuclear size, shape and density; chromatin texture and staining intensity; glandular architecture and lumen formation; stromal composition and fibrosis; cell-to-cell spatial arrangement; and mitotic activity. Unlike the 6 pattern features (which are explicitly labeled growth patterns), the embedding captures a much richer set of morphological details that are not tied to any predefined category. When you explain the SHAP balance, briefly clarify this distinction so the reader understands what "embedding features" means in practical terms.

ABLATION STUDY (three independently trained models, each producing its own P(mut)):
- Combined model (embeddings+patterns, 518-d): P(mut) = ${pComb}%
- Embedding-only model (512-d): P(mut) = ${pEmb}%
- Pattern-only model (6-d): P(mut) = ${pPat}%
- Delta (Combined − Emb-only): ${delta}pp → Patterns ${parseFloat(delta) > 2 ? 'HELP (constructive)' : parseFloat(delta) < -2 ? 'HURT (destructive interference)' : 'are NEUTRAL (minimal effect)'}
NOTE: These are outputs from THREE DIFFERENT MODELS, not components of a single prediction. The P(mut) in the header (${score}%) comes from the gene-optimal method (${geneResult.prediction_method || 'unknown'}), which may correspond to one of these bars or to a different architecture (e.g., Fuzzy Choquet).

YOUR EXPLANATION MUST:
1. State P(mut) = ${score}% for ${gene} and whether this is conclusive or inconclusive.
2. Describe the SHAP balance using the system label "${shapBalLabel}": patterns account for ${shapPatPct}% of total attribution. Explain what this means.
3. Interpret the ablation: three separately trained models produce ${pComb}%, ${pEmb}%, ${pPat}%. ${patternsHelp ? `Adding patterns improves the prediction by +${delta}pp.` : `Adding patterns reduces the prediction by ${Math.abs(parseFloat(delta)).toFixed(1)}pp — they interfere.`} These values differ from P(mut)=${score}% because P(mut) comes from the gene-optimal model.
4. Compare this slide's patterns (${patternSummary}) to literature expectations for ${gene}. Use numbered citations [1], [2] etc.
5. ${parseFloat(score) < 50 ? `The prediction is LOW. State: "A low P(mut) does not rule out the mutation — it means the model found insufficient morphological signal on this slide."` : `The prediction is elevated. Explain the morphological evidence supporting it.`}
6. ${geneResult.confidence_label === 'Inconclusive' ? 'State clearly that molecular testing is REQUIRED because the model AUROC is below the reliability threshold.' : 'Note that while the model is considered reliable for this gene, molecular confirmation is still recommended.'}
7. End with: "This analysis is generated by the LCHAI v2.0 research system (THESIS_INTERNAL evidence). It is for decision support only and must not replace molecular diagnosis or clinical judgment."

${refsText ? `REFERENCES (cite using brackets):\n${refsText}` : ''}

Do NOT use "diagnose", "confirmed", or "definitive".${langInstruction}`;

    api.post('/gene-explain', { gene, prompt, language })
      .then((r) => {
        const txt = r.data?.explanation;
        if (txt) {
          _explanationCache[cacheKey] = txt;
          setExplanation(txt);
        } else {
          setFallback();
        }
        setLoading(false);
      })
      .catch(() => {
        setFallback();
        setLoading(false);
      });

    function setFallback() {
      const fb = `P(mut) = ${score}% for ${gene} (${geneResult.confidence_label || 'unknown'}). ` +
        `SHAP attribution: embeddings ${shapEmbPct}%, patterns ${shapPatPct}%. ` +
        `Ablation: Combined ${pComb}%, Emb-only ${pEmb}%, Pat-only ${pPat}% ` +
        `(delta ${delta}pp — patterns ${patternsHelp ? 'help' : 'hurt'}). ` +
        `Slide patterns: ${patternSummary}. ` +
        `Literature expects ${kgInfo.patternAssociation} for ${gene}. ` +
        `LCHAI v2.0 research tool — not for clinical diagnosis.`;
      _explanationCache[cacheKey] = fb;
      setExplanation(fb);
    }
  }, [cacheKey]);

  return (
    <div>
      {loading && (
        <div className="flex items-center gap-2 text-gray-400 py-4">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Generating explanation...</span>
        </div>
      )}
      {explanation && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
          {renderExplanationWithCitations(explanation, refList)}
        </div>
      )}
      {refList.length > 0 && (
        <div className="mt-3 bg-gray-50 border border-gray-200 rounded p-3">
          <h5 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">References</h5>
          <ol className="list-none text-xs text-gray-600 space-y-0.5">
            {refList.map((r) => (
              <li key={r.pmid}>
                <span className="font-bold text-gray-800">[{r.num}]</span>{' '}
                <a
                  href={`https://pubmed.ncbi.nlm.nih.gov/${r.pmid.replace('PMID:', '')}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline text-blue-600"
                >
                  {r.full}
                </a>
              </li>
            ))}
          </ol>
        </div>
      )}
      {!loading && !explanation && (
        <p className="text-gray-400 text-sm py-2">No explanation available.</p>
      )}
    </div>
  );
}

/* ─────────────────────── Choquet section (conditional) ─────────────────────── */

function ChoquetSection({
  gene,
  geneResult,
  choquetData,
  caseId,
  language,
  kgInfo,
}: {
  gene: string;
  geneResult: any;
  choquetData: any;
  caseId: string;
  language: string;
  kgInfo: KgGeneInfo;
}) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!choquetData?.shapley_values) return null;

  const svEntries = Object.entries(choquetData.shapley_values as Record<string, number>)
    .filter(([pattern]) => !isDisallowedPatternName(pattern))
    .sort(([, a], [, b]) => (b as number) - (a as number));
  const maxVal = Math.max(...svEntries.map(([, v]) => v as number), 0.001);
  const uniform = 1.0 / svEntries.length;

  const handleExplain = async () => {
    const cacheKey = `choquet_v2_${gene}_${caseId}_${language}`;
    if (_explanationCache[cacheKey]) {
      setExplanation(_explanationCache[cacheKey]);
      return;
    }
    setLoading(true);
    try {
      const svObj = Object.fromEntries(svEntries.filter(([p]) => !isDisallowedPatternName(p)));
      const fuzzyProfileFrag = shapleyProfilePromptFragment(svObj);
      const fuzzyIxFrag = choquetData.interaction_indices
        ? interactionPromptFragment(
            Object.fromEntries(
              Object.entries(choquetData.interaction_indices as Record<string, number>)
                .filter(([pair]) => { const ps = pair.split('_'); return ps.length >= 2 && !isDisallowedPatternName(ps[0]) && !isDisallowedPatternName(ps[1]); })
            )
          )
        : 'No interaction indices available.';

      const langInst = language !== 'en'
        ? `\n\nCRITICAL: Respond ENTIRELY in ${LANGUAGE_NAMES[language] || language}.`
        : '';

      const prob = ((geneResult.score || 0) * 100).toFixed(1);
      const abl = geneResult?.ablation;
      const ablDelta = abl ? (((abl.p_proposed || 0) - (abl.p_emb_only || 0)) * 100).toFixed(1) : '?';

      const prompt = `You are explaining a Fuzzy Choquet integral analysis to a pathologist. Be mathematically precise but clinically clear (max 300 words).

Gene: ${gene}, P(mut) = ${prob}%
Literature pattern associations: ${kgInfo.patternAssociation}

MATHEMATICAL CONTEXT (you MUST explain this clearly):
- The Choquet integral aggregates the 6 pattern scores using a learned fuzzy measure (non-additive set function).
- Singleton Shapley values decompose the fuzzy measure into per-pattern importance weights. They ALWAYS sum to 1.0.
- Uniform baseline = ${(1 / svEntries.length).toFixed(4)} (= 1/${svEntries.length}). If all values equal this, the measure is additive (equivalent to a simple average).
- These values are NOT in the same units as P(mut). They are weights in [0, 1] that shape HOW pattern scores are aggregated. They do not directly add or subtract from P(mut).
- The causal chain is: pattern_scores → Choquet_aggregation(fuzzy measure) → concat with embeddings → classifier → P(mut).

${fuzzyProfileFrag}

${fuzzyIxFrag}

YOUR EXPLANATION MUST use the exact fuzzy labels provided above (e.g., "Uniform", "Moderate Synergy"). These labels are computed by the system using fuzzy membership functions and MUST NOT be changed or paraphrased. This ensures the explanation is deterministic and cannot hallucinate intensity levels.

1. State the Shapley profile classification and what it means for this gene's prediction mechanism.
2. For each interaction, use the system label (e.g., "Moderate Synergy between lepidic × solid") and explain the morphological implication.
3. Clarify that these values shape the aggregation mechanism, not P(mut) directly. A "${classifyShapleyProfile(svObj).label}" profile means ${classifyShapleyProfile(svObj).label === 'Uniform' || classifyShapleyProfile(svObj).label === 'Near-Uniform' ? 'the Choquet integral behaves like a simple average and the prediction relies on overall pattern distribution rather than learned preferences.' : 'the model has identified specific patterns as more important for this gene.'}
4. Compare observed pattern importance to literature expectations for ${gene} (${kgInfo.patternAssociation}).
5. If ablation shows patterns help by +${ablDelta}pp, note the Choquet measure explains the mechanism.

Do NOT say "diagnose" or "confirmed".${langInst}`;


      const resp = await api.post(`/cases/${caseId}/graph/explain`, { language, extra_context: prompt });
      const text = resp.data?.explanation || 'Explanation not available.';
      _explanationCache[cacheKey] = text;
      setExplanation(text);
    } catch (e: any) {
      setExplanation(`Could not generate: ${e?.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border rounded-lg shadow-sm overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-2">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-bold text-amber-900 text-sm">
              Fuzzy Choquet MIL — Pattern Importance ({gene})
            </h4>
            <p className="text-[10px] text-amber-700">
              Patterns contribute positively to this prediction — Choquet analysis is relevant.
            </p>
          </div>
          {(() => {
            const svObj = Object.fromEntries(svEntries.filter(([p]) => !isDisallowedPatternName(p)));
            const profile = classifyShapleyProfile(svObj);
            return (
              <span className="px-2.5 py-1 rounded text-[11px] font-bold" style={{ backgroundColor: profile.color + '25', color: profile.color, border: `1px solid ${profile.color}40` }}>
                Profile: {profile.label}
              </span>
            );
          })()}
        </div>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-2 gap-6">
          {/* Shapley values */}
          <div>
            <h5 className="text-xs font-semibold text-gray-600 mb-2">Singleton Shapley Values</h5>
            <div className="space-y-1">
              {svEntries.map(([pattern, val]) => {
                const delta = (val as number) - uniform;
                const indLabel = classifyShapleyIndividual(val as number, svEntries.length);
                return (
                  <div key={pattern} className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: patternColor(pattern) }} />
                    <span className="text-xs w-24 capitalize">{pattern}</span>
                    <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                      <div className="h-full rounded" style={{
                        width: `${Math.min(((val as number) / maxVal) * 100, 100)}%`,
                        backgroundColor: patternColor(pattern),
                        opacity: 0.7,
                      }} />
                    </div>
                    <span className="text-xs font-mono w-14">{(val as number).toFixed(4)}</span>
                    <span className={`text-[10px] font-mono w-14 ${delta > 0.002 ? 'text-sky-600' : delta < -0.002 ? 'text-rose-600' : 'text-gray-400'}`}>
                      {delta > 0 ? '+' : ''}{(delta * 100).toFixed(2)}%
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: indLabel.color + '20', color: indLabel.color }}>
                      {indLabel.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          {/* Interaction indices */}
          <div>
            <h5 className="text-xs font-semibold text-gray-600 mb-2">Interaction Indices</h5>
            {choquetData.interaction_indices && Object.keys(choquetData.interaction_indices).length > 0 ? (
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="border px-2 py-1 text-left">Pair</th>
                    <th className="border px-2 py-1 text-right">Index</th>
                    <th className="border px-2 py-1 text-center">Classification</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(choquetData.interaction_indices as Record<string, number>)
                    .filter(([pair]) => {
                      const parts = pair.split('_');
                      return parts.length >= 2 && !isDisallowedPatternName(parts[0]) && !isDisallowedPatternName(parts[1]);
                    })
                    .sort(([, a], [, b]) => Math.abs(b as number) - Math.abs(a as number))
                    .map(([pair, val]) => {
                      const [p1, p2] = pair.split('_');
                      const cl = classifyInteraction(val as number);
                      return (
                        <tr key={pair} className="hover:bg-gray-50">
                          <td className="border px-2 py-1 capitalize">
                            <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: patternColor(p1) }} />
                            {p1}
                            <span className="text-gray-400 mx-1">×</span>
                            <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: patternColor(p2) }} />
                            {p2}
                          </td>
                          <td className="border px-2 py-1 text-right font-mono">{(val as number).toFixed(4)}</td>
                          <td className="border px-2 py-1 text-center">
                            <span className="font-bold text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: cl.color + '20', color: cl.color }}>
                              {cl.label} {cl.direction === 'Synergy' ? '↑' : '↓'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            ) : (
              <span className="text-xs text-gray-400">No significant interactions</span>
            )}
          </div>
        </div>
        <div className="mt-3">
          <button
            className="px-3 py-1.5 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 disabled:opacity-50"
            onClick={handleExplain}
            disabled={loading}
          >
            {loading ? 'Generating...' : 'Explain Choquet values with AI'}
          </button>
          {explanation && (
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded p-4 text-sm leading-relaxed text-amber-950 whitespace-pre-wrap">
              {explanation}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────── Gene Analysis View ─────────────────────── */

function GeneAnalysisView({
  gene,
  geneResult,
  bundle,
  artifacts,
  aurocValues,
  aurocThreshold,
  language,
  kgInfo,
}: {
  gene: string;
  geneResult: any;
  bundle: any;
  artifacts: any[];
  aurocValues: Record<string, number>;
  aurocThreshold: number;
  language: string;
  kgInfo: KgGeneInfo;
}) {
  const geneAuroc = aurocValues[gene] ?? 0;
  const isConcl = geneAuroc >= aurocThreshold;
  const score = (geneResult?.score || 0);
  const scorePct = (score * 100).toFixed(1);
  const shapDecomp = geneResult?.shap_decomposition;
  const choquetData = geneResult?.choquet_shapley;
  const abl = geneResult?.ablation;
  const patterns = filterAllowedPatternResults(bundle?.pattern_results || []);
  const mp = bundle?.morphologic_profile;
  const caseId = bundle?.case_id || '';

  const patternsHelpPrediction = abl && (abl.p_proposed || 0) > (abl.p_emb_only || 0);

  // PATTERN OVERLAY panel must show the PURE pattern overlay (no attention contours), so the
  // visual on the left answers "where is each tissue pattern?" and the visual on the right
  // (ABMIL Attention Heatmap) answers "where does the MIL look?". Combined overlay (patterns +
  // attention contours) lives in the Viewer tab where the user can toggle it explicitly.
  const roiArt = artifacts.find((a: any) => a.artifact_type === 'roi_overlay');
  const attnArt = artifacts.find((a: any) => a.artifact_type === 'attention_overlay');
  const patternRegionArt = artifacts.find((a: any) => a.artifact_type === 'pattern_region_map');
  const attentionRegionArt = artifacts.find((a: any) => a.artifact_type === 'attention_region_map');

  return (
    <div className="space-y-5">
      {/* ── Gene Header ── */}
      <div className={`p-3 rounded-lg flex items-center justify-between ${
        isConcl ? 'bg-sky-50 border border-sky-200' : 'bg-yellow-50 border border-yellow-200'
      }`}>
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold">{gene}</span>
          <span className={`px-2.5 py-1 rounded text-xs font-bold ${
            isConcl ? 'bg-sky-200 text-sky-900' : 'bg-yellow-200 text-yellow-800'
          }`}>
            {isConcl ? 'Conclusive' : 'Inconclusive'}
          </span>
          <span className="text-xs text-gray-500">
            via {geneResult?.prediction_method || 'unknown'} | AUROC {geneAuroc.toFixed(3)}
          </span>
        </div>
        <span className="text-lg font-mono font-bold">
          P(mut) = {scorePct}%
        </span>
      </div>

      {!isConcl && (
        <div className="bg-yellow-50 border border-yellow-300 rounded p-2 text-xs text-yellow-800">
          ⚠ Molecular testing recommended — {gene} has AUROC {geneAuroc.toFixed(3)} &lt; {aurocThreshold.toFixed(3)}, prediction cannot be considered reliable from histology alone.
        </div>
      )}

      {/* ── Visual Grid: Pattern Overlay + ABMIL Attention ── */}
      <div className="grid grid-cols-2 gap-4">
        <div className="border rounded-lg overflow-hidden">
          <div className="bg-emerald-50 border-b border-emerald-200 px-3 py-1.5">
            <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wide">Pattern Overlay</h4>
          </div>
          <div className="bg-gray-100 h-64 flex items-center justify-center relative">
            {roiArt ? (
              <InteractiveOverlayImage
                imageUri={roiArt.uri}
                regionMapUri={patternRegionArt?.uri}
                mode="pattern"
                patterns={patterns}
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <span className="text-gray-400 text-xs">Not available</span>
            )}
          </div>
          <div className="px-3 py-2 border-t bg-white">
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px]">
              {ANORAK_PATTERN_ORDER.map((p) => {
                const c = PATTERN_COLORS[p];
                const pResult = patterns.find((pr: any) => (pr.pattern || '').toLowerCase() === p);
                const pct = pResult?.percentage ?? (mp as any)?.[`pct_${p}`] ?? 0;
                return (
                  <span key={p} className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: c }} />
                    <span className="capitalize font-medium">{p}</span>
                    <span className="font-mono text-gray-500">{pct.toFixed(1)}%</span>
                  </span>
                );
              })}
            </div>
          </div>
        </div>

        <div className="border rounded-lg overflow-hidden">
          <div className="bg-orange-50 border-b border-orange-200 px-3 py-1.5">
            <h4 className="text-xs font-bold text-orange-900 uppercase tracking-wide">ABMIL Attention Heatmap</h4>
          </div>
          <div className="bg-gray-100 h-64 flex items-center justify-center relative">
            {attnArt ? (
              <InteractiveOverlayImage
                imageUri={attnArt.uri}
                regionMapUri={attentionRegionArt?.uri}
                mode="attention"
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <span className="text-gray-400 text-xs">Not available</span>
            )}
          </div>
          <div className="px-3 py-1.5 text-[10px] text-gray-500 border-t">
            Hover over tiles to see fuzzy attention level. Top-200 tiles by gated attention weight.
          </div>
        </div>
      </div>

      {/* ── Charts: SHAP Decomposition + Ablation Comparison ── */}
      {abl && (
        <div className="grid grid-cols-2 gap-4">
          {/* SHAP Decomposition */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-indigo-50 border-b border-indigo-200 px-3 py-1.5">
              <h4 className="text-xs font-bold text-indigo-900 uppercase tracking-wide">SHAP Decomposition — {gene}</h4>
            </div>
            <div className="p-4">
              {shapDecomp ? (
                <>
                  <div className="h-10 rounded overflow-hidden flex bg-gray-100">
                    <div
                      className="bg-blue-600 flex items-center justify-center text-white text-xs font-bold"
                      style={{ width: `${shapDecomp.embedding_contribution_pct}%` }}
                    >
                      Emb {shapDecomp.embedding_contribution_pct?.toFixed(1)}%
                    </div>
                    <div
                      className="bg-red-500 flex items-center justify-center text-white text-xs font-bold"
                      style={{ width: `${shapDecomp.pattern_contribution_pct}%` }}
                    >
                      Pat {shapDecomp.pattern_contribution_pct?.toFixed(1)}%
                    </div>
                  </div>
                  <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                    <span>Embeddings (512-d CTransPath)</span>
                    <span>Patterns (6 classes)</span>
                  </div>
                  {shapDecomp.top_pattern_dims?.length > 0 && (() => {
                    const signedMap = (shapDecomp.pattern_shap_signed || {}) as Record<string, number>;
                    const allowedAbs = Object.entries(signedMap)
                      .filter(([p]) => !isDisallowedPatternName(p))
                      .map(([, v]) => Math.abs(v as number));
                    const maxAbs = allowedAbs.length > 0 ? Math.max(...allowedAbs) : 0;
                    // Drop patterns whose |signed SHAP| is numerical noise.
                    //   - ABSOLUTE_FLOOR: anything that would render as "0.0000" (4 decimals) is treated as
                    //     literally zero — showing it as "top contributing" is misleading.
                    //   - RELATIVE_THRESHOLD: 5% of the largest magnitude in this gene — guards against
                    //     showing a 0.001 next to a 0.500 as if both mattered.
                    const ABSOLUTE_FLOOR = 5e-4;            // |val| < 0.0005 ⇒ rounds to "0.0000"
                    const RELATIVE_THRESHOLD = 0.05 * maxAbs;
                    const isNoise = (val: number | undefined): boolean => {
                      if (val == null) return true;
                      const a = Math.abs(val);
                      if (a < ABSOLUTE_FLOOR) return true;
                      if (maxAbs > 0 && a < RELATIVE_THRESHOLD) return true;
                      return false;
                    };
                    const visible: string[] = (shapDecomp.top_pattern_dims as string[])
                      .filter((p: string) => !isDisallowedPatternName(p))
                      .filter((p: string) => !isNoise(signedMap[p]));
                    if (visible.length === 0) {
                      return (
                        <div className="mt-2 text-[10px] text-gray-400 italic">
                          No individual pattern contributes meaningfully for this gene
                          (all |signed SHAP| &lt; {ABSOLUTE_FLOOR.toExponential(0)}).
                        </div>
                      );
                    }
                    return (
                      <div className="mt-2 text-[10px] text-gray-500">
                        Top contributing:{' '}
                        {visible.map((p: string) => {
                          const dir = shapDecomp.pattern_shap_directions?.[p];
                          const val = signedMap[p] as number;
                          const isPos = dir === 'positive' || val > 0;
                          const isNeg = dir === 'negative' || val < 0;
                          const arrow = isPos ? '▲' : isNeg ? '▼' : '•';
                          const arrowColor = isPos ? 'text-emerald-600' : isNeg ? 'text-rose-600' : 'text-gray-400';
                          const directionText = isPos
                            ? 'pushes toward mutated (+)'
                            : isNeg ? 'pushes toward wild-type (−)'
                            : 'neutral';
                          const title = `${p}: signed SHAP = ${val.toFixed(4)} (${directionText})`;
                          return (
                            <span key={p} className="capitalize bg-gray-100 rounded px-1 py-0.5 mr-1" title={title}>
                              <span className="w-1.5 h-1.5 rounded-full inline-block mr-0.5" style={{ backgroundColor: patternColor(p) }} />
                              {p}
                              <span className={`ml-1 font-bold ${arrowColor}`}>{arrow}</span>
                            </span>
                          );
                        })}
                      </div>
                    );
                  })()}
                  {(() => {
                    const bal = classifySHAPBalance(shapDecomp.pattern_contribution_pct || 0);
                    return (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded" style={{ backgroundColor: bal.color + '20', color: bal.color, border: `1px solid ${bal.color}40` }}>
                          {bal.label}
                        </span>
                        <span className="text-[9px] text-gray-500">
                          {bal.label === 'Embedding-Dominated' ? 'Patterns are nearly irrelevant for this gene.' :
                           bal.label === 'Embedding-Led' ? 'Patterns provide a minor but measurable signal.' :
                           bal.label === 'Balanced' ? 'Both embeddings and patterns contribute meaningfully.' :
                           bal.label === 'Pattern-Led' ? 'Patterns are the primary signal source.' :
                           'Embeddings play a secondary role.'}
                        </span>
                      </div>
                    );
                  })()}
                </>
              ) : (
                <span className="text-gray-400 text-xs">SHAP data not available</span>
              )}
            </div>
          </div>

          {/* Ablation Comparison */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-violet-50 border-b border-violet-200 px-3 py-1.5">
              <h4 className="text-xs font-bold text-violet-900 uppercase tracking-wide">Ablation Comparison — {gene}</h4>
            </div>
            <div className="p-4">
              <div className="flex items-end justify-center gap-8 h-36">
                {[
                  { label: 'Combined', desc: 'Emb+Pat (518-d)', val: abl.p_proposed, color: 'bg-blue-500' },
                  { label: 'Emb-only', desc: '512-d', val: abl.p_emb_only, color: 'bg-orange-400' },
                  { label: 'Pat-only', desc: '6-d', val: abl.p_pat_only, color: 'bg-violet-500' },
                ].map((item) => (
                  <div key={item.label} className="flex flex-col items-center gap-1 w-20">
                    <span className="text-xs font-mono font-bold">{((item.val || 0) * 100).toFixed(1)}%</span>
                    <div className="w-10 bg-gray-100 rounded-t relative" style={{ height: '90px' }}>
                      <div
                        className={`absolute bottom-0 left-0 right-0 rounded-t ${item.color}`}
                        style={{ height: `${Math.min((item.val || 0) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-gray-700 text-center font-semibold">{item.label}</span>
                    <span className="text-[9px] text-gray-400 text-center">{item.desc}</span>
                  </div>
                ))}
              </div>
              <div className={`mt-3 text-center text-[10px] font-medium px-2 py-1 rounded ${
                patternsHelpPrediction ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {patternsHelpPrediction
                  ? `Patterns help: +${(((abl.p_proposed || 0) - (abl.p_emb_only || 0)) * 100).toFixed(1)}pp vs emb-only`
                  : `Patterns hurt: ${(((abl.p_proposed || 0) - (abl.p_emb_only || 0)) * 100).toFixed(1)}pp vs emb-only`
                }
              </div>
              <div className="mt-2 bg-gray-50 border border-gray-200 rounded p-2 text-[9px] text-gray-500 leading-relaxed">
                Each bar shows P(mut) from a <strong>different model</strong> trained on different input features.
                The P(mut) = {scorePct}% in the header corresponds to the gene-optimal method ({geneResult?.prediction_method || 'unknown'}).
                {(() => {
                  const method = (geneResult?.prediction_method || '').toLowerCase();
                  if (method.includes('proposed') || method.includes('concat')) return ' This matches the Combined (blue) bar.';
                  if (method.includes('embedding') || method.includes('b2')) return ' This matches the Emb-only (orange) bar.';
                  if (method.includes('choquet') || method.includes('fc')) return ' P(mut) comes from the Fuzzy Choquet model (a separate dual-pathway architecture), not shown directly in this ablation chart.';
                  return '';
                })()}
                {' '}Delta = Combined − Emb-only measures whether adding pattern features helps (+) or hurts (−).
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Auto-Generated Explanation ── */}
      <div className="border rounded-lg shadow-sm overflow-hidden">
        <div className="bg-slate-100 border-b border-slate-200 px-4 py-2">
          <h4 className="font-bold text-slate-800 text-sm">AI-Generated Explanation</h4>
        </div>
        <div className="p-4">
          <AutoExplanation
            gene={gene}
            geneResult={geneResult}
            language={language}
            patternResults={patterns}
            shapDecomp={shapDecomp}
            kgInfo={kgInfo}
            morphProfile={mp}
          />
        </div>
      </div>

      {/* ── Fuzzy Choquet (only if patterns contribute positively) ── */}
      {patternsHelpPrediction && choquetData?.shapley_values && (
        <ChoquetSection
          gene={gene}
          geneResult={geneResult}
          choquetData={choquetData}
          caseId={caseId}
          language={language}
          kgInfo={kgInfo}
        />
      )}

      {/* ── Morphologic Profile ── */}
      {mp && (
        <div className="border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-gray-50 border-b border-gray-200 px-4 py-2">
            <h4 className="font-semibold text-gray-700 text-sm">Morphologic Profile</h4>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-4 gap-2 text-sm">
              <div className="bg-gray-50 rounded p-2 text-center">
                <div className="text-xs text-gray-500">Total Tiles</div>
                <div className="font-bold text-lg">{mp.n_tiles_total}</div>
              </div>
              {ANORAK_PATTERN_ORDER.map((pattern) => {
                const color = PATTERN_COLORS[pattern];
                const val = (mp as any)[`pct_${pattern}`] ?? 0;
                return (
                  <div key={pattern} className="rounded p-2 text-center" style={{ backgroundColor: color + '15' }}>
                    <div className="flex items-center justify-center gap-1">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                      <span className="text-xs text-gray-600 capitalize">{pattern}</span>
                    </div>
                    <div className="font-bold">{val.toFixed(1)}%</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Thesis Disclaimer ── */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
        <strong>DISCLAIMER:</strong> LCHAI v2.0 is a research tool developed as part of a doctoral thesis
        (THESIS_INTERNAL evidence source). Mutation predictions use ABMIL + Fuzzy Choquet MIL on
        histological slide images. {!isConcl && `${gene} has AUROC ${geneAuroc.toFixed(3)} < ${aurocThreshold.toFixed(3)} — this prediction is inconclusive and molecular testing is required. `}
        This system is intended for decision support only and must NOT be used for clinical diagnosis.
        All predictions require molecular confirmation.
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════ */

interface Props {
  caseId: string;
  imageId?: string | null;
  resultBundleId?: string | null;
  onImageSelected: (id: string) => void;
  onResultsReady: (rbId: string) => void;
  onCaseChanged: (caseId: string) => void;
}

export default function AnalysisPanel({
  caseId,
  imageId: initialImageId,
  resultBundleId,
  onImageSelected,
  onResultsReady,
  onCaseChanged,
}: Props) {
  const { preferredLanguage } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [selImage, setSelImage] = useState<string | null>(initialImageId || null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [processedImageId, setProcessedImageId] = useState<string | null>(null);
  const [autoSelected, setAutoSelected] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [selGene, setSelGene] = useState('');

  /* ── Queries ── */

  const images = useQuery({
    queryKey: ['images', caseId],
    queryFn: () => getImages(caseId).then((r) => r.data),
  });

  const results = useQuery({
    queryKey: ['results', selImage],
    queryFn: async () => {
      try {
        return (await getLatestResults(selImage!)).data;
      } catch (err: any) {
        if (err?.response?.status === 404) return null;
        throw err;
      }
    },
    enabled: !!selImage,
    retry: false,
  });

  const bundle = useQuery({
    queryKey: ['bundle', resultBundleId],
    queryFn: () => getResultBundle(resultBundleId!).then((r) => r.data),
    enabled: !!resultBundleId,
  });

  const artifactsQ = useQuery({
    queryKey: ['artifacts', resultBundleId],
    queryFn: () => getArtifacts(resultBundleId!).then((r) => r.data),
    enabled: !!resultBundleId,
  });

  const params = useQuery({
    queryKey: ['system-params'],
    queryFn: () => api.get('/parameters').then((r) => r.data),
    staleTime: 0,
    refetchOnMount: 'always' as const,
  });

  const kgAssoc = useQuery({
    queryKey: ['kg-gene-associations'],
    queryFn: () => getGeneAssociations().then((r) => r.data),
    staleTime: 60_000,
  });

  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId!).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: (data) =>
      data?.status === 'COMPLETED' || data?.status === 'FAILED' ? false : 2000,
  });

  /* ── Derived ── */

  const rb = results.data;
  const bd = bundle.data || rb;
  const allArts = artifactsQ.data || [];
  const genetics = bd?.genetic_results || [];
  const aurocValues: Record<string, number> = params.data?.auroc_values || {};
  const aurocThreshold: number = params.data?.auroc_threshold ?? 0.70;

  const sortedGenes = [...genetics].sort(
    (a: any, b: any) => (b.score ?? 0) - (a.score ?? 0),
  );

  /* ── Auto-select image + gene ── */

  useEffect(() => {
    setAutoSelected(false);
    setSelImage(null);
  }, [caseId]);

  useEffect(() => {
    if (!autoSelected && images.data?.length && !selImage) {
      const first = images.data[0];
      setSelImage(first.image_id);
      onImageSelected(first.image_id);
      setAutoSelected(true);
    }
  }, [images.data, autoSelected, selImage, onImageSelected]);

  useEffect(() => {
    if (sortedGenes.length > 0 && !selGene) {
      setSelGene(sortedGenes[0].mutation);
    }
  }, [sortedGenes.length]);

  useEffect(() => {
    if (results.data?.result_bundle_id) {
      onResultsReady(results.data.result_bundle_id);
    }
  }, [results.data?.result_bundle_id, onResultsReady]);

  /* ── Mutations (upload / process / job) ── */

  const [uploadError, setUploadError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const filename = file.name.replace(/\.[^.]+$/, '');
      const uniqueId = `${filename}_${Date.now()}`;
      let patientId: string;
      try {
        patientId = (await createPatient({ external_id: uniqueId })).data.patient_id;
      } catch {
        patientId = (await createPatient({ external_id: `${uniqueId}_${Math.random().toString(36).slice(2, 6)}` })).data.patient_id;
      }
      const newCaseId = (await createCase({ patient_id: patientId })).data.case_id;
      setUploadProgress(0);
      try {
        const imgRes = await uploadImage(newCaseId, file, (pct) => setUploadProgress(pct));
        setUploadProgress(null);
        return { ...imgRes, newCaseId };
      } catch (err) {
        // Transactional rollback: best-effort delete patient (cascades to case + any partial rows)
        try { await deletePatient(patientId); }
        catch (rollbackErr) {
          console.warn('Rollback failed; orphan patient/case may remain:', rollbackErr);
          try { await deleteCase(newCaseId); } catch { /* swallow */ }
        }
        throw err;
      }
    },
    onSuccess: (r: any) => {
      setUploadProgress(null);
      setUploadError(null);
      onCaseChanged(r.newCaseId);
      setTimeout(() => {
        setSelImage(r.data.image_id);
        onImageSelected(r.data.image_id);
        setAutoSelected(true);
      }, 200);
    },
    onError: (err: any) => {
      setUploadProgress(null);
      const detail = err?.response?.data?.detail
        || err?.response?.statusText
        || err?.message
        || 'unknown error';
      setUploadError(String(detail));
    },
  });

  const process = useMutation({
    mutationFn: () => processImage(selImage!, caseId),
    onSuccess: (r) => {
      setProcessedImageId(selImage);
      setJobId(r.data.job_id);
    },
  });

  useEffect(() => {
    if (job.data?.status === 'COMPLETED' && job.data?.result_bundle_id) {
      if (processedImageId && processedImageId !== selImage) {
        setSelImage(processedImageId);
        onImageSelected(processedImageId);
      }
      onResultsReady(job.data.result_bundle_id);
      results.refetch();
      setJobId(null);
    }
  }, [job.data?.status]);

  /* ── Current gene data ── */

  const geneResult = genetics.find((g: any) => g.mutation === selGene);
  const kgInfo = buildKgGeneInfo(selGene, kgAssoc.data);

  return (
    <div>
      {/* ══ Upload Bar ══ */}
      <div className="flex gap-3 mb-4 items-center">
        <input
          ref={fileRef}
          type="file"
          accept=".png,.jpg,.jpeg,.tif,.tiff,.svs,.bif"
          className="hidden"
          onChange={(e) => { if (e.target.files?.[0]) upload.mutate(e.target.files[0]); }}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
          onClick={() => fileRef.current?.click()}
          disabled={upload.isPending}
        >
          {upload.isPending ? 'Uploading...' : 'Upload Image'}
        </button>
        {uploadProgress !== null && (
          <div className="flex items-center gap-2 flex-1 max-w-xs">
            <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
              <div className="bg-blue-500 h-full rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
            </div>
            <span className="text-xs font-mono text-blue-700">{uploadProgress}%</span>
          </div>
        )}
        {uploadProgress === null && (
          <span className="text-gray-500 text-xs">Supported: PNG, JPEG, TIFF, SVS, BIF</span>
        )}
        {selImage && (
          <button
            className="bg-purple-600 text-white px-4 py-2 rounded text-sm"
            onClick={() => process.mutate()}
          >
            Analyze Slide
          </button>
        )}
      </div>

      {uploadError && (
        <div className="mb-4 bg-red-50 border border-red-300 rounded-lg p-3 flex items-start gap-3">
          <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1 text-sm">
            <p className="font-bold text-red-800">Upload failed</p>
            <p className="text-red-700 break-words">{uploadError}</p>
            <p className="text-red-600 text-xs mt-1">
              The patient and case created for this upload have been rolled back.
            </p>
          </div>
          <button
            className="text-red-400 hover:text-red-700 text-xl leading-none"
            onClick={() => setUploadError(null)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      {/* Image list */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {images.data?.map((img: any) => (
          <button
            key={img.image_id}
            className={`border rounded px-3 py-1 text-xs ${selImage === img.image_id ? 'bg-blue-100 border-blue-400' : ''}`}
            onClick={() => { setSelImage(img.image_id); onImageSelected(img.image_id); }}
          >
            {img.image_id.slice(0, 8)} ({img.format})
          </button>
        ))}
      </div>

      {/* ══ Processing Modal ══ */}
      {jobId && job.data && job.data.status !== 'COMPLETED' && job.data.status !== 'FAILED' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-96">
            <h3 className="font-bold text-lg mb-1">Processing Image</h3>
            {(() => {
              const stage = job.data.stage || '';
              const status = job.data.status || '';
              const imgData = images.data?.find((img: any) => img.image_id === (processedImageId || selImage));
              const slideName = imgData?.image_id?.slice(0, 12) || 'Unknown';
              const slideFormat = imgData?.format?.toUpperCase() || '';
              const tileMatch = stage.match(/(\d[\d,]*)\s*tiles/);
              const tiles = tileMatch ? parseInt(tileMatch[1].replace(/,/g, '')) : 0;
              const estMin = tiles > 0 ? Math.ceil((tiles * 0.05) / 60) : 0;
              return (
                <>
                  <p className="text-xs text-gray-600 mb-1">
                    Slide: <strong>{slideName}...</strong> {slideFormat && `(${slideFormat})`}
                  </p>
                  <p className="text-xs text-gray-500 mb-4">
                    {status === 'PENDING' ? (
                      <span className="text-amber-600 font-medium">Waiting in queue...</span>
                    ) : (
                      <>v2.0 Pipeline: CTransPath + ABMIL + Choquet
                        {tiles > 0 && <span className="ml-1 font-medium text-blue-600">— {tiles.toLocaleString()} tiles (~{estMin} min)</span>}
                      </>
                    )}
                  </p>
                </>
              );
            })()}
            <div className="bg-gray-200 rounded-full h-4 overflow-hidden mb-2">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-500"
                style={{ width: `${Math.max((job.data.progress || 0) * 100, 2)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs mb-3">
              <span className="text-gray-600">{job.data.stage || job.data.status}</span>
              <span className="font-mono font-bold text-blue-700">{((job.data.progress || 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="bg-gray-50 rounded p-3 text-xs text-gray-500 space-y-1">
              {[
                { thresh: 0.10, label: 'Decoding image' },
                { thresh: 0.50, label: 'CTransPath tile inference' },
                { thresh: 0.65, label: 'Mutation prediction (ABMIL/Choquet)' },
                { thresh: 0.75, label: 'Ablation + permutation analysis' },
                { thresh: 0.85, label: 'SHAP decomposition' },
                { thresh: 0.95, label: 'Saving results' },
              ].map((s) => {
                const prog = job.data.progress || 0;
                const done = prog >= s.thresh;
                const active = prog >= s.thresh - 0.15 && !done;
                return (
                  <div key={s.label} className={`flex items-center gap-2 ${done || active ? 'text-blue-600' : ''}`}>
                    <span>{done ? '✓' : active ? '⏳' : '○'}</span> {s.label}
                  </div>
                );
              })}
            </div>
            <button
              className="mt-4 w-full py-2 bg-red-100 text-red-700 rounded text-sm font-medium hover:bg-red-200"
              onClick={async () => {
                const currentJobId = jobId;
                setJobId(null);
                try {
                  const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                  await fetch(`${API}/api/v1/jobs/${currentJobId}:cancel`, { method: 'POST' });
                } catch { /* best effort */ }
                onCaseChanged(caseId);
                images.refetch();
              }}
            >
              Cancel and discard
            </button>
          </div>
        </div>
      )}

      {/* ══ No Results State ══ */}
      {!bd?.genetic_results && (
        <div className="text-center py-16 text-gray-400">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <p className="text-lg font-medium">No analysis results yet</p>
          <p className="text-sm mt-1">Upload and analyze a slide to see explainability results.</p>
        </div>
      )}

      {/* ══ Gene Sub-tabs + Analysis ══ */}
      {sortedGenes.length > 0 && (
        <>
          <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
            Mutation Prediction
          </h3>
          <div className="border-b border-gray-200 mb-4">
            <div className="flex gap-0 overflow-x-auto">
              {sortedGenes.map((g: any, idx: number) => {
                const gene = g.mutation;
                const gAuroc = aurocValues[gene] ?? 0;
                const isConclusive = gAuroc >= aurocThreshold;
                const isActive = selGene === gene;
                return (
                  <button
                    key={gene}
                    className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                      isActive
                        ? 'border-blue-600 text-blue-600 bg-blue-50'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                    }`}
                    onClick={() => setSelGene(gene)}
                  >
                    <span className="font-bold">{gene}</span>
                    <span className="ml-1.5 text-xs font-mono">
                      {((g.score || 0) * 100).toFixed(1)}%
                    </span>
                    <span className={`ml-1.5 text-[10px] ${isConclusive ? 'text-sky-600' : 'text-yellow-600'}`}>
                      {isConclusive ? '●' : '○'}
                    </span>
                    {idx === 0 && (
                      <span className="ml-1.5 text-[9px] bg-blue-100 text-blue-700 px-1 py-0.5 rounded">
                        TOP
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {geneResult && (
            <GeneAnalysisView
              gene={selGene}
              geneResult={geneResult}
              bundle={bd}
              artifacts={allArts}
              aurocValues={aurocValues}
              aurocThreshold={aurocThreshold}
              language={preferredLanguage}
              kgInfo={kgInfo}
            />
          )}
        </>
      )}
    </div>
  );
}
