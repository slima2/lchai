import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getResultBundle, getArtifacts, getArtifactUrl } from '../api';

interface Props {
  resultBundleId: string;
}

const GENES = ['EGFR', 'KRAS', 'TP53'];

const PATTERN_COLORS: Record<string, string> = {
  lepidic: '#FFEB3B',
  acinar: '#4CAF50',
  papillary: '#2196F3',
  micropapillary: '#E91E63',
  solid: '#F44336',
  mucinous: '#FF9800',
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
          <p className="text-[10px] mt-1 max-w-[200px] truncate">{uri}</p>
        </div>
      </div>
    );
  }

  return (
    <img
      src={imgUrl}
      alt={alt}
      className={className}
      onError={() => setError(true)}
    />
  );
}

export default function ShapPanel({ resultBundleId }: Props) {
  const [selGene, setSelGene] = useState('EGFR');

  const bundle = useQuery({
    queryKey: ['bundle', resultBundleId],
    queryFn: () => getResultBundle(resultBundleId).then(r => r.data),
  });

  const artifacts = useQuery({
    queryKey: ['artifacts', resultBundleId],
    queryFn: () => getArtifacts(resultBundleId).then(r => r.data),
  });

  const allArts = artifacts.data || [];

  // Filter artifacts by gene and type
  const barArt = allArts.find(
    (a: any) => a.artifact_type?.includes('bar') &&
    (a.gene?.toUpperCase() === selGene || a.gene?.toLowerCase() === selGene.toLowerCase())
  );
  const beeswarmArt = allArts.find(
    (a: any) => a.artifact_type?.includes('beeswarm') &&
    (a.gene?.toUpperCase() === selGene || a.gene?.toLowerCase() === selGene.toLowerCase())
  );
  const forceArt = allArts.find(
    (a: any) => a.artifact_type?.includes('force') &&
    (a.gene?.toUpperCase() === selGene || a.gene?.toLowerCase() === selGene.toLowerCase())
  );

  const mp = bundle.data?.morphologic_profile;
  const patterns = bundle.data?.pattern_results || [];
  const genetics = bundle.data?.genetic_results || [];

  // Find the selected gene's result
  const geneResult = genetics.find((g: any) => g.mutation === selGene);

  return (
    <div>
      <div className="flex gap-3 mb-4 items-center">
        <h2 className="text-lg font-semibold">SHAP / Explainability</h2>
        <div className="flex gap-1 ml-4">
          {GENES.map(g => (
            <button
              key={g}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                selGene === g
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
              onClick={() => setSelGene(g)}
            >
              {g}
              {genetics.find((gr: any) => gr.mutation === g) && (
                <span className={`ml-1 text-xs ${
                  genetics.find((gr: any) => gr.mutation === g)?.status === 'POS' ? 'text-red-200' :
                  genetics.find((gr: any) => gr.mutation === g)?.status === 'NEG' ? 'text-green-200' :
                  'text-yellow-200'
                }`}>
                  ({genetics.find((gr: any) => gr.mutation === g)?.status})
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Limitations banner */}
      <div className="bg-yellow-50 border border-yellow-300 rounded p-3 mb-4 text-xs text-yellow-800">
        <strong>Limitations:</strong> SHAP values are computed from morphology aggregation (thesis evidence only).
        This is NOT a MIL (multiple instance learning) explanation. Evidence source: THESIS_INTERNAL.
        Mutation predictions are based on XGBoost models trained on TCGA morphological features.
      </div>

      {/* Clarification: distribution vs SHAP importance */}
      <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4 text-xs text-blue-800">
        <strong>Distribución vs SHAP:</strong> La tabla &quot;Pattern Composition&quot; muestra la <em>composición de este caso</em> (porcentaje de tiles por patrón).
        El <strong>SHAP Bar</strong> muestra la <em>importancia global</em> de cada feature en el modelo (cuánto influye en la predicción, en promedio).
        No tienen por qué coincidir: un patrón puede ser muy frecuente en el caso (ej. solid 56.7%) pero tener baja importancia global si el modelo discrimina más por otros (ej. lepidic, papillary). Los gráficos SHAP son reales (XGBoost + TreeExplainer) cuando el backend no es mock.
      </div>

      {/* Gene-specific result header */}
      {geneResult && (
        <div className={`p-3 rounded mb-4 flex items-center justify-between ${
          geneResult.status === 'POS' ? 'bg-red-50 border border-red-200' :
          geneResult.status === 'NEG' ? 'bg-green-50 border border-green-200' :
          'bg-yellow-50 border border-yellow-200'
        }`}>
          <div>
            <span className="text-sm font-semibold">{selGene} Mutation Prediction:</span>
            <span className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${
              geneResult.status === 'POS' ? 'bg-red-200 text-red-800' :
              geneResult.status === 'NEG' ? 'bg-green-200 text-green-800' :
              'bg-yellow-200 text-yellow-800'
            }`}>
              {geneResult.status}
            </span>
          </div>
          <span className="text-sm font-mono">Score: {geneResult.score?.toFixed(4)}</span>
        </div>
      )}

      {/* Morphologic profile */}
      {mp && (
        <div className="mb-6">
          <h3 className="font-semibold mb-2 text-sm">Morphologic Profile (features for mutation models)</h3>
          <div className="grid grid-cols-4 gap-2 text-sm">
            <div className="bg-gray-50 rounded p-2 text-center">
              <div className="text-xs text-gray-500">Total Tiles</div>
              <div className="font-bold text-lg">{mp.n_tiles_total}</div>
            </div>
            {Object.entries(PATTERN_COLORS).map(([pattern, color]) => {
              const pctKey = `pct_${pattern}` as string;
              const val = (mp as any)[pctKey] ?? 0;
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

          {/* Horizontal bar chart of pattern distribution */}
          <div className="mt-3">
            {patterns.map((p: any) => (
              <div key={p.pattern} className="flex items-center gap-2 mb-1">
                <span className="text-xs w-24 text-right capitalize">{p.pattern}</span>
                <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                  <div
                    className="h-full rounded transition-all duration-500"
                    style={{
                      width: `${Math.min(p.percentage || 0, 100)}%`,
                      backgroundColor: PATTERN_COLORS[p.pattern] || '#ccc',
                      opacity: 0.8,
                    }}
                  />
                </div>
                <span className="text-xs font-mono w-12">{(p.percentage || 0).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SHAP global + force visualization */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* SHAP Bar Chart */}
        <div>
          <h3 className="font-semibold mb-2 text-sm">SHAP Bar — {selGene} (Global Feature Importance)</h3>
          <div className="border rounded bg-gray-50 h-64 flex items-center justify-center overflow-hidden">
            {barArt ? (
              <ArtifactImage
                uri={barArt.uri}
                alt={`SHAP bar chart for ${selGene}`}
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <div className="text-center text-gray-400 text-sm">
                <svg className="w-10 h-10 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p>No bar chart for {selGene}</p>
                <p className="text-xs mt-1">Process an image to generate SHAP artifacts</p>
              </div>
            )}
          </div>
        </div>

        {/* SHAP Beeswarm */}
        <div>
          <h3 className="font-semibold mb-2 text-sm">SHAP Beeswarm — {selGene} (Feature Impact Distribution)</h3>
          <div className="border rounded bg-gray-50 h-64 flex items-center justify-center overflow-hidden">
            {beeswarmArt ? (
              <ArtifactImage
                uri={beeswarmArt.uri}
                alt={`SHAP beeswarm for ${selGene}`}
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <div className="text-center text-gray-400 text-sm">
                <svg className="w-10 h-10 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
                <p>No beeswarm plot for {selGene}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SHAP Force Plot (full width) */}
      <div className="mb-6">
        <h3 className="font-semibold mb-2 text-sm">SHAP Force Plot — {selGene} (Case-Level Explanation)</h3>
        <div className="border rounded bg-gray-50 h-48 flex items-center justify-center overflow-hidden">
          {forceArt ? (
            <ArtifactImage
              uri={forceArt.uri}
              alt={`SHAP force plot for ${selGene}`}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <div className="text-center text-gray-400 text-sm">
              <p>No force plot for {selGene}</p>
              <p className="text-xs mt-1">Force plots show individual feature contributions for this case</p>
            </div>
          )}
        </div>
      </div>

      {/* All XAI Artifacts table */}
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
                <th className="border px-2 py-1.5">Hash</th>
                <th className="border px-2 py-1.5">Preview</th>
              </tr>
            </thead>
            <tbody>
              {allArts.map((a: any, i: number) => (
                <tr key={a.artifact_id || i} className="hover:bg-gray-50">
                  <td className="border px-2 py-1.5">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      a.artifact_type?.includes('bar') ? 'bg-blue-100 text-blue-700' :
                      a.artifact_type?.includes('beeswarm') ? 'bg-purple-100 text-purple-700' :
                      a.artifact_type?.includes('force') ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {a.artifact_type}
                    </span>
                  </td>
                  <td className="border px-2 py-1.5 font-mono">{a.gene || '-'}</td>
                  <td className="border px-2 py-1.5 text-blue-600 truncate max-w-xs" title={a.uri}>
                    {a.uri}
                  </td>
                  <td className="border px-2 py-1.5 font-mono text-gray-400">{a.hash?.slice(0, 12)}...</td>
                  <td className="border px-2 py-1.5">
                    <a
                      href={getArtifactUrl(a.uri)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      Open
                    </a>
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
