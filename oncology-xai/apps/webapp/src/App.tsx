import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from './auth/AuthProvider';
import ImagePanel from './panels/ImagePanel';
import ViewerPanel from './panels/ViewerPanel';
import GraphPanel from './panels/GraphPanel';
import ShapPanel from './panels/ShapPanel';
import AdminPanel from './panels/AdminPanel';
import { getPatients, getCases, getImages, getLatestResults } from './api';

type Tab = 'images' | 'viewer' | 'graph' | 'shap' | 'admin';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Espanol' },
  { code: 'de', label: 'Deutsch' },
  { code: 'fr', label: 'Francais' },
  { code: 'pt', label: 'Portugues' },
];

interface CaseEntry {
  caseId: string;
  patientId: string;
  patientName: string;
  imageCount?: number;
}

export default function App() {
  const { user, isAdmin, isClinician, isAuditor, logout, preferredLanguage, setPreferredLanguage } = useAuth();
  const [tab, setTab] = useState<Tab>('images');
  const [caseId, setCaseId] = useState<string | null>(null);
  const [imageId, setImageId] = useState<string | null>(null);
  const [resultBundleId, setResultBundleId] = useState<string | null>(null);
  const [allCases, setAllCases] = useState<CaseEntry[]>([]);
  const [caseDropdownOpen, setCaseDropdownOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

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

  const tabs: { key: Tab; label: string; roles?: string[] }[] = [
    { key: 'images', label: 'Images' },
    { key: 'viewer', label: 'Viewer' },
    { key: 'graph', label: 'Graph' },
    { key: 'shap', label: 'Explainability' },
    ...(isAdmin ? [{ key: 'admin' as Tab, label: 'Admin' }] : []),
  ];

  return (
    <div className="min-h-screen">
      <header className="bg-blue-900 text-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">LCHAI v2.0</h1>
          <p className="text-xs text-blue-200">Lung Cancer Histologic Analysis with AI — ABMIL + Choquet MIL</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-xs text-blue-300">
            Research tool — NOT for clinical diagnosis
          </div>
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 bg-blue-800 hover:bg-blue-700 rounded-full px-3 py-1.5 text-xs"
            >
              <span className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold text-xs">
                {(user?.name || 'U')[0].toUpperCase()}
              </span>
              <span>{user?.name || 'User'}</span>
              <span className="text-blue-300 text-[10px]">({user?.roles?.filter(r => ['admin','clinician','auditor'].includes(r)).join(', ')})</span>
            </button>
            {userMenuOpen && (
              <div className="absolute right-0 top-full mt-1 bg-white border rounded-lg shadow-xl z-50 min-w-[220px] text-gray-800">
                <div className="px-4 py-3 border-b">
                  <p className="font-semibold text-sm">{user?.name}</p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                  <div className="flex gap-1 mt-1">
                    {user?.roles?.filter(r => ['admin','clinician','auditor'].includes(r)).map(r => (
                      <span key={r} className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        r === 'admin' ? 'bg-red-100 text-red-700' :
                        r === 'clinician' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>{r}</span>
                    ))}
                  </div>
                </div>
                <div className="px-4 py-2 border-b">
                  <label className="text-xs text-gray-500 block mb-1">Explanation language</label>
                  <select
                    value={preferredLanguage}
                    onChange={(e) => { setPreferredLanguage(e.target.value); setUserMenuOpen(false); }}
                    className="w-full text-xs border rounded px-2 py-1"
                  >
                    {LANGUAGES.map(l => (
                      <option key={l.code} value={l.code}>{l.label}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => { setUserMenuOpen(false); logout(); }}
                  className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 rounded-b-lg"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
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
        {tab === 'admin' && isAdmin && <AdminPanel />}
        {tab === 'admin' && !isAdmin && (
          <div className="bg-red-50 border border-red-200 rounded p-6 text-center">
            <p className="text-red-700 font-semibold">Access Denied</p>
            <p className="text-red-500 text-sm mt-1">Admin panel requires administrator privileges.</p>
          </div>
        )}
      </main>

      <footer className="bg-gray-100 border-t px-6 py-3 text-xs text-gray-500 text-center">
        DISCLAIMER: LCHAI v2.0 is a research tool (THESIS_INTERNAL evidence).
        Mutation predictions use ABMIL + Fuzzy Choquet MIL (Artifacts 2 &amp; 3).
        Inconclusive genes (AUROC &lt; 0.70) require molecular testing. NOT for clinical diagnosis.
      </footer>
    </div>
  );
}
