import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, getResultBundle, getArtifacts, getArtifactUrl, getImages } from '../api';

interface Props {
  caseId: string;
  imageId?: string | null;
  resultBundleId?: string | null;
}

type LayerMode = 'original' | 'pattern' | 'attention' | 'combined';

const PATTERN_COLORS: Record<string, string> = {
  lepidic: '#E6FF32', acinar: '#00FF00', papillary: '#0000FF',
  micropapillary: '#FFD700', solid: '#FF0000', mucinous: '#FFA500',
};

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

  const thumbnailUrl = thumbArt?.uri ? getArtifactUrl(thumbArt.uri) : null;
  const patternUrl = roiArt?.uri ? getArtifactUrl(roiArt.uri) : null;
  const attentionUrl = attnArt?.uri ? getArtifactUrl(attnArt.uri) : null;
  const combinedUrl = combArt?.uri ? getArtifactUrl(combArt.uri) : null;
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

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    setPanStart({ ...pan });
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return;
    setPan({ x: panStart.x + (e.clientX - dragStart.x), y: panStart.y + (e.clientY - dragStart.y) });
  }, [dragging, dragStart, panStart]);

  const handleMouseUp = useCallback(() => setDragging(false), []);
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

  const rb = bundle.data;
  const genetics = rb?.genetic_results || [];
  const patterns = rb?.pattern_results || [];

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
            <span>Pattern: <strong className="text-white capitalize">{rb.predominant_pattern}</strong></span>
            <span>Tiles: <strong className="text-white">{rb.morphologic_profile?.n_tiles_total?.toLocaleString()}</strong></span>
            <span>Pipeline: <strong className="text-green-400">v{rb.pipeline_version}</strong></span>
          </div>
        )}
        <div className="text-gray-500 text-[10px] ml-2">Scroll=zoom Drag=pan 1/2/3/4 +−0</div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Canvas */}
        <div
          className="flex-1 bg-gray-950 overflow-hidden relative select-none"
          style={{ cursor: dragging ? 'grabbing' : 'grab' }}
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
              <img src={activeUrl} alt={`${layer} view`} draggable={false}
                onLoad={() => setImgLoaded(true)} onError={() => setImgError(true)}
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

          <div className="absolute bottom-3 left-3 bg-black/70 text-white text-xs font-mono px-2 py-1 rounded">
            {(zoom * 100).toFixed(0)}% | {layer} {imgLoaded ? '✓' : '⏳'}
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
              {gr.shap_decomposition?.embedding_contribution_pct != null && (
                <div className="mt-1 h-1.5 rounded bg-gray-700 overflow-hidden flex">
                  <div className="bg-blue-500 h-full" style={{ width: `${gr.shap_decomposition.embedding_contribution_pct}%` }} />
                  <div className="bg-red-400 h-full" style={{ width: `${gr.shap_decomposition.pattern_contribution_pct}%` }} />
                </div>
              )}
            </div>
          )) : <p className="text-gray-500 text-xs">Process an image first</p>}

          <h4 className="text-gray-300 text-xs font-bold mt-4 mb-2 uppercase tracking-wide">Patterns</h4>
          {patterns.sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0)).map((p: any) => (
            <div key={p.pattern} className="flex items-center gap-1.5 mb-1">
              <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: PATTERN_COLORS[p.pattern] || '#888' }} />
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
        </div>
      </div>
    </div>
  );
}
