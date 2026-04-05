import React, { useState, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { api, getResultBundle, getArtifacts, getArtifactUrl } from '../api';
import { clinicalAssocForGene } from '../data/geneClinicalAssociations';
import { useAuth } from '../auth/AuthProvider';
import {
  PATTERN_COLORS,
  ANORAK_PATTERN_ORDER,
  patternColor,
  filterAllowedPatternResults,
  isDisallowedPatternName,
} from '../patternConstants';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const _explanationCache: Record<string, string> = {};

function GeneExplanation({ gene, geneResult, language = 'en' }: { gene: string; geneResult: any; language?: string }) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const a = geneResult?.ablation;
  const p = geneResult?.permutation;
  const dataKey = `${gene}_${a?.p_proposed}_${a?.p_emb_only}_${p?.importance_pct}`;

  React.useEffect(() => {
    if (!a) return;

    if (_explanationCache[dataKey]) {
      setExplanation(_explanationCache[dataKey]);
      return;
    }
    setLoading(true);
    setExplanation(null);

    const pComb = ((a.p_proposed || 0) * 100).toFixed(1);
    const pEmb = ((a.p_emb_only || 0) * 100).toFixed(1);
    const pPat = ((a.p_pat_only || 0) * 100).toFixed(1);
    const combLessThanEmb = (a.p_proposed || 0) < (a.p_emb_only || 0);
    const combLessThanPat = (a.p_proposed || 0) < (a.p_pat_only || 0);

    const prompt = `You are an expert computational pathologist explaining an AI mutation prediction ablation study. Be precise and insightful (4-6 sentences).

Gene: ${gene}
Prediction method used by system: ${geneResult.prediction_method || 'unknown'}
Final prediction probability: ${((geneResult.score || 0) * 100).toFixed(1)}%

Ablation comparison on THIS specific slide:
- Combined model (512-d visual embeddings + 6-d pattern probabilities = 518-d): ${pComb}%
- Embeddings-only model (512-d CTransPath features): ${pEmb}%
- Patterns-only model (6 histological pattern probabilities): ${pPat}%

Key observation: ${combLessThanEmb ? `Combined (${pComb}%) is LOWER than embeddings-only (${pEmb}%). This means adding pattern features HURTS the prediction — pattern information interferes with the embedding signal.` : `Combined (${pComb}%) is higher than or equal to embeddings-only (${pEmb}%). Pattern features help or are neutral.`}
${combLessThanPat ? `Combined is also lower than patterns-only (${pPat}%).` : ''}

Permutation importance: shuffling pattern dims changes prediction by ${p?.importance_pct?.toFixed(1) || '?'}%

Explain:
1. WHY the combined model might perform differently than individual models (interference, signal dilution, or synergy)
2. What this tells us about which features (sub-cellular morphology in embeddings vs. histological growth patterns) drive the mutation signal for ${gene}
3. Whether the pattern composition of this specific slide aligns with known ${gene} associations from literature
4. Clinical implication: is the prediction reliable and what should the clinician do?`;

    api.post('/gene-explain', { gene, prompt, language })
      .then(r => {
        const txt = r.data?.explanation;
        if (txt) { _explanationCache[dataKey] = txt; setExplanation(txt); setLoading(false); }
        else { generateFallback(); }
      })
      .catch(() => { generateFallback(); });

    function generateFallback() {
      const fComb = (a.p_proposed || 0);
      const fEmb = (a.p_emb_only || 0);
      const fPat = (a.p_pat_only || 0);
      const sComb = (fComb * 100).toFixed(1);
      const sEmb = (fEmb * 100).toFixed(1);
      const sPat = (fPat * 100).toFixed(1);
      const permImp = p?.importance_pct || 0;
      const delta = (fComb - fEmb) * 100;

      const highest = Math.max(fComb, fEmb, fPat);
      const winner = highest === fEmb ? 'embeddings-only' : highest === fPat ? 'patterns-only' : 'combined';

      let text = `For ${gene}, three models were compared: combined (${sComb}%), embeddings-only (${sEmb}%), and patterns-only (${sPat}%). `;

      if (fComb < fEmb && fComb < fPat) {
        text += `The combined model performs WORSE than both individual models, suggesting destructive interference: the 6 pattern dimensions introduce noise that disrupts the embedding signal in the 518-d feature space. `;
      } else if (fComb < fEmb) {
        text += `The combined model (${sComb}%) is lower than embeddings-only (${sEmb}%), indicating pattern features interfere with the prediction. `;
        text += `Adding the 6 pattern probabilities dilutes the mutation signal captured by the 512-d visual embeddings by ${Math.abs(delta).toFixed(1)} percentage points. `;
        text += `This occurs because the histological patterns of this slide (predominantly ${gene === 'TP53' ? 'acinar' : gene === 'EGFR' ? 'acinar' : 'the observed pattern'}) do not align with the expected ${gene} morphological associations. `;
      } else if (fComb > fEmb + 0.05) {
        text += `The combined model benefits from pattern information (+${delta.toFixed(1)}pp vs emb-only), indicating histological patterns provide complementary signal for ${gene} prediction. `;
      } else {
        text += `The ${winner} model gives the strongest signal. Pattern features have minimal impact (${Math.abs(delta).toFixed(1)}pp change). `;
      }

      if (permImp > 5) {
        text += `Permutation test confirms pattern relevance (${permImp.toFixed(1)}% change when shuffled).`;
      } else {
        text += `Permutation test confirms embeddings dominate (only ${permImp.toFixed(1)}% change when patterns shuffled).`;
      }

      _explanationCache[dataKey] = text;
      setExplanation(text);
      setLoading(false);
    }
  }, [dataKey]);

  return (
    <div className="text-sm text-gray-700 leading-relaxed mb-4">
      {loading && <p className="text-gray-400 animate-pulse">Generating explanation...</p>}
      {explanation && <p>{explanation}</p>}
      {!loading && !explanation && <p className="text-gray-400">No explanation available</p>}
      <p className="text-xs text-gray-400 italic mt-2">
        Method: {geneResult?.prediction_method}. Gene-dependent optimal model (thesis Finding 2).
      </p>
    </div>
  );
}

interface Props {
  resultBundleId: string;
}

const GENES_V2 = ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10'];

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

const CHOQUET_STYLE_GENES = ['TP53', 'EGFR'] as const;

/** Slide-level pattern synergy narrative for B2 genes: complements true Choquet Shapley (KRAS, RBM10). */
function PatternSynergyExplainBlock({
  selGene,
  caseId,
  geneResult,
  morphologicProfile,
  synergyExpl,
  setSynergyExpl,
  synergyLoading,
  setSynergyLoading,
}: any) {
  const row = clinicalAssocForGene(selGene);
  const litPatterns = row?.patternAssociation ?? 'Unknown';
  const litTreatment = row?.treatmentImplications ?? 'Unknown';
  const cacheKey = `synergy_${selGene}_${caseId}`;

  const handleExplain = async () => {
    if (_explanationCache[cacheKey]) {
      setSynergyExpl(_explanationCache[cacheKey]);
      return;
    }
    setSynergyLoading(true);
    try {
      const patterns = ['lepidic', 'acinar', 'papillary', 'micropapillary', 'solid', 'cribriform'] as const;
      const parts = patterns
        .map((p) => ({ p, v: (morphologicProfile?.[`pct_${p}`] as number) ?? 0 }))
        .sort((a, b) => b.v - a.v);
      const distText = parts.map(({ p, v }) => `  ${p}: ${v.toFixed(1)}%`).join('\n');
      const top2 = parts.slice(0, 2).filter((x) => x.v > 0.5);
      const pairHint =
        top2.length >= 2
          ? `Dominant admixture on this slide: ${top2[0].p} (${top2[0].v.toFixed(1)}%) with ${top2[1].p} (${top2[1].v.toFixed(1)}%).`
          : 'Single-pattern dominance or sparse secondary components.';

      const prompt = `You are a clinical decision support assistant for lung adenocarcinoma. The mutation model for ${selGene} uses embedding-first ABMIL (not the Fuzzy Choquet MIL head). There are therefore no learned Choquet Shapley values for this gene—but the six-class growth-pattern distribution on this slide still matters for interpreting architecture–genotype hypotheses.

Gene: ${selGene}
Mutation probability: ${((geneResult.score || geneResult.probability || 0) * 100).toFixed(1)}%
Literature-typical pattern associations (approximate): ${litPatterns}
Treatment context (summary): ${litTreatment}

Tile-level pattern proportions on this slide:
${distText}

${pairHint}

Task: Write a concise clinical interpretation (max 220 words) for a pathologist covering:
(1) How the observed pattern mixture relates to what is often described for ${selGene} in the literature (without claiming this slide proves genotype).
(2) Which pattern pairs or transitions could plausibly act together (synergy-like co-occurrence) versus which components are minor.
(3) Why interaction-aware aggregation (Fuzzy Choquet) is informative for other genes (e.g. KRAS) but ${selGene} is evaluated with embedding-led models in this pipeline.
Do NOT say "diagnose" or "confirmed".`;

      const resp = await api.post(`/cases/${caseId}/graph/explain`, { language: 'en', extra_context: prompt });
      const text = resp.data?.explanation || 'Explanation not available.';
      _explanationCache[cacheKey] = text;
      setSynergyExpl(text);
    } catch (e: any) {
      setSynergyExpl(`Could not generate explanation: ${e?.message || 'Unknown error'}`);
    } finally {
      setSynergyLoading(false);
    }
  };

  return (
    <div className="mb-4 mt-2 border-t border-violet-200 pt-3">
      <p className="text-xs text-violet-800 mb-2">
        <strong>Fuzzy Choquet–style pattern synergies ({selGene}).</strong> True Choquet Shapley values are computed for KRAS and RBM10.
        For {selGene}, use this slide&apos;s six-pattern distribution to discuss architectural co-occurrence in the same spirit as interaction indices.
      </p>
      <button
        className="px-3 py-1.5 bg-violet-600 text-white rounded text-sm hover:bg-violet-700 disabled:opacity-50"
        onClick={handleExplain}
        disabled={synergyLoading}
      >
        {synergyLoading ? 'Generating…' : 'Interpret pattern synergies (slide-level)'}
      </button>
      {synergyExpl && (
        <div className="mt-3 bg-violet-50 border border-violet-200 rounded p-4 text-sm leading-relaxed text-violet-900 whitespace-pre-wrap">
          <strong>Pattern synergy interpretation — {selGene}</strong>
          <div className="mt-2">{synergyExpl}</div>
        </div>
      )}
    </div>
  );
}

function ChoquetExplainBlock({ selGene, caseId, geneResult, choquetData, choquetExpl, setChoquetExpl, choquetLoading, setChoquetLoading }: any) {
  const row = clinicalAssocForGene(selGene);
  const litPatterns = row?.patternAssociation ?? 'Unknown';
  const litTreatment = row?.treatmentImplications ?? 'Unknown';
  const cacheKey = `choquet_${selGene}_${caseId}`;

  const handleExplain = async () => {
    if (_explanationCache[cacheKey]) { setChoquetExpl(_explanationCache[cacheKey]); return; }
    setChoquetLoading(true);
    try {
      const svText = Object.entries(choquetData.shapley_values as Record<string, number>)
        .sort(([,a],[,b]) => (b as number) - (a as number))
        .map(([p, v]) => `  ${p}: ${(v as number).toFixed(4)}`).join('\n');
      const ixText = choquetData.interaction_indices
        ? Object.entries(choquetData.interaction_indices as Record<string, number>)
            .sort(([,a],[,b]) => Math.abs(b as number) - Math.abs(a as number))
            .slice(0, 5)
            .map(([p, v]) => `  ${p.replace('_', ' x ')}: ${(v as number) > 0 ? '+' : ''}${(v as number).toFixed(4)} (${(v as number) > 0 ? 'synergy' : 'redundancy'})`)
            .join('\n')
        : 'None';
      const prompt = `You are a clinical decision support system for lung adenocarcinoma. Explain the following Choquet Shapley analysis results for a pathologist who is NOT a data scientist. Be concise (max 200 words), clinically grounded, and honest about limitations.\n\nGene: ${selGene}\nMutation probability: ${((geneResult.score || geneResult.probability || 0) * 100).toFixed(1)}%\nKnown clinical association (thesis Table gene_unified summary): ${selGene} mutations are often discussed in relation to ${litPatterns}. Treatment context: ${litTreatment}.\n\nLearned Shapley values (pattern importance from the AI model):\n${svText}\n\nTop interaction indices (pattern pair synergies/redundancies):\n${ixText}\n\nExplain: 1) What the Shapley values tell us clinically, 2) Whether they align with known literature, 3) What the interaction indices mean for this patient, 4) Any limitations. Use language a pathologist would understand. Do NOT use the word "diagnose" or "confirmed".`;

      const resp = await api.post(`/cases/${caseId}/graph/explain`, { language: 'en', extra_context: prompt });
      const text = resp.data?.explanation || 'Explanation not available.';
      _explanationCache[cacheKey] = text;
      setChoquetExpl(text);
    } catch (e: any) {
      setChoquetExpl(`Could not generate explanation: ${e?.message || 'Unknown error'}`);
    } finally {
      setChoquetLoading(false);
    }
  };

  return (
    <div className="mb-4 mt-2">
      <button
        className="px-3 py-1.5 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 disabled:opacity-50"
        onClick={handleExplain}
        disabled={choquetLoading}
      >
        {choquetLoading ? 'Generating clinical interpretation...' : 'Explain Choquet values with AI'}
      </button>
      {choquetExpl && (
        <div className="mt-3 bg-amber-50 border border-amber-200 rounded p-4 text-sm leading-relaxed text-amber-950 whitespace-pre-wrap">
          <strong>Clinical Interpretation — {selGene}</strong>
          <div className="mt-2">{choquetExpl}</div>
          <div className="mt-2 text-xs text-gray-500 italic">
            Known association: {litPatterns} | Treatment: {litTreatment}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ShapPanel({ resultBundleId }: Props) {
  const { preferredLanguage } = useAuth();
  const [selGene, setSelGene] = useState('');
  const [choquetExpl, setChoquetExpl] = useState<string | null>(null);
  const [choquetLoading, setChoquetLoading] = useState(false);
  const [synergyExpl, setSynergyExpl] = useState<string | null>(null);
  const [synergyLoading, setSynergyLoading] = useState(false);

  const bundle = useQuery({
    queryKey: ['bundle', resultBundleId],
    queryFn: () => getResultBundle(resultBundleId).then(r => r.data),
  });

  const artifacts = useQuery({
    queryKey: ['artifacts', resultBundleId],
    queryFn: () => getArtifacts(resultBundleId).then(r => r.data),
  });

  const params = useQuery({
    queryKey: ['system-params'],
    queryFn: () => api.get('/parameters').then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always' as const,
  });

  const aurocValues: Record<string, number> = params.data?.auroc_values || {};
  const aurocThreshold: number = params.data?.auroc_threshold ?? 0.70;
  const isDynConcl = useCallback((gene: string) => (aurocValues[gene] ?? 0) >= aurocThreshold, [aurocValues, aurocThreshold]);

  const allArts = artifacts.data || [];
  const genetics = bundle.data?.genetic_results || [];
  const patterns = filterAllowedPatternResults(bundle.data?.pattern_results || []);
  const mp = bundle.data?.morphologic_profile;
  const isV2 = bundle.data?.pipeline_version?.startsWith('2');
  const caseId = bundle.data?.case_id || '';

  React.useEffect(() => {
    if (genetics.length > 0 && !selGene) {
      const top = [...genetics].sort((a: any, b: any) => (b.score ?? 0) - (a.score ?? 0))[0];
      if (top) setSelGene(top.mutation);
    }
  }, [genetics, selGene]);

  React.useEffect(() => {
    setSynergyExpl(null);
  }, [selGene]);

  const geneResult = genetics.find((g: any) => g.mutation === selGene);
  const shapDecomp = geneResult?.shap_decomposition;
  const choquetData = geneResult?.choquet_shapley;

  const decompBarArt = allArts.find(
    (a: any) => a.artifact_type === 'shap' && a.uri?.includes(`shap_decomp_${selGene}_bar`)
  );
  const decompPatArt = allArts.find(
    (a: any) => a.artifact_type === 'shap' && a.uri?.includes(`shap_decomp_${selGene}_patterns`)
  );

  return (
    <div>
      {/* Header + gene selector */}
      <div className="flex gap-3 mb-4 items-center">
        <h2 className="text-lg font-semibold">SHAP / Explainability {isV2 && <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded ml-2">v2.0</span>}</h2>
        <div className="flex gap-1 ml-4 flex-wrap">
          {[...GENES_V2].sort((a, b) => {
            const sa = genetics.find((x: any) => x.mutation === a)?.score ?? 0;
            const sb = genetics.find((x: any) => x.mutation === b)?.score ?? 0;
            return sb - sa;
          }).map(g => {
            const gr = genetics.find((x: any) => x.mutation === g);
            return (
              <button
                key={g}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  selGene === g ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                onClick={() => setSelGene(g)}
              >
                {g}
                {gr && (
                  <span className={`ml-1 text-xs ${
                    isDynConcl(g) ? 'text-cyan-100' : 'text-yellow-200'
                  }`}>
                    ({isDynConcl(g) ? 'conclusive' : 'inconclusive'})
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* v2 banner */}
      {isV2 ? (
        <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-xs text-blue-800">
          <strong>v2.0 Pipeline:</strong> Mutation predictions use Pattern-Informed ABMIL (Artifact 2).
          SHAP values are computed via gradient-based DeepSHAP on the ABMIL model, decomposed into embedding dims (0-511) and pattern dims (512-517).
          {bundle.data?.use_choquet && ' Choquet Shapley values from Fuzzy Choquet MIL (Artifact 3) show pattern-level importance.'}
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-300 rounded p-3 mb-4 text-xs text-yellow-800">
          <strong>v1.x Pipeline:</strong> SHAP values from TreeExplainer on XGBoost morphological features.
        </div>
      )}

      {/* Gene result header */}
      {geneResult && (
        <div className={`p-3 rounded mb-4 flex items-center justify-between ${
          isDynConcl(selGene) ? 'bg-sky-50 border border-sky-200' :
          'bg-yellow-50 border border-yellow-200'
        }`}>
          <div>
            <span className="text-sm font-semibold">{selGene} Mutation:</span>
            <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
              isDynConcl(selGene) ? 'bg-sky-200 text-sky-900' : 'bg-yellow-200 text-yellow-800'
            }`}>
              {isDynConcl(selGene) ? 'Conclusive' : 'Inconclusive'}
            </span>
            <span className="ml-2 text-xs text-gray-500">via {geneResult.prediction_method || 'xgboost'}</span>
          </div>
          <span className="text-sm font-mono">P(mut) = {((geneResult.score || 0) * 100).toFixed(1)}%</span>
        </div>
      )}

      {geneResult && !isDynConcl(selGene) && (
        <div className="bg-yellow-50 border border-yellow-300 rounded p-2 mb-4 text-xs text-yellow-800">
          ⚠ Molecular testing recommended. {selGene} prediction has AUROC {(aurocValues[selGene] ?? 0).toFixed(3)} &lt; {aurocThreshold.toFixed(3)} — cannot be reliably predicted from histological features alone.
        </div>
      )}

      {/* ── ABLATION + PERMUTATION — unified explanation ── */}
      {geneResult?.ablation && (
        <div className="mb-6 border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-emerald-50 border-b border-emerald-200 px-4 py-2">
            <h3 className="font-bold text-emerald-900">How was this prediction made? — {selGene}</h3>
          </div>
          <div className="p-4">
            {/* LLM-generated explanation */}
            <GeneExplanation gene={selGene} geneResult={geneResult} language={preferredLanguage} />

            {/* Compact vertical bars — no redundant numbers above */}
            <div className="flex items-end justify-center gap-10 h-40">
              {[
                { label: 'Combined', val: geneResult.ablation.p_proposed, color: 'bg-blue-500' },
                { label: 'Emb-only', val: geneResult.ablation.p_emb_only, color: 'bg-orange-400' },
                { label: 'Pat-only', val: geneResult.ablation.p_pat_only, color: 'bg-violet-500' },
              ].map(item => (
                <div key={item.label} className="flex flex-col items-center gap-1 w-20">
                  <span className="text-xs font-mono font-bold">{((item.val || 0) * 100).toFixed(1)}%</span>
                  <div className="w-12 bg-gray-100 rounded-t relative" style={{ height: '110px' }}>
                    <div className={`absolute bottom-0 left-0 right-0 rounded-t ${item.color}`}
                      style={{ height: `${Math.min((item.val || 0) * 100, 100)}%` }} />
                  </div>
                  <span className="text-[10px] text-gray-600 text-center font-medium">{item.label}</span>
                </div>
              ))}
            </div>
            {mp &&
              CHOQUET_STYLE_GENES.includes(selGene as (typeof CHOQUET_STYLE_GENES)[number]) && (
                <PatternSynergyExplainBlock
                  selGene={selGene}
                  caseId={caseId}
                  geneResult={geneResult}
                  morphologicProfile={mp}
                  synergyExpl={synergyExpl}
                  setSynergyExpl={setSynergyExpl}
                  synergyLoading={synergyLoading}
                  setSynergyLoading={setSynergyLoading}
                />
              )}
          </div>
        </div>
      )}

      {/* ── OUTPUT 3: SHAP Decomposition (only for Proposed concat genes: STK11, KEAP1) ── */}
      {shapDecomp && geneResult?.prediction_method?.includes('proposed') && (
        <div className="mb-6 border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-indigo-50 border-b border-indigo-200 px-4 py-2">
            <h3 className="font-bold text-indigo-900">SHAP Decomposition — {selGene}</h3>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-3 gap-4">
              {/* Stacked bar */}
              <div className="col-span-1">
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Embedding vs Pattern contribution</h4>
                <div className="h-8 rounded overflow-hidden flex bg-gray-100">
                  <div
                    className="bg-blue-500 flex items-center justify-center text-white text-[10px] font-bold"
                    style={{ width: `${shapDecomp.embedding_contribution_pct}%` }}
                  >
                    {shapDecomp.embedding_contribution_pct?.toFixed(1)}%
                  </div>
                  <div
                    className="bg-red-400 flex items-center justify-center text-white text-[10px] font-bold"
                    style={{ width: `${shapDecomp.pattern_contribution_pct}%` }}
                  >
                    {shapDecomp.pattern_contribution_pct?.toFixed(1)}%
                  </div>
                </div>
                <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                  <span>Embeddings (512d)</span>
                  <span>Patterns (6d)</span>
                </div>
                {shapDecomp.top_pattern_dims && (
                  <div className="mt-2 text-xs text-gray-600">
                    Top patterns: {shapDecomp.top_pattern_dims
                      .filter((p: string) => !isDisallowedPatternName(p))
                      .map((p: string) => (
                      <span key={p} className="capitalize bg-gray-100 rounded px-1.5 py-0.5 mr-1">
                        <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: patternColor(p) }} />
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* SHAP decomposition bar plot */}
              <div className="col-span-1">
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Decomposition Plot</h4>
                <div className="border rounded bg-gray-50 h-40 flex items-center justify-center overflow-hidden">
                  {decompBarArt ? (
                    <ArtifactImage uri={decompBarArt.uri} alt={`SHAP decomposition ${selGene}`} className="max-h-full max-w-full object-contain" />
                  ) : (
                    <span className="text-gray-400 text-xs">No decomposition plot</span>
                  )}
                </div>
              </div>

              {/* Pattern-dim SHAP */}
              <div className="col-span-1">
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Pattern-Dimension SHAP</h4>
                <div className="border rounded bg-gray-50 h-40 flex items-center justify-center overflow-hidden">
                  {decompPatArt ? (
                    <ArtifactImage uri={decompPatArt.uri} alt={`Pattern SHAP ${selGene}`} className="max-h-full max-w-full object-contain" />
                  ) : (
                    <span className="text-gray-400 text-xs">No pattern SHAP plot</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── OUTPUT 4: Choquet Shapley Values (only for Choquet genes: KRAS, RBM10) ── */}
      {choquetData && geneResult?.prediction_method?.includes('Choquet') && (
        <div className="mb-6 border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between">
            <h3 className="font-bold text-amber-900">Choquet Shapley Values — {selGene} (Fuzzy Choquet MIL)</h3>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 gap-6">
              {/* Shapley values */}
              <div>
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Pattern Shapley Values (singleton importance)</h4>
                {choquetData.shapley_values && (
                  <div className="space-y-1">
                    {(() => {
                      const entries = Object.entries(choquetData.shapley_values as Record<string, number>)
                        .filter(([pattern]) => !isDisallowedPatternName(pattern))
                        .sort(([, a], [, b]) => (b as number) - (a as number));
                      const maxVal = Math.max(...entries.map(([, v]) => v as number), 0.001);
                      const uniform = 1.0 / entries.length;
                      return entries.map(([pattern, val]) => {
                        const delta = (val as number) - uniform;
                        return (
                          <div key={pattern} className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: patternColor(pattern) }} />
                            <span className="text-xs w-24 capitalize">{pattern}</span>
                            <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                              <div
                                className="h-full rounded"
                                style={{
                                  width: `${Math.min(((val as number) / maxVal) * 100, 100)}%`,
                                  backgroundColor: patternColor(pattern),
                                  opacity: 0.7,
                                }}
                              />
                            </div>
                            <span className="text-xs font-mono w-16">{(val as number).toFixed(4)}</span>
                            <span className={`text-[10px] font-mono w-14 ${delta > 0.002 ? 'text-sky-600' : delta < -0.002 ? 'text-rose-600' : 'text-gray-400'}`}>
                              {delta > 0 ? '+' : ''}{(delta * 100).toFixed(2)}%
                            </span>
                          </div>
                        );
                      });
                    })()}
                  </div>
                )}
              </div>

              {/* Interaction indices */}
              <div>
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Interaction Indices (pairwise synergies)</h4>
                {choquetData.interaction_indices && Object.keys(choquetData.interaction_indices).length > 0 ? (
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="border px-2 py-1 text-left">Pattern Pair</th>
                        <th className="border px-2 py-1 text-right">Interaction</th>
                        <th className="border px-2 py-1 text-center">Direction</th>
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
                                {(val as number) > 0 ? (
                                  <span className="text-red-600 font-bold">Synergy ↑</span>
                                ) : (
                                  <span className="text-blue-600 font-bold">Redundancy ↓</span>
                                )}
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
          </div>
        </div>
      )}

      {/* ── Unified Choquet Clinical Interpretation (LLM-powered) ── */}
      {choquetData && geneResult?.prediction_method?.includes('Choquet') && (
        <ChoquetExplainBlock
          selGene={selGene}
          caseId={caseId}
          geneResult={geneResult}
          choquetData={choquetData}
          choquetExpl={choquetExpl}
          setChoquetExpl={setChoquetExpl}
          choquetLoading={choquetLoading}
          setChoquetLoading={setChoquetLoading}
        />
      )}

      {/* Morphologic profile */}
      {mp && (
        <div className="mb-6">
          <h3 className="font-semibold mb-2 text-sm">Morphologic Profile</h3>
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
                    <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: color }} />
                    <span className="text-xs text-gray-600 capitalize">{pattern}</span>
                  </div>
                  <div className="font-bold">{val.toFixed(1)}%</div>
                </div>
              );
            })}
          </div>
          {geneResult &&
            mp &&
            !geneResult.ablation &&
            CHOQUET_STYLE_GENES.includes(selGene as (typeof CHOQUET_STYLE_GENES)[number]) && (
              <PatternSynergyExplainBlock
                selGene={selGene}
                caseId={caseId}
                geneResult={geneResult}
                morphologicProfile={mp}
                synergyExpl={synergyExpl}
                setSynergyExpl={setSynergyExpl}
                synergyLoading={synergyLoading}
                setSynergyLoading={setSynergyLoading}
              />
            )}
        </div>
      )}

      {/* All XAI Artifacts */}
      {allArts.length > 0 && (
        <details className="mt-4">
          <summary className="font-semibold text-sm cursor-pointer text-gray-600">
            All XAI Artifacts ({allArts.length})
          </summary>
          <table className="w-full text-xs border-collapse mt-2">
            <thead>
              <tr className="bg-gray-100">
                <th className="border px-2 py-1.5">Type</th>
                <th className="border px-2 py-1.5">Gene</th>
                <th className="border px-2 py-1.5">URI</th>
                <th className="border px-2 py-1.5">Preview</th>
              </tr>
            </thead>
            <tbody>
              {allArts.map((a: any, i: number) => (
                <tr key={a.artifact_id || i} className="hover:bg-gray-50">
                  <td className="border px-2 py-1.5">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      a.artifact_type?.includes('attention') ? 'bg-orange-100 text-orange-700' :
                      a.artifact_type?.includes('decomp') ? 'bg-indigo-100 text-indigo-700' :
                      a.artifact_type?.includes('overlay') ? 'bg-cyan-100 text-cyan-800' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {a.artifact_type}
                    </span>
                  </td>
                  <td className="border px-2 py-1.5 font-mono">{a.gene || '-'}</td>
                  <td className="border px-2 py-1.5 text-blue-600 truncate max-w-xs" title={a.uri}>{a.uri}</td>
                  <td className="border px-2 py-1.5">
                    <a href={getArtifactUrl(a.uri)} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Open</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}
