import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, getResultBundle, getArtifacts, getArtifactUrl, getImages, getJob, submitPatternCorrections, getActiveLearningJob } from '../api';
import { patternColor, filterAllowedPatternResults, predominantPatternForDisplay, PATTERN_COLORS, type AnorakPattern } from '../patternConstants';

interface Props {
  caseId: string;
  imageId?: string | null;
  resultBundleId?: string | null;
}

type LayerMode = 'original' | 'pattern' | 'attention' | 'combined';

function pointInPolygon(x: number, y: number, polygon: {x: number; y: number}[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x, yi = polygon[i].y;
    const xj = polygon[j].x, yj = polygon[j].y;
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }
  return inside;
}

export default function ViewerPanel({ caseId, imageId, resultBundleId }: Props) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [layer, setLayer] = useState<LayerMode>('pattern');
  const [overlayOpacity, setOverlayOpacity] = useState(0.85);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; pattern: string } | null>(null);
  const [regionMap, setRegionMap] = useState<any[] | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // Active Learning: Correction mode with lasso drawing
  const [correctionMode, setCorrectionMode] = useState(false);
  const [selectedTiles, setSelectedTiles] = useState<Set<number>>(new Set());
  const [correctionPattern, setCorrectionPattern] = useState<string>('acinar');
  const [retrainJobId, setRetrainJobId] = useState<string | null>(null);
  const [retrainStatus, setRetrainStatus] = useState<string | null>(null);
  const [retrainProgress, setRetrainProgress] = useState(0);
  const [retrainStage, setRetrainStage] = useState('');
  const [lassoPoints, setLassoPoints] = useState<{x: number; y: number}[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [cacheBust, setCacheBust] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const queryClient = useQueryClient();

  const images = useQuery({
    queryKey: ['viewer-images', caseId],
    queryFn: () => getImages(caseId).then(r => r.data),
  });

  const params = useQuery({
    queryKey: ['system-params'],
    queryFn: () => api.get('/parameters').then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always' as const,
  });
  const aurocValues: Record<string, number> = params.data?.auroc_values || {};
  const aurocThreshold: number = params.data?.auroc_threshold ?? 0.70;
  const isDynConcl = (gene: string) => (aurocValues[gene] ?? 0) >= aurocThreshold;

  const bundle = useQuery({
    queryKey: ['viewer-bundle', resultBundleId],
    queryFn: () => getResultBundle(resultBundleId!).then(r => r.data),
    enabled: !!resultBundleId,
  });

  const artifacts = useQuery({
    queryKey: ['viewer-artifacts', resultBundleId],
    queryFn: () => getArtifacts(resultBundleId!).then(r => r.data),
    enabled: !!resultBundleId,
  });

  const selImageData = images.data?.find((img: any) => img.image_id === imageId);
  const isWSI = selImageData && ['svs', 'tif', 'tiff', 'bif'].includes((selImageData.format || '').toLowerCase());

  const allArts = artifacts.data || [];
  const thumbArt = allArts.find((a: any) => (a.type || a.artifact_type) === 'thumbnail');
  const roiArt = allArts.find((a: any) => (a.type || a.artifact_type) === 'roi_overlay');
  const attnArt = allArts.find((a: any) => (a.type || a.artifact_type) === 'attention_overlay');
  const combArt = allArts.find((a: any) => (a.type || a.artifact_type) === 'combined_overlay');
  const regionMapArt = allArts.find((a: any) => (a.type || a.artifact_type) === 'pattern_region_map');

  useEffect(() => {
    if (regionMapArt?.uri) {
      const url = getArtifactUrl(regionMapArt.uri);
      fetch(url).then(r => r.json()).then(data => setRegionMap(data)).catch(() => setRegionMap(null));
    }
  }, [regionMapArt?.uri]);

  const bust = cacheBust ? `&_cb=${cacheBust}` : '';
  const thumbnailUrl = thumbArt?.uri ? getArtifactUrl(thumbArt.uri) + bust : null;
  const patternUrl = roiArt?.uri ? getArtifactUrl(roiArt.uri) + bust : null;
  const attentionUrl = attnArt?.uri ? getArtifactUrl(attnArt.uri) + bust : null;
  const combinedUrl = combArt?.uri ? getArtifactUrl(combArt.uri) + bust : null;
  const originalUrl = thumbnailUrl || (isWSI ? patternUrl : (selImageData?.storage_uri ? getArtifactUrl(selImageData.storage_uri) : null));

  const activeUrl = layer === 'original' ? (originalUrl || patternUrl)
    : layer === 'pattern' ? (patternUrl || originalUrl)
    : layer === 'attention' ? (attentionUrl || patternUrl || originalUrl)
    : (combinedUrl || patternUrl || originalUrl);

  useEffect(() => { setImgLoaded(false); setImgError(false); }, [activeUrl]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom(z => Math.min(Math.max(z * (e.deltaY > 0 ? 0.85 : 1.18), 0.1), 30));
  }, []);

  const clientToNormalized = useCallback((clientX: number, clientY: number): { x: number; y: number } | null => {
    const img = imgRef.current;
    if (!img || !img.naturalWidth) return null;
    const rect = img.getBoundingClientRect();
    const xn = (clientX - rect.left) / rect.width;
    const yn = (clientY - rect.top) / rect.height;
    return { x: Math.max(0, Math.min(1, xn)), y: Math.max(0, Math.min(1, yn)) };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    if (correctionMode) {
      const pt = clientToNormalized(e.clientX, e.clientY);
      if (pt) {
        setIsDrawing(true);
        setLassoPoints([pt]);
        e.preventDefault();
      }
      return;
    }
    setDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    setPanStart({ ...pan });
  }, [pan, correctionMode, clientToNormalized]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (correctionMode && isDrawing) {
      const pt = clientToNormalized(e.clientX, e.clientY);
      if (pt) setLassoPoints(pts => [...pts, pt]);
      return;
    }
    if (!dragging) return;
    setPan({ x: panStart.x + (e.clientX - dragStart.x), y: panStart.y + (e.clientY - dragStart.y) });
  }, [dragging, dragStart, panStart, correctionMode, isDrawing, clientToNormalized]);

  const handleMouseUp = useCallback(() => {
    if (correctionMode && isDrawing && lassoPoints.length > 2 && regionMap) {
      const newSelected = new Set(selectedTiles);
      for (let i = 0; i < regionMap.length; i++) {
        const r = regionMap[i];
        const cx = r.xn + r.wn / 2;
        const cy = r.yn + r.hn / 2;
        if (pointInPolygon(cx, cy, lassoPoints)) {
          newSelected.add(i);
        }
      }
      setSelectedTiles(newSelected);
      setIsDrawing(false);
      setLassoPoints([]);
      return;
    }
    setIsDrawing(false);
    setLassoPoints([]);
    setDragging(false);
  }, [correctionMode, isDrawing, lassoPoints, regionMap, selectedTiles]);
  const resetView = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }); }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '0') { setZoom(1); setPan({ x: 0, y: 0 }); }
      if (e.key === '+' || e.key === '=') setZoom(z => Math.min(z * 1.4, 30));
      if (e.key === '-') setZoom(z => Math.max(z / 1.4, 0.1));
      if (e.key === '1') setLayer('original');
      if (e.key === '2') setLayer('pattern');
      if (e.key === '3') setLayer('attention');
      if (e.key === '4') setLayer('combined');
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Poll active-learning-service job
  useEffect(() => {
    if (!retrainJobId || retrainStatus === 'COMPLETED' || retrainStatus === 'FAILED') return;
    const interval = setInterval(async () => {
      try {
        const { data } = await getActiveLearningJob(retrainJobId);
        setRetrainProgress(data.progress || 0);
        setRetrainStage(data.error_detail || data.stage || '');
        if (data.status === 'COMPLETED') {
          setRetrainStatus('COMPLETED');
          setRetrainStage('Model updated successfully');
          setSelectedTiles(new Set());
          setCorrectionMode(false);
          setCacheBust(Date.now());
          queryClient.invalidateQueries({ queryKey: ['viewer-bundle', resultBundleId] });
          queryClient.invalidateQueries({ queryKey: ['viewer-artifacts', resultBundleId] });
          // Re-fetch region map with new data
          if (regionMapArt?.uri) {
            fetch(getArtifactUrl(regionMapArt.uri) + `&_cb=${Date.now()}`)
              .then(r => r.json()).then(d => setRegionMap(d)).catch(() => {});
          }
          setTimeout(() => { setRetrainJobId(null); setRetrainStatus(null); }, 4000);
        } else if (data.status === 'FAILED') {
          setRetrainStatus('FAILED');
          setRetrainStage(data.error_detail || 'Retrain failed');
        }
      } catch { /* ignore polling errors */ }
    }, 1500);
    return () => clearInterval(interval);
  }, [retrainJobId, retrainStatus, resultBundleId, queryClient]);

  const handleSubmitCorrections = useCallback(async () => {
    if (!regionMap || selectedTiles.size === 0 || !resultBundleId || !caseId) return;
    const corrections = Array.from(selectedTiles).map(idx => ({
      tile_index: idx,
      tile_x: regionMap[idx]?.xn || 0,
      tile_y: regionMap[idx]?.yn || 0,
      original_pattern: regionMap[idx]?.pattern || 'unknown',
      corrected_pattern: correctionPattern,
      corrected_by: 'pathologist (SOLCA)',
    }));
    try {
      setRetrainStatus('PENDING');
      setRetrainProgress(0);
      setRetrainStage('Submitting corrections...');
      const { data } = await submitPatternCorrections(resultBundleId, caseId, imageId || '', corrections);
      setRetrainJobId(data.job_id);
      setRetrainStatus('RUNNING');
    } catch (err: any) {
      setRetrainStatus('FAILED');
      setRetrainStage(err?.message || 'Submission failed');
    }
  }, [regionMap, selectedTiles, resultBundleId, caseId, correctionPattern]);

  const rb = bundle.data;
  const genetics = rb?.genetic_results || [];
  const patterns = useMemo(
    () => filterAllowedPatternResults(rb?.pattern_results || []).sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0)),
    [rb?.pattern_results],
  );
  const predominantLabel = rb ? predominantPatternForDisplay(rb.predominant_pattern, rb.pattern_results || []) : '—';

  return (
    <div className="flex flex-col h-[calc(100vh-140px)]">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-900 border-b border-gray-700 flex-shrink-0">
        <div className="flex gap-1">
          {(['original', 'pattern', 'attention', 'combined'] as LayerMode[]).map(m => (
            <button key={m} onClick={() => setLayer(m)}
              className={`px-3 py-1.5 rounded text-xs font-medium ${layer === m ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
              {m === 'original' ? '1 Original' : m === 'pattern' ? '2 Patterns' : m === 'attention' ? '3 Attention' : '4 Combined'}
            </button>
          ))}
        </div>
        <div className="w-px h-6 bg-gray-600 mx-1" />
        <button onClick={() => setZoom(z => Math.max(z / 1.4, 0.1))} className="px-2 py-1.5 bg-gray-700 text-gray-300 rounded text-xs hover:bg-gray-600">−</button>
        <span className="text-gray-300 text-xs font-mono min-w-[50px] text-center">{(zoom * 100).toFixed(0)}%</span>
        <button onClick={() => setZoom(z => Math.min(z * 1.4, 30))} className="px-2 py-1.5 bg-gray-700 text-gray-300 rounded text-xs hover:bg-gray-600">+</button>
        <button onClick={resetView} className="px-2 py-1.5 bg-gray-700 text-gray-300 rounded text-xs hover:bg-gray-600">Fit</button>
        <div className="w-px h-6 bg-gray-600 mx-1" />
        {layer !== 'original' && (
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-xs">Opacity:</span>
            <input type="range" min="0" max="100" value={overlayOpacity * 100}
              onChange={e => setOverlayOpacity(Number(e.target.value) / 100)} className="w-20 h-1 accent-blue-500" />
            <span className="text-gray-400 text-xs font-mono w-8">{(overlayOpacity * 100).toFixed(0)}%</span>
          </div>
        )}
        <div className="flex-1" />
        {rb && (
          <div className="flex gap-3 text-xs text-gray-400">
            <span>Pattern: <strong className="text-white capitalize">{predominantLabel}</strong></span>
            <span>Tiles: <strong className="text-white">{rb.morphologic_profile?.n_tiles_total?.toLocaleString()}</strong></span>
            <span>Pipeline: <strong className="text-green-400">v{rb.pipeline_version}</strong></span>
          </div>
        )}
        <div className="w-px h-6 bg-gray-600 mx-1" />
        <button
          onClick={() => { setCorrectionMode(m => !m); setSelectedTiles(new Set()); }}
          className={`px-3 py-1.5 rounded text-xs font-medium ${correctionMode ? 'bg-orange-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
          title="Toggle pattern correction mode (Active Learning)"
        >
          {correctionMode ? 'Exit Correction' : 'Correct Patterns'}
        </button>
        <div className="text-gray-500 text-[10px] ml-2">Scroll=zoom Drag=pan 1/2/3/4 +−0</div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Canvas */}
        <div
          className="flex-1 bg-gray-950 overflow-hidden relative select-none"
          style={{ cursor: correctionMode ? 'crosshair' : dragging ? 'grabbing' : 'grab' }}
          onWheel={handleWheel} onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}
        >
          {activeUrl ? (
            <div className="absolute inset-0 flex items-center justify-center"
              style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: 'center center' }}>
              {!imgLoaded && !imgError && (
                <div className="text-gray-500 text-sm animate-pulse absolute">Loading image...</div>
              )}
              {imgError && (
                <div className="text-red-400 text-sm absolute">Failed to load image</div>
              )}
              <img ref={imgRef} src={activeUrl} alt={`${layer} view`} draggable={false}
                onLoad={() => setImgLoaded(true)} onError={() => setImgError(true)}
                onMouseMove={(e) => {
                  if (!regionMap || (layer !== 'pattern' && layer !== 'combined')) { setTooltip(null); return; }
                  const img = imgRef.current;
                  if (!img) return;
                  const rect = img.getBoundingClientRect();
                  const xn = (e.clientX - rect.left) / rect.width;
                  const yn = (e.clientY - rect.top) / rect.height;
                  const hit = regionMap.find((r: any) =>
                    xn >= r.xn && xn <= r.xn + r.wn && yn >= r.yn && yn <= r.yn + r.hn
                  );
                  if (hit) {
                    setTooltip({ x: e.clientX, y: e.clientY, pattern: hit.pattern });
                  } else {
                    setTooltip(null);
                  }
                }}
                onMouseLeave={() => setTooltip(null)}
                style={{
                  maxWidth: 'none', maxHeight: 'none',
                  opacity: imgLoaded ? (layer === 'original' ? 1 : overlayOpacity) : 0,
                  imageRendering: zoom > 3 ? 'pixelated' : 'auto',
                }} />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              {!imageId ? 'Select an image from the Images tab' :
               !resultBundleId ? 'Process an image first (Images tab)' :
               artifacts.isLoading ? 'Loading artifacts...' :
               'No overlay found for this result'}
            </div>
          )}

          {isWSI && layer === 'original' && !thumbnailUrl && (
            <div className="absolute top-2 left-2 bg-yellow-900/80 text-yellow-200 text-xs px-3 py-1.5 rounded max-w-xs">
              WSI shown as pattern overlay. Switch to "2 Patterns" for analysis.
            </div>
          )}

          {tooltip && (
            <div
              className="fixed z-50 pointer-events-none bg-black/85 text-white text-xs font-bold px-3 py-1.5 rounded shadow-lg capitalize"
              style={{ left: tooltip.x + 12, top: tooltip.y - 30 }}
            >
              <span className="inline-block w-2.5 h-2.5 rounded-full mr-1.5" style={{
                backgroundColor: patternColor(tooltip.pattern),
              }} />
              {tooltip.pattern}
            </div>
          )}
          {/* Selected tile highlights + lasso — overlaid on the image using same transform */}
          {correctionMode && imgRef.current && (selectedTiles.size > 0 || (isDrawing && lassoPoints.length > 1)) && (
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              {/* Position a container exactly over the img using its bounding rect */}
              {(() => {
                const img = imgRef.current!;
                const rect = img.getBoundingClientRect();
                const container = img.closest('.bg-gray-950');
                const cRect = container?.getBoundingClientRect() || rect;
                const left = rect.left - cRect.left;
                const top = rect.top - cRect.top;
                return (
                  <div style={{ position: 'absolute', left, top, width: rect.width, height: rect.height }}>
                    {/* Selected tiles */}
                    {regionMap && Array.from(selectedTiles).map(idx => {
                      const r = regionMap[idx];
                      if (!r) return null;
                      const color = patternColor(correctionPattern);
                      return (
                        <div key={idx} className="absolute border-2 border-white/80"
                          style={{
                            left: `${r.xn * 100}%`, top: `${r.yn * 100}%`,
                            width: `${r.wn * 100}%`, height: `${r.hn * 100}%`,
                            backgroundColor: `${color}55`,
                          }} />
                      );
                    })}
                    {/* Lasso path */}
                    {isDrawing && lassoPoints.length > 1 && (
                      <svg className="absolute inset-0 w-full h-full">
                        <polyline
                          points={lassoPoints.map(p => `${p.x * rect.width},${p.y * rect.height}`).join(' ')}
                          fill="rgba(249,115,22,0.15)" stroke="#f97316" strokeWidth="2"
                          strokeDasharray="6 4" strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                );
              })()}
            </div>
          )}

          {/* Retrain progress bar */}
          {retrainStatus && (
            <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-gray-900/95 border border-gray-600 rounded-lg px-4 py-3 min-w-[320px] z-50 shadow-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white text-xs font-bold">
                  {retrainStatus === 'COMPLETED' ? 'Delta Training Complete' :
                   retrainStatus === 'FAILED' ? 'Delta Training Failed' :
                   'Delta Training in Progress...'}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                  retrainStatus === 'COMPLETED' ? 'bg-green-900 text-green-300' :
                  retrainStatus === 'FAILED' ? 'bg-red-900 text-red-300' :
                  'bg-blue-900 text-blue-300'
                }`}>{retrainStatus}</span>
              </div>
              <div className="h-2 bg-gray-700 rounded overflow-hidden mb-1">
                <div className={`h-full transition-all duration-500 ${retrainStatus === 'FAILED' ? 'bg-red-500' : retrainStatus === 'COMPLETED' ? 'bg-green-500' : 'bg-blue-500'}`}
                  style={{ width: `${retrainProgress * 100}%` }} />
              </div>
              <div className="text-gray-400 text-[10px]">{retrainStage}</div>
            </div>
          )}

          <div className="absolute bottom-3 left-3 bg-black/70 text-white text-xs font-mono px-2 py-1 rounded">
            {(zoom * 100).toFixed(0)}% | {layer} {correctionMode ? `| CORRECTION (${selectedTiles.size} selected)` : ''} {imgLoaded ? '✓' : '⏳'}
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-56 bg-gray-900 border-l border-gray-700 overflow-y-auto flex-shrink-0 p-3">
          <h4 className="text-gray-300 text-xs font-bold mb-3 uppercase tracking-wide">Mutation Report</h4>
          {genetics.length > 0 ? genetics.map((gr: any) => (
            <div key={gr.mutation} className="mb-2 p-2 rounded bg-gray-800">
              <div className="flex justify-between items-center">
                <span className="text-white text-sm font-bold">{gr.mutation}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                  isDynConcl(gr.mutation) ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'
                }`}>{isDynConcl(gr.mutation) ? 'Conclusive' : 'Inconclusive'}</span>
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-gray-400 text-xs">P(mut)</span>
                <span className="text-white text-xs font-mono">{((gr.score || 0) * 100).toFixed(1)}%</span>
              </div>
              {gr.shap_decomposition?.embedding_contribution_pct != null && (gr.prediction_method || '').includes('proposed') && (
                <div className="mt-1 h-1.5 rounded bg-gray-700 overflow-hidden flex" title={`Emb ${gr.shap_decomposition.embedding_contribution_pct}% / Pat ${gr.shap_decomposition.pattern_contribution_pct}%`}>
                  <div className="bg-blue-500 h-full" style={{ width: `${gr.shap_decomposition.embedding_contribution_pct}%` }} />
                  <div className="bg-red-400 h-full" style={{ width: `${gr.shap_decomposition.pattern_contribution_pct}%` }} />
                </div>
              )}
            </div>
          )) : <p className="text-gray-500 text-xs">Process an image first</p>}

          <h4 className="text-gray-300 text-xs font-bold mt-4 mb-2 uppercase tracking-wide">Patterns</h4>
          {patterns.map((p: any) => (
            <div key={p.pattern} className="flex items-center gap-1.5 mb-1">
              <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: patternColor(p.pattern) }} />
              <span className="text-gray-300 text-xs capitalize flex-1">{p.pattern}</span>
              <span className="text-gray-400 text-xs font-mono">{(p.percentage || 0).toFixed(1)}%</span>
            </div>
          ))}

          <div className="mt-4 pt-3 border-t border-gray-700">
            <h4 className="text-gray-300 text-xs font-bold mb-2 uppercase tracking-wide">Layers</h4>
            <div className="space-y-1 text-xs">
              {(['original', 'pattern', 'attention', 'combined'] as LayerMode[]).map(m => (
                <div key={m} className={`p-1.5 rounded cursor-pointer ${layer === m ? 'bg-gray-700' : 'hover:bg-gray-800'}`} onClick={() => setLayer(m)}>
                  <span className="text-gray-300">{
                    m === 'original' ? '1 — Original H&E' :
                    m === 'pattern' ? '2 — Pattern Overlay' :
                    m === 'attention' ? '3 — ABMIL Attention' :
                    '4 — Combined (Pat+Attn)'
                  }</span>
                </div>
              ))}
            </div>
          </div>

          {/* Active Learning: Correction Panel */}
          {correctionMode && (
            <div className="mt-4 pt-3 border-t border-orange-700">
              <h4 className="text-orange-300 text-xs font-bold mb-2 uppercase tracking-wide">
                Pattern Correction
              </h4>
              <p className="text-gray-400 text-[10px] mb-2">
                Draw a lasso around the region to correct (click &amp; drag),
                then assign the correct pattern. All tiles whose center falls
                inside your lasso will be selected. Draw multiple lassos to add more tiles.
              </p>
              <div className="mb-2">
                <label className="text-gray-400 text-[10px] block mb-1">Correct pattern:</label>
                <select
                  value={correctionPattern}
                  onChange={e => setCorrectionPattern(e.target.value)}
                  className="w-full bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-600"
                >
                  {Object.keys(PATTERN_COLORS).map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
                <div className="flex items-center gap-1 mt-1">
                  <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: patternColor(correctionPattern) }} />
                  <span className="text-gray-300 text-[10px] capitalize">{correctionPattern}</span>
                </div>
              </div>
              <div className="text-gray-400 text-[10px] mb-2">
                {selectedTiles.size} tile{selectedTiles.size !== 1 ? 's' : ''} selected
                {selectedTiles.size > 0 && regionMap && (
                  <span className="block mt-0.5">
                    From: {Array.from(selectedTiles).slice(0, 3).map(i =>
                      regionMap[i]?.pattern
                    ).filter(Boolean).join(', ')}
                    {selectedTiles.size > 3 && '...'}
                  </span>
                )}
              </div>
              <div className="flex gap-1">
                <button
                  onClick={handleSubmitCorrections}
                  disabled={selectedTiles.size === 0 || !!retrainStatus}
                  className="flex-1 px-2 py-1.5 bg-orange-600 text-white text-xs rounded font-medium disabled:opacity-40 hover:bg-orange-500"
                >
                  Save &amp; Retrain ({selectedTiles.size})
                </button>
                <button
                  onClick={() => setSelectedTiles(new Set())}
                  className="px-2 py-1.5 bg-gray-700 text-gray-300 text-xs rounded hover:bg-gray-600"
                >
                  Clear
                </button>
              </div>
              <p className="text-gray-500 text-[10px] mt-2 leading-tight">
                Delta training updates the FuzzyArcLoss V2 head only (backbone frozen).
                Mutation predictions for P/FC genes (STK11, KEAP1, KRAS, RBM10) will be re-computed.
                TP53/EGFR remain unchanged (embedding-only).
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
