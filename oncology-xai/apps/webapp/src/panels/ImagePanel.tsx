import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getImages, uploadImage, processImage, getJob, getLatestResults, getArtifactUrl } from '../api';

const PATTERN_COLORS: Record<string, string> = {
  lepidic: '#FFFF00',
  acinar: '#00FF00',
  papillary: '#0000FF',
  micropapillary: '#FF00FF',
  solid: '#FF0000',
  mucinous: '#FFA500',
};

const GENES_V2 = ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10'];

interface Props {
  caseId: string;
  imageId?: string | null;
  onImageSelected: (id: string) => void;
  onResultsReady: (rbId: string) => void;
}

export default function ImagePanel({ caseId, imageId: initialImageId, onImageSelected, onResultsReady }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [selImage, setSelImage] = useState<string | null>(initialImageId || null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [processedImageId, setProcessedImageId] = useState<string | null>(null);
  const [autoSelected, setAutoSelected] = useState(false);
  const [showAttnOverlay, setShowAttnOverlay] = useState(false);

  const images = useQuery({
    queryKey: ['images', caseId],
    queryFn: () => getImages(caseId).then(r => r.data),
  });

  useEffect(() => {
    if (!autoSelected && images.data && images.data.length > 0 && !selImage) {
      const firstImg = images.data[0];
      setSelImage(firstImg.image_id);
      onImageSelected(firstImg.image_id);
      setAutoSelected(true);
    }
  }, [images.data, autoSelected, selImage, onImageSelected]);

  const selImageData = images.data?.find((img: any) => img.image_id === selImage);
  const viewerUrl = selImageData?.storage_uri ? getArtifactUrl(selImageData.storage_uri) : null;

  const results = useQuery({
    queryKey: ['results', selImage],
    queryFn: async () => {
      try {
        const r = await getLatestResults(selImage!);
        return r.data;
      } catch (err: any) {
        if (err?.response?.status === 404) return null;
        throw err;
      }
    },
    enabled: !!selImage,
    retry: false,
  });

  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId!).then(r => r.data),
    enabled: !!jobId,
    refetchInterval: (data) => data?.status === 'COMPLETED' || data?.status === 'FAILED' ? false : 2000,
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadImage(caseId, file),
    onSuccess: (r) => {
      setSelImage(r.data.image_id);
      onImageSelected(r.data.image_id);
      images.refetch();
    },
  });

  const process = useMutation({
    mutationFn: () => processImage(selImage!, caseId),
    onSuccess: (r) => {
      setProcessedImageId(selImage);
      setJobId(r.data.job_id);
    },
  });

  React.useEffect(() => {
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

  React.useEffect(() => {
    if (results.data?.result_bundle_id) {
      onResultsReady(results.data.result_bundle_id);
    }
  }, [results.data?.result_bundle_id, onResultsReady]);

  const rb = results.data;
  const isV2 = rb?.pipeline_version?.startsWith('2');

  const roiArt = rb?.xai_artifacts?.find((a: any) => a.type === 'roi_overlay');
  const attnArt = rb?.xai_artifacts?.find((a: any) => a.type === 'attention_overlay');

  return (
    <div>
      {/* Upload bar */}
      <div className="flex gap-3 mb-4">
        <input ref={fileRef} type="file" accept=".png,.jpg,.jpeg,.tif,.tiff,.svs,.bif" className="hidden" onChange={e => {
          if (e.target.files?.[0]) upload.mutate(e.target.files[0]);
        }} />
        <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm" onClick={() => fileRef.current?.click()}>
          Upload Image
        </button>
        <span className="text-gray-500 text-xs self-center">Supported: PNG, JPEG, TIFF, SVS</span>
        {selImage && (
          <button className="bg-purple-600 text-white px-4 py-2 rounded text-sm" onClick={() => process.mutate()}>
            Process (v2 ABMIL + Choquet)
          </button>
        )}
        {jobId && job.data && (
          <span className="self-center text-sm text-gray-600">
            Job: {job.data.status} {job.data.status === 'RUNNING' && '...'}
          </span>
        )}
        {isV2 && (
          <span className="self-center text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded font-medium">
            v2.0 Pipeline
          </span>
        )}
      </div>

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

      {/* ══════════════════════════════════════════════════════════════
           CARD 1: Mutation Report (confidence-labelled)
         ══════════════════════════════════════════════════════════════ */}
      {rb?.genetic_results && (
        <div className="mb-6 border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-red-50 border-b border-red-200 px-4 py-2">
            <h3 className="font-bold text-red-900">Card 1 — Mutation Report (Confidence-Labelled)</h3>
          </div>
          <div className="p-4">
            <table className="w-full border-collapse text-sm mb-4">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border px-3 py-2 text-left">Gene</th>
                  <th className="border px-3 py-2 text-right">Probability</th>
                  <th className="border px-3 py-2 text-center">Label</th>
                  <th className="border px-3 py-2 text-center">Method</th>
                  <th className="border px-3 py-2 text-left">SHAP Split (Emb/Pat)</th>
                  {rb.use_choquet && <th className="border px-3 py-2 text-left">Choquet Shapley</th>}
                  <th className="border px-3 py-2 text-left">Disclaimer</th>
                </tr>
              </thead>
              <tbody>
                {rb.genetic_results.map((gr: any) => (
                  <tr key={gr.mutation} className="hover:bg-gray-50">
                    <td className="border px-3 py-2 font-bold">{gr.mutation}</td>
                    <td className="border px-3 py-2 text-right font-mono">{gr.score?.toFixed(4)}</td>
                    <td className="border px-3 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        gr.confidence_label === 'Conclusive' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {gr.confidence_label || gr.status}
                      </span>
                    </td>
                    <td className="border px-3 py-2 text-center text-xs">
                      <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                        {gr.prediction_method || 'xgboost'}
                      </span>
                    </td>
                    <td className="border px-3 py-2 text-xs">
                      {gr.shap_decomposition ? (
                        <div className="flex items-center gap-1">
                          <div className="flex-1 bg-gray-100 rounded h-3 overflow-hidden flex">
                            <div
                              className="h-full bg-blue-500"
                              style={{ width: `${gr.shap_decomposition.embedding_contribution_pct || 0}%` }}
                              title={`Embeddings: ${gr.shap_decomposition.embedding_contribution_pct}%`}
                            />
                            <div
                              className="h-full bg-red-400"
                              style={{ width: `${gr.shap_decomposition.pattern_contribution_pct || 0}%` }}
                              title={`Patterns: ${gr.shap_decomposition.pattern_contribution_pct}%`}
                            />
                          </div>
                          <span className="text-[10px] whitespace-nowrap">
                            {gr.shap_decomposition.embedding_contribution_pct?.toFixed(0)}% / {gr.shap_decomposition.pattern_contribution_pct?.toFixed(0)}%
                          </span>
                        </div>
                      ) : <span className="text-gray-400">—</span>}
                    </td>
                    {rb.use_choquet && (
                      <td className="border px-3 py-2 text-xs">
                        {gr.choquet_shapley?.shapley_values ? (
                          <div className="flex flex-wrap gap-0.5">
                            {Object.entries(gr.choquet_shapley.shapley_values as Record<string, number>)
                              .sort(([, a], [, b]) => (b as number) - (a as number))
                              .slice(0, 3)
                              .map(([pat, val]) => (
                                <span key={pat} className="bg-gray-100 rounded px-1 py-0.5">
                                  <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: PATTERN_COLORS[pat] || '#ccc' }} />
                                  {(val as number).toFixed(2)}
                                </span>
                              ))}
                          </div>
                        ) : <span className="text-gray-400">—</span>}
                      </td>
                    )}
                    <td className="border px-3 py-2 text-xs text-gray-500">
                      {gr.disclaimer ? (
                        <span className="text-yellow-700">{gr.disclaimer}</span>
                      ) : <span className="text-green-600">Reliable prediction</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Legend */}
            <div className="flex gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-3 h-1.5 bg-blue-500 inline-block rounded" /> Embedding dims (0-511)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-1.5 bg-red-400 inline-block rounded" /> Pattern dims (512-517)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
           CARD 2: Attention + Pattern Visualisation
         ══════════════════════════════════════════════════════════════ */}
      {rb?.pattern_results && (
        <div className="mb-6 border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 flex items-center justify-between">
            <h3 className="font-bold text-blue-900">Card 2 — Attention + Pattern Visualisation</h3>
            <div className="flex gap-2">
              <button
                className={`px-3 py-1 rounded text-xs ${!showAttnOverlay ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
                onClick={() => setShowAttnOverlay(false)}
              >
                Pattern Overlay
              </button>
              {attnArt && (
                <button
                  className={`px-3 py-1 rounded text-xs ${showAttnOverlay ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
                  onClick={() => setShowAttnOverlay(true)}
                >
                  ABMIL Attention Map
                </button>
              )}
            </div>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 gap-6">
              {/* Left: Original / Overlay toggle */}
              <div>
                <h4 className="font-semibold mb-2 text-sm">
                  {showAttnOverlay ? 'Spatial Attention Map (Top-200 tiles)' : 'Pattern Overlay (Tile-level colour map)'}
                </h4>
                <div className="border rounded bg-gray-100 h-72 flex items-center justify-center overflow-hidden">
                  {showAttnOverlay && attnArt ? (
                    <img src={getArtifactUrl(attnArt.uri)} alt="ABMIL attention heatmap" className="max-h-full max-w-full object-contain" />
                  ) : roiArt ? (
                    <img src={getArtifactUrl(roiArt.uri)} alt="ROI pattern overlay" className="max-h-full max-w-full object-contain" />
                  ) : (
                    <span className="text-gray-400 text-sm">Process image to see overlay</span>
                  )}
                </div>
                {/* Color legend */}
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  {Object.entries(PATTERN_COLORS).map(([pattern, color]) => (
                    <span key={pattern} className="flex items-center gap-1">
                      <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: color }} />
                      <span className="capitalize">{pattern}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Right: Pattern composition + enrichment chart */}
              <div>
                <h4 className="font-semibold mb-2 text-sm">Pattern Composition</h4>
                <div className="bg-yellow-50 border border-yellow-300 rounded p-2 mb-3 text-xs text-yellow-800">
                  Predominant: <strong className="capitalize">{rb.predominant_pattern}</strong>
                  {' | '}Evidence: {rb.evidence_source}
                </div>

                {/* Bar chart */}
                <div className="space-y-1">
                  {rb.pattern_results
                    .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
                    .map((p: any) => (
                    <div key={p.pattern} className="flex items-center gap-2">
                      <span className="text-xs w-24 text-right capitalize">{p.pattern}</span>
                      <div className="flex-1 bg-gray-100 rounded h-5 overflow-hidden">
                        <div
                          className="h-full rounded transition-all duration-500"
                          style={{
                            width: `${Math.min(p.percentage || 0, 100)}%`,
                            backgroundColor: PATTERN_COLORS[p.pattern] || '#ccc',
                            opacity: 0.8,
                          }}
                        />
                      </div>
                      <span className="text-xs font-mono w-14">{(p.percentage || 0).toFixed(1)}%</span>
                      <span className={`text-[10px] ${p.is_conclusive ? 'text-green-600' : 'text-red-500'}`}>
                        {p.is_conclusive ? 'YES' : 'INC'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
           CARD 3: Ontology-Grounded Case Explanation (placeholder)
         ══════════════════════════════════════════════════════════════ */}
      {rb?.genetic_results && (
        <div className="mb-6 border rounded-lg shadow-sm overflow-hidden">
          <div className="bg-purple-50 border-b border-purple-200 px-4 py-2">
            <h3 className="font-bold text-purple-900">Card 3 — Ontology-Grounded Case Explanation</h3>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-3 gap-4">
              {/* SPARQL results */}
              <div className="bg-gray-50 rounded p-3">
                <h4 className="font-semibold text-xs mb-2 text-gray-700">SPARQL Query Chain</h4>
                <p className="text-xs text-gray-500 mb-2">pattern → gene → treatment</p>
                <div className="space-y-1 text-xs">
                  {rb.genetic_results
                    .filter((gr: any) => gr.score >= 0.5)
                    .map((gr: any) => (
                      <div key={gr.mutation} className="bg-white rounded px-2 py-1 border">
                        <span className="font-bold">{gr.mutation}</span>
                        <span className="text-gray-400 mx-1">→</span>
                        <span className="text-gray-600">
                          {gr.mutation === 'EGFR' ? 'Osimertinib, Erlotinib' :
                           gr.mutation === 'TP53' ? 'Platinum-based chemo' :
                           gr.mutation === 'KRAS' ? 'Sotorasib (G12C)' :
                           gr.mutation === 'STK11' ? 'Pembrolizumab (limited)' :
                           gr.mutation === 'KEAP1' ? 'No targeted therapy' :
                           'Under investigation'}
                        </span>
                      </div>
                    ))}
                </div>
              </div>

              {/* KG summary */}
              <div className="bg-gray-50 rounded p-3">
                <h4 className="font-semibold text-xs mb-2 text-gray-700">Knowledge Graph</h4>
                <p className="text-xs text-gray-500 mb-2">NCIt + MONDO + SO (case-filtered)</p>
                <div className="text-xs text-gray-600">
                  <div>Nodes: patterns ({rb.pattern_results?.length}), genes ({rb.genetic_results?.length})</div>
                  <div>Ontologies: NCIt, MONDO</div>
                  <a href="#" onClick={(e) => { e.preventDefault(); }} className="text-blue-600 underline text-xs mt-1 inline-block">
                    View full graph in Graph tab →
                  </a>
                </div>
              </div>

              {/* DeepSearch + LLM */}
              <div className="bg-gray-50 rounded p-3">
                <h4 className="font-semibold text-xs mb-2 text-gray-700">LLM Explanation</h4>
                <p className="text-xs text-gray-500 mb-2">Clinical narrative with guardrails</p>
                <div className="text-xs text-gray-600">
                  <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px] font-medium mr-1">DeepSearch</span>
                  Literature-grounded relations available
                </div>
                <a href="#" onClick={(e) => { e.preventDefault(); }} className="text-blue-600 underline text-xs mt-2 inline-block">
                  Generate explanation in Graph tab →
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Disclaimers */}
      {rb?.disclaimers && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          <strong>Disclaimers:</strong>
          <ul className="list-disc ml-4 mt-1">
            {rb.disclaimers.map((d: string, i: number) => <li key={i}>{d}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}
