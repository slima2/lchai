import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import ImagePanel from './panels/ImagePanel';
import ViewerPanel from './panels/ViewerPanel';
import GraphPanel from './panels/GraphPanel';
import ShapPanel from './panels/ShapPanel';
import AdminPanel from './panels/AdminPanel';
import { getPatients, getCases, getImages, getLatestResults } from './api';

type Tab = 'images' | 'viewer' | 'graph' | 'shap' | 'admin';

interface CaseEntry {
  caseId: string;
  patientId: string;
  patientName: string;
  imageCount?: number;
}

export default function App() {
  const [tab, setTab] = useState<Tab>('images');
  const [caseId, setCaseId] = useState<string | null>(null);
  const [imageId, setImageId] = useState<string | null>(null);
  const [resultBundleId, setResultBundleId] = useState<string | null>(null);
  const [allCases, setAllCases] = useState<CaseEntry[]>([]);
  const [caseDropdownOpen, setCaseDropdownOpen] = useState(false);

  useEffect(() => {
    loadAllCases();
  }, []);

  async function loadAllCases() {
    try {
      const patientsRes = await getPatients();
      const patients = patientsRes.data || [];
      const entries: CaseEntry[] = [];

      for (const p of patients) {
        const casesRes = await getCases(p.patient_id);
        const cases = casesRes.data || [];
        for (const c of cases) {
          entries.push({
            caseId: c.case_id,
            patientId: p.patient_id,
            patientName: p.external_id || p.patient_id.slice(0, 8),
          });
        }
      }

      setAllCases(entries);

      if (!caseId && entries.length > 0) {
        const first = entries[0];
        setCaseId(first.caseId);
        const imagesRes = await getImages(first.caseId);
        const images = imagesRes.data || [];
        if (images.length > 0) {
          setImageId(images[0].image_id);
          try {
            const resultsRes = await getLatestResults(images[0].image_id);
            if (resultsRes.data?.result_bundle_id) {
              setResultBundleId(resultsRes.data.result_bundle_id);
            }
          } catch { /* no results */ }
        }
      }
    } catch (err) {
      console.warn('Failed to load cases:', err);
    }
  }

  async function selectCase(entry: CaseEntry) {
    setCaseId(entry.caseId);
    setImageId(null);
    setResultBundleId(null);
    setCaseDropdownOpen(false);

    try {
      const imagesRes = await getImages(entry.caseId);
      const images = imagesRes.data || [];
      if (images.length > 0) {
        setImageId(images[0].image_id);
        try {
          const resultsRes = await getLatestResults(images[0].image_id);
          if (resultsRes.data?.result_bundle_id) {
            setResultBundleId(resultsRes.data.result_bundle_id);
          }
        } catch { /* no results */ }
      }
    } catch { /* no images */ }
  }

  const currentCase = allCases.find(c => c.caseId === caseId);

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

      {/* Case selector bar */}
      <div className="bg-yellow-50 border-b border-yellow-200 px-6 py-2 text-xs text-yellow-800 flex items-center gap-4">
        <div className="relative">
          <button
            onClick={() => setCaseDropdownOpen(!caseDropdownOpen)}
            className="bg-white border border-yellow-300 rounded px-3 py-1 text-xs font-medium hover:bg-yellow-100 flex items-center gap-1"
          >
            <span>Slide: <strong>{currentCase?.patientName || 'Select...'}</strong></span>
            <span className="text-gray-400 ml-1">▼</span>
          </button>
          {caseDropdownOpen && (
            <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded shadow-lg z-50 min-w-[250px] max-h-60 overflow-y-auto">
              {allCases.map(entry => (
                <button
                  key={entry.caseId}
                  onClick={() => selectCase(entry)}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-blue-50 ${entry.caseId === caseId ? 'bg-blue-100 font-bold' : ''}`}
                >
                  <div>{entry.patientName}</div>
                  <div className="text-gray-400 text-[10px]">{entry.caseId}</div>
                </button>
              ))}
              {allCases.length === 0 && (
                <div className="px-3 py-2 text-gray-400 text-xs">No cases found. Upload an image.</div>
              )}
            </div>
          )}
        </div>
        {imageId && <span>Image: <strong>{imageId.slice(0, 12)}...</strong></span>}
        {resultBundleId && <span>Results: <strong>{resultBundleId.slice(0, 12)}...</strong></span>}
        <span className="text-gray-400 ml-auto">{allCases.length} slide(s) loaded</span>
      </div>

      <main className="p-6">
        {tab === 'images' && caseId && (
          <ImagePanel
            caseId={caseId}
            imageId={imageId}
            onImageSelected={setImageId}
            onResultsReady={setResultBundleId}
            onCaseChanged={(id) => {
              setCaseId(id);
              setImageId(null);
              setResultBundleId(null);
              loadAllCases();
            }}
          />
        )}
        {tab === 'images' && !caseId && (
          <p className="text-gray-500">Upload an image to get started.</p>
        )}
        {tab === 'viewer' && caseId && (
          <ViewerPanel caseId={caseId} imageId={imageId} resultBundleId={resultBundleId} />
        )}
        {tab === 'viewer' && !caseId && (
          <p className="text-gray-500">Upload and process an image first.</p>
        )}
        {tab === 'graph' && caseId && <GraphPanel caseId={caseId} resultBundleId={resultBundleId} />}
        {tab === 'graph' && !caseId && (
          <p className="text-gray-500">Upload and process an image first.</p>
        )}
        {tab === 'shap' && resultBundleId && <ShapPanel resultBundleId={resultBundleId} />}
        {tab === 'shap' && !resultBundleId && (
          <p className="text-gray-500">Process an image first to view explainability results.</p>
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
