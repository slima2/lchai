import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getImages, uploadImage, processImage, getJob, getLatestResults, getArtifactUrl, createPatient, createCase, api } from '../api';

const PATTERN_COLORS: Record<string, string> = {
  lepidic: '#E6FF32',
  acinar: '#00FF00',
  papillary: '#0000FF',
  micropapillary: '#FFD700',
  solid: '#FF0000',
  mucinous: '#FFA500',
};

const GENES_V2 = ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10'];

interface Props {
  caseId: string;
  imageId?: string | null;
  onImageSelected: (id: string) => void;
  onResultsReady: (rbId: string) => void;
  onCaseChanged: (caseId: string) => void;
}

export default function ImagePanel({ caseId, imageId: initialImageId, onImageSelected, onResultsReady, onCaseChanged }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [selImage, setSelImage] = useState<string | null>(initialImageId || null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [processedImageId, setProcessedImageId] = useState<string | null>(null);
  const [autoSelected, setAutoSelected] = useState(false);
  const [showAttnOverlay, setShowAttnOverlay] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  const images = useQuery({
    queryKey: ['images', caseId],
    queryFn: () => getImages(caseId).then(r => r.data),
  });

  useEffect(() => {
    setAutoSelected(false);
    setSelImage(null);
  }, [caseId]);

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
    mutationFn: async (file: File) => {
      const filename = file.name.replace(/\.[^.]+$/, '');
      const uniqueId = `${filename}_${Date.now()}`;
      let patientId: string;
      try {
        const patRes = await createPatient({ external_id: uniqueId });
        patientId = patRes.data.patient_id;
      } catch {
        const patRes = await createPatient({ external_id: `${uniqueId}_${Math.random().toString(36).slice(2, 6)}` });
        patientId = patRes.data.patient_id;
      }
      const caseRes = await createCase({ patient_id: patientId });
      const newCaseId = caseRes.data.case_id;
      setUploadProgress(0);
      const imgRes = await uploadImage(newCaseId, file, (pct) => setUploadProgress(pct));
      setUploadProgress(null);
      return { ...imgRes, newCaseId, fileName: file.name, fileSize: file.size };
    },
    onSuccess: (r: any) => {
      setUploadProgress(null);
      const newImageId = r.data.image_id;
      onCaseChanged(r.newCaseId);
      setTimeout(() => {
        setSelImage(newImageId);
        onImageSelected(newImageId);
        setAutoSelected(true);
      }, 200);
    },
    onError: () => {
      setUploadProgress(null);
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

  const params = useQuery({
    queryKey: ['system-params'],
    queryFn: () => api.get('/parameters').then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  });

  const rb = results.data;
  const isV2 = rb?.pipeline_version?.startsWith('2');

  const aurocValues: Record<string, number> = params.data?.auroc_values || {};
  const aurocThreshold: number = params.data?.auroc_threshold ?? 0.70;

  const roiArt = rb?.xai_artifacts?.find((a: any) => a.type === 'roi_overlay');
  const attnArt = rb?.xai_artifacts?.find((a: any) => a.type === 'attention_overlay');

  return (
    <div>
      {/* Upload bar */}
      <div className="flex gap-3 mb-4">
        <input ref={fileRef} type="file" accept=".png,.jpg,.jpeg,.tif,.tiff,.svs,.bif" className="hidden" onChange={e => {
          if (e.target.files?.[0]) upload.mutate(e.target.files[0]);
        }} />
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
              <div className="bg-blue-500 h-full rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
            </div>
            <span className="text-xs font-mono text-blue-700 whitespace-nowrap">{uploadProgress}%</span>
          </div>
        )}
        {uploadProgress === null && <span className="text-gray-500 text-xs self-center">Supported: PNG, JPEG, TIFF, SVS, BIF</span>}
        {selImage && (
          <button className="bg-purple-600 text-white px-4 py-2 rounded text-sm" onClick={() => process.mutate()}>
            Analyze Slide
          </button>
        )}
        {isV2 && (
          <span className="self-center text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded font-medium">
            v2.0 Pipeline
          </span>
        )}
      </div>

      {/* Processing progress modal */}
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
              const estMin = tiles > 0 ? Math.ceil(tiles * 0.05 / 60) : 0;
              return (
                <>
                  <p className="text-xs text-gray-600 mb-1">
                    Slide: <strong>{slideName}...</strong> {slideFormat && `(${slideFormat})`}
                  </p>
                  <p className="text-xs text-gray-500 mb-4">
                    {status === 'PENDING' ? (
                      <span className="text-amber-600 font-medium">Waiting in queue... another job is being processed.</span>
                    ) : (
                      <>
                        v2.0 Pipeline: CTransPath + ABMIL + Choquet
                        {tiles > 0 && <span className="ml-1 font-medium text-blue-600">— {tiles.toLocaleString()} tiles (~{estMin} min)</span>}
                      </>
                    )}
                  </p>
                </>
              );
            })()}

            {/* Progress bar */}
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

            {/* Stage details */}
            <div className="bg-gray-50 rounded p-3 text-xs text-gray-500 space-y-1">
              <div className={`flex items-center gap-2 ${(job.data.progress || 0) >= 0.05 ? 'text-green-600' : ''}`}>
                <span>{(job.data.progress || 0) >= 0.10 ? '✓' : '⏳'}</span> Decoding image
              </div>
              <div className={`flex items-center gap-2 ${(job.data.progress || 0) >= 0.20 ? 'text-green-600' : ''}`}>
                <span>{(job.data.progress || 0) >= 0.50 ? '✓' : (job.data.progress || 0) >= 0.20 ? '⏳' : '○'}</span> CTransPath tile inference {(() => {
                  const tileMatch = (job.data.stage || '').match(/(\d+)\s*tiles/);
                  if (tileMatch) {
                    const tiles = parseInt(tileMatch[1]);
                    const mins = Math.ceil(tiles * 0.05 / 60);
                    return `(~${mins} min for ${tiles.toLocaleString()} tiles)`;
                  }
                  return '';
                })()}
              </div>
              <div className={`flex items-center gap-2 ${(job.data.progress || 0) >= 0.55 ? 'text-green-600' : ''}`}>
                <span>{(job.data.progress || 0) >= 0.65 ? '✓' : (job.data.progress || 0) >= 0.55 ? '⏳' : '○'}</span> Mutation prediction (ABMIL/Choquet)
              </div>
              <div className={`flex items-center gap-2 ${(job.data.progress || 0) >= 0.65 ? 'text-green-600' : ''}`}>
                <span>{(job.data.progress || 0) >= 0.75 ? '✓' : (job.data.progress || 0) >= 0.65 ? '⏳' : '○'}</span> Ablation + permutation analysis
              </div>
              <div className={`flex items-center gap-2 ${(job.data.progress || 0) >= 0.75 ? 'text-green-600' : ''}`}>
                <span>{(job.data.progress || 0) >= 0.85 ? '✓' : (job.data.progress || 0) >= 0.75 ? '⏳' : '○'}</span> SHAP decomposition
              </div>
              <div className={`flex items-center gap-2 ${(job.data.progress || 0) >= 0.85 ? 'text-green-600' : ''}`}>
                <span>{(job.data.progress || 0) >= 0.95 ? '✓' : (job.data.progress || 0) >= 0.85 ? '⏳' : '○'}</span> Saving results
              </div>
            </div>

            <button
              className="mt-4 w-full py-2 bg-red-100 text-red-700 rounded text-sm font-medium hover:bg-red-200 transition"
              onClick={async () => {
                const currentJobId = jobId;
                setJobId(null);
                try {
                  const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                  const res = await fetch(`${API}/api/v1/jobs/${currentJobId}:cancel`, { method: 'POST' });
                  if (res.ok) {
                    const data = await res.json();
                    if (data.cleaned) {
                      onCaseChanged(caseId);
                    }
                  }
                } catch { /* best effort */ }
                images.refetch();
              }}
            >
              Cancel and discard
            </button>
          </div>
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
                  <th className="border px-3 py-2 text-left">Interpretability</th>
                  <th className="border px-3 py-2 text-left">Interpretation</th>
                </tr>
              </thead>
              <tbody>
                {rb.genetic_results.map((gr: any) => {
                  const prob = (gr.score || 0);
                  const pct = (prob * 100).toFixed(1);
                  const geneAuroc = aurocValues[gr.mutation] ?? 0;
                  const isConcl = geneAuroc >= aurocThreshold;
                  const isPos = prob >= 0.5;

                  const aurocStr = geneAuroc > 0 ? ` (AUROC=${geneAuroc.toFixed(3)})` : '';
                  let interpretation = '';
                  if (isConcl && isPos) {
                    interpretation = `High probability (${pct}%) of ${gr.mutation} mutation. This prediction is reliable${aurocStr}. Confirm with molecular testing.`;
                  } else if (isConcl && !isPos) {
                    interpretation = `Low probability (${pct}%) of ${gr.mutation} mutation — likely wild-type. This prediction is reliable${aurocStr}.`;
                  } else if (!isConcl && isPos) {
                    interpretation = `Elevated probability (${pct}%) but the model has limited accuracy for ${gr.mutation}${aurocStr}. Molecular testing required.`;
                  } else {
                    interpretation = `Low probability (${pct}%). However, ${gr.mutation} has limited predictive accuracy${aurocStr}. Molecular testing recommended.`;
                  }

                  return (
                  <tr key={gr.mutation} className="hover:bg-gray-50">
                    <td className="border px-3 py-2 font-bold">{gr.mutation}</td>
                    <td className="border px-3 py-2 text-right font-mono">{pct}%</td>
                    <td className="border px-3 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        isConcl ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {isConcl ? 'Conclusive' : 'Inconclusive'}
                      </span>
                    </td>
                    <td className="border px-3 py-2 text-center text-xs">
                      <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                        {gr.prediction_method || 'xgboost'}
                      </span>
                    </td>
                    <td className="border px-3 py-2 text-xs">
                      {(gr.prediction_method || '').includes('proposed') && gr.shap_decomposition ? (
                        <div>
                          <div className="text-[10px] text-gray-500 mb-0.5">SHAP Split (Emb/Pat)</div>
                          <div className="flex items-center gap-1">
                            <div className="flex-1 bg-gray-100 rounded h-3 overflow-hidden flex">
                              <div className="h-full bg-blue-500"
                                style={{ width: `${gr.shap_decomposition.embedding_contribution_pct || 0}%` }} />
                              <div className="h-full bg-red-400"
                                style={{ width: `${gr.shap_decomposition.pattern_contribution_pct || 0}%` }} />
                            </div>
                            <span className="text-[10px] whitespace-nowrap">
                              {gr.shap_decomposition.embedding_contribution_pct?.toFixed(0)}% / {gr.shap_decomposition.pattern_contribution_pct?.toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      ) : (gr.prediction_method || '').includes('Choquet') && gr.choquet_shapley?.shapley_values ? (
                        <div>
                          <div className="text-[10px] text-gray-500 mb-0.5">Choquet Shapley</div>
                          <div className="flex flex-wrap gap-0.5">
                            {Object.entries(gr.choquet_shapley.shapley_values as Record<string, number>)
                              .sort(([, a], [, b]) => (b as number) - (a as number))
                              .slice(0, 3)
                              .map(([pat, val]) => (
                                <span key={pat} className="bg-gray-100 rounded px-1 py-0.5 text-[10px]">
                                  <span className="w-2 h-2 rounded-full inline-block mr-0.5" style={{ backgroundColor: PATTERN_COLORS[pat] || '#ccc' }} />
                                  <span className="capitalize">{pat.slice(0, 3)}</span> {(val as number).toFixed(3)}
                                </span>
                              ))}
                          </div>
                        </div>
                      ) : (gr.prediction_method || '').includes('embedding') ? (
                        <span className="text-gray-400 text-[10px]">Visual features only</span>
                      ) : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="border px-3 py-2 text-xs text-gray-600 max-w-xs">
                      {interpretation}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Legend */}
            <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
              <span className="text-gray-400">Interpretability: </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-1.5 bg-blue-500 inline-block rounded" /> Emb
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-1.5 bg-red-400 inline-block rounded" /> Pat
              </span>
              <span className="text-gray-400 ml-1">(SHAP Split for proposed genes)</span>
              <span className="text-gray-400">|</span>
              <span className="text-gray-400">Choquet Shapley for FC genes</span>
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
                      <span className={`text-[10px] ${(p.percentage || 0) >= 5 ? 'text-green-600 font-medium' : 'text-gray-400'}`}>
                        {(p.percentage || 0) >= 20 ? 'Major' : (p.percentage || 0) >= 5 ? 'Minor' : ''}
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
            <h3 className="font-bold text-purple-900">Card 3 — Clinical Summary</h3>
          </div>
          <div className="p-4 text-sm text-gray-700 leading-relaxed">
            {(() => {
              const isDynConcl = (gene: string) => (aurocValues[gene] ?? 0) >= aurocThreshold;
              const posGenes = rb.genetic_results.filter((g: any) => g.score >= 0.5);
              const negGenes = rb.genetic_results.filter((g: any) => g.score < 0.5);
              const conclPos = posGenes.filter((g: any) => isDynConcl(g.mutation));
              const inconclPos = posGenes.filter((g: any) => !isDynConcl(g.mutation));
              const predominant = rb.predominant_pattern;
              const tiles = rb.morphologic_profile?.n_tiles_total || 0;

              return (
                <div className="space-y-3">
                  <p>
                    <strong>Histological analysis</strong> of this lung adenocarcinoma slide ({tiles.toLocaleString()} tissue tiles analyzed)
                    reveals a <strong className="capitalize">{predominant}</strong>-predominant pattern
                    ({rb.pattern_composition?.[predominant]?.toFixed(1)}% of tiles).
                    {rb.pattern_results?.filter((p: any) => p.percentage > 1 && p.pattern !== predominant)
                      .map((p: any) => ` ${p.pattern} (${p.percentage.toFixed(1)}%)`)
                      .join(',') && (
                      <span> Secondary patterns include
                        {rb.pattern_results
                          .filter((p: any) => p.percentage > 1 && p.pattern !== predominant)
                          .sort((a: any, b: any) => b.percentage - a.percentage)
                          .map((p: any) => ` ${p.pattern} (${p.percentage.toFixed(1)}%)`)
                          .join(',')}.
                      </span>
                    )}
                  </p>

                  {conclPos.length > 0 && (
                    <p>
                      <strong>Mutation predictions (reliable):</strong>{' '}
                      {conclPos.map((g: any) => `${g.mutation} (${((g.score || 0) * 100).toFixed(1)}%)`).join(', ')}
                      {' '}— these genes have model AUROC ≥ {aurocThreshold.toFixed(3)} and the predictions are considered reliable.
                      {conclPos.some((g: any) => g.mutation === 'TP53') && ' TP53 mutations are commonly associated with solid and micropapillary patterns.'}
                      {conclPos.some((g: any) => g.mutation === 'EGFR') && ' EGFR mutations correlate with lepidic and papillary patterns.'}
                    </p>
                  )}

                  {negGenes.filter((g: any) => isDynConcl(g.mutation)).length > 0 && (
                    <p>
                      <strong>Likely wild-type (reliable):</strong>{' '}
                      {negGenes.filter((g: any) => isDynConcl(g.mutation))
                        .map((g: any) => `${g.mutation} (${((g.score || 0) * 100).toFixed(1)}%)`).join(', ')}.
                    </p>
                  )}

                  {inconclPos.length > 0 && (
                    <p className="text-yellow-800 bg-yellow-50 p-2 rounded">
                      <strong>Requires molecular testing:</strong>{' '}
                      {inconclPos.map((g: any) => `${g.mutation} (${((g.score || 0) * 100).toFixed(1)}%)`).join(', ')}
                      {' '}— these genes cannot be reliably predicted from histology alone (AUROC &lt; {aurocThreshold.toFixed(3)}).
                    </p>
                  )}

                  <p className="text-xs text-gray-500 italic">
                    Prediction methods: {[...new Set(rb.genetic_results.map((g: any) => g.prediction_method))].join(', ')}.
                    Each gene uses its optimal model based on thesis Finding 2 (Lima et al., 2026).
                  </p>
                </div>
              );
            })()}
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
