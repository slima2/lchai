import React, { useState, useEffect } from 'react';
import ImagePanel from './panels/ImagePanel';
import ViewerPanel from './panels/ViewerPanel';
import GraphPanel from './panels/GraphPanel';
import ShapPanel from './panels/ShapPanel';
import AdminPanel from './panels/AdminPanel';
import { getPatients, getCases, getImages, getLatestResults } from './api';

type Tab = 'images' | 'viewer' | 'graph' | 'shap' | 'admin';

const DEFAULT_PATIENT_EXTERNAL_ID = 'TCGA-69-7979';

export default function App() {
  const [tab, setTab] = useState<Tab>('images');
  const [caseId, setCaseId] = useState<string | null>(null);
  const [imageId, setImageId] = useState<string | null>(null);
  const [resultBundleId, setResultBundleId] = useState<string | null>(null);
  const [autoLoaded, setAutoLoaded] = useState(false);

  useEffect(() => {
    if (autoLoaded) return;
    setAutoLoaded(true);

    (async () => {
      try {
        const patientsRes = await getPatients();
        const patients = patientsRes.data || [];
        const defaultPatient = patients.find(
          (p: any) => p.external_id === DEFAULT_PATIENT_EXTERNAL_ID
        );
        if (!defaultPatient) return;

        const casesRes = await getCases(defaultPatient.patient_id);
        const cases = casesRes.data || [];
        if (cases.length === 0) return;
        const defaultCase = cases[0];
        setCaseId(defaultCase.case_id);

        const imagesRes = await getImages(defaultCase.case_id);
        const images = imagesRes.data || [];
        if (images.length > 0) {
          setImageId(images[0].image_id);
          try {
            const resultsRes = await getLatestResults(images[0].image_id);
            if (resultsRes.data?.result_bundle_id) {
              setResultBundleId(resultsRes.data.result_bundle_id);
            }
          } catch { /* no results yet */ }
        }
      } catch (err) {
        console.warn('Auto-load failed:', err);
      }
    })();
  }, [autoLoaded]);

  const tabs: { key: Tab; label: string }[] = [
    { key: 'images', label: 'Images' },
    { key: 'viewer', label: 'Viewer' },
    { key: 'graph', label: 'Graph' },
    { key: 'shap', label: 'Explainability' },
    { key: 'admin', label: 'Admin' },
  ];

  return (
    <div className="min-h-screen">
      <header className="bg-blue-900 text-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">LCHAI v2.0</h1>
          <p className="text-xs text-blue-200">Lung Cancer Histologic Analysis with AI — ABMIL + Choquet MIL</p>
        </div>
        <div className="text-xs text-blue-300">
          Research tool — NOT for clinical diagnosis
        </div>
      </header>

      <nav className="bg-white border-b flex gap-0">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-blue-600 text-blue-600 bg-blue-50'
                : 'border-transparent text-gray-600 hover:text-blue-600'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {caseId && (
        <div className="bg-yellow-50 border-b border-yellow-200 px-6 py-2 text-xs text-yellow-800 flex gap-4">
          <span>Case: <strong>{caseId}</strong></span>
          {imageId && <span>Image: <strong>{imageId}</strong></span>}
          {resultBundleId && <span>Results: <strong>{resultBundleId}</strong></span>}
        </div>
      )}

      <main className="p-6">
        {tab === 'images' && caseId && (
          <ImagePanel
            caseId={caseId}
            imageId={imageId}
            onImageSelected={setImageId}
            onResultsReady={setResultBundleId}
          />
        )}
        {tab === 'images' && !caseId && (
          <p className="text-gray-500">Loading default case... If this persists, check that the system has data.</p>
        )}
        {tab === 'viewer' && caseId && (
          <ViewerPanel caseId={caseId} imageId={imageId} resultBundleId={resultBundleId} />
        )}
        {tab === 'viewer' && !caseId && (
          <p className="text-gray-500">Upload and process an image first.</p>
        )}
        {tab === 'graph' && caseId && <GraphPanel caseId={caseId} />}
        {tab === 'graph' && !caseId && (
          <p className="text-gray-500">Upload and process an image first.</p>
        )}
        {tab === 'shap' && resultBundleId && <ShapPanel resultBundleId={resultBundleId} />}
        {tab === 'shap' && !resultBundleId && (
          <p className="text-gray-500">Process an image first to view SHAP results.</p>
        )}
        {tab === 'admin' && <AdminPanel />}
      </main>

      <footer className="bg-gray-100 border-t px-6 py-3 text-xs text-gray-500 text-center">
        DISCLAIMER: LCHAI v2.0 is a research tool (THESIS_INTERNAL evidence).
        Mutation predictions use ABMIL + Fuzzy Choquet MIL (Artifacts 2 &amp; 3).
        Inconclusive genes (AUROC &lt; 0.70) require molecular testing. NOT for clinical diagnosis.
      </footer>
    </div>
  );
}
