import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getImages, uploadImage, processImage, getJob, getLatestResults, getArtifactUrl } from '../api';

// Pattern color palette (DERCAS 7)
const PATTERN_COLORS: Record<string, string> = {
  lepidic: '#FFFF00',
  acinar: '#00FF00',
  papillary: '#0000FF',
  micropapillary: '#FF00FF',
  solid: '#FF0000',
  mucinous: '#FFA500',
};

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
  const [autoSelected, setAutoSelected] = useState(false);

  const images = useQuery({
    queryKey: ['images', caseId],
    queryFn: () => getImages(caseId).then(r => r.data),
  });

  // Auto-select first image when images load
  useEffect(() => {
    if (!autoSelected && images.data && images.data.length > 0 && !selImage) {
      const firstImg = images.data[0];
      setSelImage(firstImg.image_id);
      onImageSelected(firstImg.image_id);
      setAutoSelected(true);
    }
  }, [images.data, autoSelected, selImage, onImageSelected]);

  // Get viewer URL using the artifacts proxy (works from browser)
  const selImageData = images.data?.find((img: any) => img.image_id === selImage);
  const viewerUrl = selImageData?.storage_uri ? getArtifactUrl(selImageData.storage_uri) : null;

  const results = useQuery({
    queryKey: ['results', selImage],
    queryFn: async () => {
      try {
        const r = await getLatestResults(selImage!);
        return r.data;
      } catch (err: any) {
        // 404 = no results yet (image not processed); treat as empty, not error
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
    onSuccess: (r) => setJobId(r.data.job_id),
  });

  // When job completes, refetch results
  React.useEffect(() => {
    if (job.data?.status === 'COMPLETED' && job.data?.result_bundle_id) {
      onResultsReady(job.data.result_bundle_id);
      results.refetch();
      setJobId(null);
    }
  }, [job.data?.status]);

  // Propagate result_bundle_id when results load (e.g., pre-existing data)
  React.useEffect(() => {
    if (results.data?.result_bundle_id) {
      onResultsReady(results.data.result_bundle_id);
    }
  }, [results.data?.result_bundle_id, onResultsReady]);

  const rb = results.data;

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
            Process / Highlight Patterns
          </button>
        )}
        {jobId && job.data && (
          <span className="self-center text-sm text-gray-600">
            Job: {job.data.status} {job.data.status === 'RUNNING' && '...'}
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

      <div className="grid grid-cols-2 gap-6">
        {/* Left: Original image */}
        <div>
          <h3 className="font-semibold mb-2">Original Image</h3>
          <div className="border rounded bg-gray-100 h-80 flex items-center justify-center overflow-hidden">
            {viewerUrl ? (
              selImageData && ['svs', 'tif', 'tiff'].includes((selImageData.format || '').toLowerCase()) ? (
                <span className="text-gray-600 text-sm px-4 text-center">
                  Whole-slide image (.{selImageData.format}). Browsers cannot preview this format. Click &quot;Process / Highlight Patterns&quot; to generate overlay and results.
                </span>
              ) : (
                <img src={viewerUrl} alt="Histopathological" className="max-h-full max-w-full object-contain" />
              )
            ) : (
              <span className="text-gray-400 text-sm">Select or upload an image</span>
            )}
          </div>
        </div>

        {/* Right: Overlay + results */}
        <div>
          <h3 className="font-semibold mb-2">ROI Overlay — Pattern Predictions</h3>
          <div className="border rounded bg-gray-100 h-80 flex items-center justify-center overflow-hidden">
            {rb?.xai_artifacts?.find((a: any) => a.type === 'roi_overlay') ? (
              <img
                src={getArtifactUrl(rb.xai_artifacts.find((a: any) => a.type === 'roi_overlay').uri)}
                alt="ROI pattern overlay"
                className="max-h-full max-w-full object-contain"
              />
            ) : rb?.pattern_results ? (
              <span className="text-sm text-gray-600">Overlay available (see SHAP tab)</span>
            ) : (
              <span className="text-gray-400 text-sm">Process image to see overlay</span>
            )}
          </div>
          {/* Color legend */}
          {rb?.pattern_results && (
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {Object.entries(PATTERN_COLORS).map(([pattern, color]) => (
                <span key={pattern} className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: color }} />
                  <span className="capitalize">{pattern}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Pattern composition table (OBLIGATORIO — UC-IMG-03) */}
      {rb?.pattern_results && (
        <div className="mt-6">
          <h3 className="font-semibold mb-2">Pattern Composition (Table)</h3>
          <div className="bg-yellow-50 border border-yellow-300 rounded p-2 mb-3 text-xs text-yellow-800">
            Predominant pattern: <strong>{rb.predominant_pattern}</strong>
            {' | '}Evidence: {rb.evidence_source} | {rb.intended_use}
          </div>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border px-3 py-2 text-left">Pattern</th>
                <th className="border px-3 py-2 text-left">Color</th>
                <th className="border px-3 py-2 text-right">Score</th>
                <th className="border px-3 py-2 text-right">Percentage</th>
                <th className="border px-3 py-2 text-center">Conclusive</th>
              </tr>
            </thead>
            <tbody>
              {rb.pattern_results.map((pr: any) => (
                <tr key={pr.pattern} className="hover:bg-gray-50">
                  <td className="border px-3 py-2 font-medium capitalize">{pr.pattern}</td>
                  <td className="border px-3 py-2">
                    <span className="inline-block w-4 h-4 rounded" style={{ backgroundColor: PATTERN_COLORS[pr.pattern] || '#ccc' }} />
                  </td>
                  <td className="border px-3 py-2 text-right font-mono">{pr.score.toFixed(4)}</td>
                  <td className="border px-3 py-2 text-right font-mono">{pr.percentage.toFixed(1)}%</td>
                  <td className="border px-3 py-2 text-center">
                    {pr.is_conclusive ? (
                      <span className="text-green-600 font-bold">YES</span>
                    ) : (
                      <span className="text-red-500 font-bold">INCONCLUSIVE</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Genetic results */}
          {rb.genetic_results && (
            <>
              <h3 className="font-semibold mt-6 mb-2">Mutation Predictions</h3>
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border px-3 py-2 text-left">Gene</th>
                    <th className="border px-3 py-2 text-right">Score</th>
                    <th className="border px-3 py-2 text-center">Status</th>
                    <th className="border px-3 py-2 text-left">Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {rb.genetic_results.map((gr: any) => (
                    <tr key={gr.mutation}>
                      <td className="border px-3 py-2 font-bold">{gr.mutation}</td>
                      <td className="border px-3 py-2 text-right font-mono">{gr.score.toFixed(4)}</td>
                      <td className="border px-3 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          gr.status === 'POS' ? 'bg-red-100 text-red-700' :
                          gr.status === 'NEG' ? 'bg-green-100 text-green-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>{gr.status}</span>
                      </td>
                      <td className="border px-3 py-2 text-xs text-gray-500">{gr.evidence_source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {/* Disclaimers */}
          {rb.disclaimers && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              <strong>Disclaimers:</strong>
              <ul className="list-disc ml-4 mt-1">
                {rb.disclaimers.map((d: string, i: number) => <li key={i}>{d}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
