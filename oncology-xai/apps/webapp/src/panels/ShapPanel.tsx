import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getResultBundle, getArtifacts, getArtifactUrl } from '../api';

interface Props {
  resultBundleId: string;
}

const GENES_V2 = ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10'];

const PATTERN_COLORS: Record<string, string> = {
  lepidic: '#E6FF32',
  acinar: '#00FF00',
  papillary: '#0000FF',
  micropapillary: '#FFD700',
  solid: '#FF0000',
  mucinous: '#FFA500',
};

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

export default function ShapPanel({ resultBundleId }: Props) {
  const [selGene, setSelGene] = useState('TP53');

  const bundle = useQuery({
    queryKey: ['bundle', resultBundleId],
    queryFn: () => getResultBundle(resultBundleId).then(r => r.data),
  });

  const artifacts = useQuery({
    queryKey: ['artifacts', resultBundleId],
    queryFn: () => getArtifacts(resultBundleId).then(r => r.data),
  });

  const allArts = artifacts.data || [];
  const genetics = bundle.data?.genetic_results || [];
  const patterns = bundle.data?.pattern_results || [];
  const mp = bundle.data?.morphologic_profile;
  const isV2 = bundle.data?.pipeline_version?.startsWith('2');

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
        <h2 className="text-lg font-semibold">SHAP / Explainability {isV2 && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded ml-2">v2.0</span>}</h2>
        <div className="flex gap-1 ml-4 flex-wrap">
          {GENES_V2.map(g => {
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
                    gr.confidence_label === 'Conclusive' ? 'text-green-200' : 'text-yellow-200'
                  }`}>
                    ({gr.confidence_label || gr.status})
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
          geneResult.confidence_label === 'Conclusive' ? 'bg-green-50 border border-green-200' :
          'bg-yellow-50 border border-yellow-200'
        }`}>
          <div>
            <span className="text-sm font-semibold">{selGene} Mutation:</span>
            <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
              geneResult.confidence_label === 'Conclusive' ? 'bg-green-200 text-green-800' : 'bg-yellow-200 text-yellow-800'
            }`}>
              {geneResult.confidence_label || geneResult.status}
            </span>
            <span className="ml-2 text-xs text-gray-500">via {geneResult.prediction_method || 'xgboost'}</span>
          </div>
          <span className="text-sm font-mono">P(mut) = {((geneResult.score || 0) * 100).toFixed(1)}%</span>
        </div>
      )}

      {geneResult?.disclaimer && (
        <div className="bg-yellow-50 border border-yellow-300 rounded p-2 mb-4 text-xs text-yellow-800">
          ⚠ {geneResult.disclaimer}
        </div>
      )}

      {/* ── ABLATION + PERMUTATION — unified explanation ── */}
      {geneResult?.ablation && (
        <div className="mb-6 border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-emerald-50 border-b border-emerald-200 px-4 py-2">
            <h3 className="font-bold text-emerald-900">How was this prediction made? — {selGene}</h3>
          </div>
          <div className="p-4">
            {/* Natural language explanation */}
            {(() => {
              const a = geneResult.ablation;
              const p = geneResult.permutation;
              const pProp = ((a.p_proposed || 0) * 100).toFixed(1);
              const pEmb = ((a.p_emb_only || 0) * 100).toFixed(1);
              const pPat = ((a.p_pat_only || 0) * 100).toFixed(1);
              const delta = ((a.delta_patterns || 0) * 100).toFixed(1);
              const deltaAbs = Math.abs((a.delta_patterns || 0) * 100);
              const permImp = p?.importance_pct || 0;
              const method = geneResult.prediction_method || '';

              const bestModel = parseFloat(pEmb) > parseFloat(pProp) ? 'embeddings-only' :
                parseFloat(pPat) > parseFloat(pProp) ? 'patterns-only' : 'proposed (combined)';

              return (
                <div className="text-sm text-gray-700 leading-relaxed mb-4 space-y-2">
                  <p>
                    Three independently trained models were run on this slide to predict <strong>{selGene}</strong> mutation.
                    The <strong className="text-blue-700">combined model</strong> (embeddings + patterns) predicts <strong>{pProp}%</strong>,
                    the <strong className="text-orange-600">embeddings-only model</strong> predicts <strong>{pEmb}%</strong>,
                    and the <strong className="text-green-600">patterns-only model</strong> predicts <strong>{pPat}%</strong>.
                  </p>
                  <p>
                    {deltaAbs > 5
                      ? `Adding pattern information ${parseFloat(delta) > 0 ? 'increases' : 'decreases'} the prediction by ${Math.abs(parseFloat(delta))}% compared to using embeddings alone, indicating that histological patterns have a meaningful impact on this gene's prediction.`
                      : `The difference between the combined and embeddings-only models is small (${delta}%), suggesting that for ${selGene} on this slide, visual features captured by CTransPath are the primary driver.`}
                  </p>
                  {p && (
                    <p>
                      {permImp > 5
                        ? `When pattern dimensions are randomly shuffled, the prediction changes by ${permImp.toFixed(1)}%, confirming that patterns contribute meaningfully to the ${selGene} prediction.`
                        : `Randomly shuffling pattern dimensions changes the prediction by only ${permImp.toFixed(1)}%, confirming that embeddings dominate for ${selGene}.`}
                    </p>
                  )}
                  <p className="text-xs text-gray-500 italic">
                    Active method for {selGene}: {method}. Selected based on thesis Finding 2 (gene-dependent optimal representation).
                  </p>
                </div>
              );
            })()}

            {/* Compact vertical bars — no redundant numbers above */}
            <div className="flex items-end justify-center gap-10 h-40">
              {[
                { label: 'Combined', val: geneResult.ablation.p_proposed, color: 'bg-blue-500' },
                { label: 'Emb-only', val: geneResult.ablation.p_emb_only, color: 'bg-orange-400' },
                { label: 'Pat-only', val: geneResult.ablation.p_pat_only, color: 'bg-green-500' },
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
                    Top patterns: {shapDecomp.top_pattern_dims.map((p: string) => (
                      <span key={p} className="capitalize bg-gray-100 rounded px-1.5 py-0.5 mr-1">
                        <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: PATTERN_COLORS[p] }} />
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
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2">
            <h3 className="font-bold text-amber-900">Choquet Shapley Values — {selGene} (Fuzzy Choquet MIL)</h3>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 gap-6">
              {/* Shapley values */}
              <div>
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Pattern Shapley Values (singleton importance)</h4>
                {choquetData.shapley_values && (
                  <div className="space-y-1">
                    {Object.entries(choquetData.shapley_values as Record<string, number>)
                      .sort(([, a], [, b]) => (b as number) - (a as number))
                      .map(([pattern, val]) => (
                        <div key={pattern} className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: PATTERN_COLORS[pattern] || '#ccc' }} />
                          <span className="text-xs w-24 capitalize">{pattern}</span>
                          <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                            <div
                              className="h-full rounded"
                              style={{
                                width: `${Math.min((val as number) * 100, 100)}%`,
                                backgroundColor: PATTERN_COLORS[pattern] || '#888',
                                opacity: 0.7,
                              }}
                            />
                          </div>
                          <span className="text-xs font-mono w-12">{(val as number).toFixed(3)}</span>
                        </div>
                      ))}
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
                        .sort(([, a], [, b]) => Math.abs(b as number) - Math.abs(a as number))
                        .map(([pair, val]) => {
                          const [p1, p2] = pair.split('_');
                          return (
                            <tr key={pair} className="hover:bg-gray-50">
                              <td className="border px-2 py-1 capitalize">
                                <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: PATTERN_COLORS[p1] || '#ccc' }} />
                                {p1}
                                <span className="text-gray-400 mx-1">×</span>
                                <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: PATTERN_COLORS[p2] || '#ccc' }} />
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

      {/* Morphologic profile */}
      {mp && (
        <div className="mb-6">
          <h3 className="font-semibold mb-2 text-sm">Morphologic Profile</h3>
          <div className="grid grid-cols-4 gap-2 text-sm">
            <div className="bg-gray-50 rounded p-2 text-center">
              <div className="text-xs text-gray-500">Total Tiles</div>
              <div className="font-bold text-lg">{mp.n_tiles_total}</div>
            </div>
            {Object.entries(PATTERN_COLORS).map(([pattern, color]) => {
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
                      a.artifact_type?.includes('overlay') ? 'bg-green-100 text-green-700' :
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
