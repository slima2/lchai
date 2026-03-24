import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getOntologies, createProposal, getAuditEvents,
  runDeepSearch, runBatchDeepSearch, getDeepSearchJobs, getDiscoveredRelations,
  getKGSnapshots, createKGSnapshot, getKGChangelog, api,
} from '../api';

type Tab = 'parameters' | 'pipeline' | 'versions' | 'ontologies' | 'audit';

const METHODS: Record<string, string> = {
  TP53: 'B2 (embeddings)', EGFR: 'B2 (embeddings)', RBM10: 'FC (Fuzzy Choquet)',
  STK11: 'P (proposed)', KRAS: 'FC (Fuzzy Choquet)', KEAP1: 'P (proposed)',
};
const FOLDS: Record<string, number> = { TP53: 2, EGFR: 4, KRAS: 3, STK11: 3, KEAP1: 1, RBM10: 4 };
const GENE_ORDER = ['TP53', 'EGFR', 'RBM10', 'STK11', 'KRAS', 'KEAP1'];

const METHOD_OPTIONS = [
  { value: 'baseline2', label: 'B2 (embeddings)' },
  { value: 'proposed', label: 'P (proposed concat)' },
  { value: 'choquet', label: 'FC (Fuzzy Choquet)' },
];

function ParametersPanel() {
  const [aurocs, setAurocs] = useState<Record<string, number>>({
    TP53: 0.718, EGFR: 0.701, RBM10: 0.661, STK11: 0.695, KRAS: 0.609, KEAP1: 0.610,
  });
  const [methods, setMethods] = useState<Record<string, string>>({
    TP53: 'baseline2', EGFR: 'baseline2', STK11: 'proposed', KEAP1: 'proposed', KRAS: 'choquet', RBM10: 'choquet',
  });
  const [threshold, setThreshold] = useState(0.70);
  const [mutThreshold, setMutThreshold] = useState(0.50);
  const [topK, setTopK] = useState(200);
  const [maxTiles, setMaxTiles] = useState(20000);
  const [permRepeats, setPermRepeats] = useState(10);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  React.useEffect(() => {
    api.get('/parameters').then(r => {
      if (r.data?.auroc_values) setAurocs(r.data.auroc_values);
      if (r.data?.auroc_threshold != null) setThreshold(r.data.auroc_threshold);
      if (r.data?.best_method) setMethods(r.data.best_method);
      if (r.data?.mutation_threshold != null) setMutThreshold(r.data.mutation_threshold);
      if (r.data?.top_k_tiles != null) setTopK(r.data.top_k_tiles);
      if (r.data?.max_tiles != null) setMaxTiles(r.data.max_tiles);
      if (r.data?.permutation_repeats != null) setPermRepeats(r.data.permutation_repeats);
    }).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.put('/parameters', {
        auroc_values: aurocs, auroc_threshold: threshold, best_method: methods,
        mutation_threshold: mutThreshold, top_k_tiles: topK, max_tiles: maxTiles,
        permutation_repeats: permRepeats,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch { /* */ }
    setSaving(false);
  };

  return (
    <div>
      <h3 className="font-semibold mb-3 text-lg">System Parameters</h3>
      <p className="text-xs text-gray-500 mb-4">
        Edit values below and click "Save Parameters". Changes take effect on the next image analysis.
        Default AUROC values = mean across 5-fold CV on 687 LUAD slides (thesis benchmark).
      </p>

      <div className="border-2 border-blue-200 rounded-lg p-4 mb-4">
      <div className="grid grid-cols-2 gap-6">
        <div>
          <h4 className="font-semibold text-sm mb-2">Gene AUROC (mean, 5-fold CV) — editable</h4>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border px-3 py-2 text-left">Gene</th>
                <th className="border px-3 py-2 text-center">AUROC</th>
                <th className="border px-3 py-2 text-center">Method</th>
                <th className="border px-3 py-2 text-center">Label</th>
              </tr>
            </thead>
            <tbody>
              {GENE_ORDER.map(gene => (
                <tr key={gene} className="hover:bg-gray-50">
                  <td className="border px-3 py-2 font-bold">{gene}</td>
                  <td className="border px-1 py-1 text-center">
                    <input
                      type="number" step="0.001" min="0" max="1"
                      className="w-20 text-center font-mono border rounded px-1 py-1 text-sm"
                      value={aurocs[gene] ?? 0}
                      onChange={e => setAurocs({ ...aurocs, [gene]: parseFloat(e.target.value) || 0 })}
                    />
                  </td>
                  <td className="border px-1 py-1 text-center">
                    <select
                      className="text-xs border rounded px-1 py-1"
                      value={methods[gene] || 'proposed'}
                      onChange={e => setMethods({ ...methods, [gene]: e.target.value })}
                    >
                      {METHOD_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </td>
                  <td className="border px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                      (aurocs[gene] ?? 0) >= threshold ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {(aurocs[gene] ?? 0) >= threshold ? 'Conclusive' : 'Inconclusive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-gray-400 mt-2">
            Source: thesis benchmark (Lima et al., 2026). Mean across 5-fold CV on 687 LUAD-only slides.
          </p>
        </div>

        <div>
          <h4 className="font-semibold text-sm mb-2">Classification Threshold — editable</h4>
          <div className="bg-gray-50 rounded p-4 mb-4">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-sm font-medium">AUROC Threshold:</span>
              <input
                type="number" step="0.001" min="0.5" max="1"
                className="w-20 text-center text-xl font-bold text-blue-700 border rounded px-2 py-1"
                value={threshold}
                onChange={e => setThreshold(parseFloat(e.target.value) || 0.70)}
              />
            </div>
            <p className="text-xs text-gray-600">
              Genes with AUROC ≥ threshold → <strong className="text-green-700">Conclusive</strong>.
              Below → <strong className="text-yellow-700">Inconclusive</strong>.
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Default 0.70 = "acceptable discrimination" (Hosmer & Lemeshow, 2000).
            </p>
          </div>

          <h4 className="font-semibold text-sm mt-4 mb-2">Inference Parameters — editable</h4>
          <div className="bg-gray-50 rounded p-4 space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Mutation threshold (POS/NEG)</span>
              <input type="number" step="0.05" min="0.1" max="0.9" className="w-20 text-center font-mono border rounded px-1 py-1 text-sm"
                value={mutThreshold} onChange={e => setMutThreshold(parseFloat(e.target.value) || 0.5)} />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Top-K attention tiles</span>
              <input type="number" step="50" min="50" max="1000" className="w-20 text-center font-mono border rounded px-1 py-1 text-sm"
                value={topK} onChange={e => setTopK(parseInt(e.target.value) || 200)} />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Max tiles per WSI</span>
              <input type="number" step="1000" min="1000" max="100000" className="w-24 text-center font-mono border rounded px-1 py-1 text-sm"
                value={maxTiles} onChange={e => setMaxTiles(parseInt(e.target.value) || 20000)} />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Permutation repeats</span>
              <input type="number" step="5" min="5" max="100" className="w-20 text-center font-mono border rounded px-1 py-1 text-sm"
                value={permRepeats} onChange={e => setPermRepeats(parseInt(e.target.value) || 10)} />
            </div>
          </div>
        </div>
      </div>

      {/* Save button inside bordered section */}
      <div className="mt-4 flex items-center gap-4">
        <button onClick={save} disabled={saving}
          className="bg-blue-600 text-white px-8 py-2.5 rounded text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50">
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save All Parameters'}
        </button>
        {saved && <span className="text-green-600 text-sm font-medium">Parameters saved. Changes apply to the next image analysis.</span>}
      </div>

      </div>{/* end bordered editable section */}

      {/* Non-editable system info */}
      <div className="mt-4 p-4 bg-gray-50 rounded">
        <h4 className="font-semibold text-sm mb-2 text-gray-500">Fixed System Configuration (requires rebuild to change)</h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="flex justify-between"><span className="text-gray-500">Tile size</span><span className="font-mono">224 px</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Backbone</span><span className="font-mono">CTransPath Swin Tiny</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Classifier</span><span className="font-mono">FuzzyArcLoss V2</span></div>
        </div>
      </div>
    </div>
  );
}

export default function AdminPanel() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('parameters');
  const [targets, setTargets] = useState('NCIt,MONDO');
  const [searchText, setSearchText] = useState('');
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);

  // Queries
  const ontologies = useQuery({
    queryKey: ['ontologies'],
    queryFn: () => getOntologies().then(r => r.data),
    enabled: tab === 'ontologies',
  });

  const audit = useQuery({
    queryKey: ['audit'],
    queryFn: () => getAuditEvents({ limit: 50 }).then(r => r.data),
    enabled: tab === 'audit',
  });

  const jobs = useQuery({
    queryKey: ['deep-search-jobs'],
    queryFn: () => getDeepSearchJobs().then(r => r.data),
    enabled: tab === 'pipeline',
  });

  const snapshots = useQuery({
    queryKey: ['kg-snapshots'],
    queryFn: () => getKGSnapshots().then(r => r.data),
    enabled: tab === 'versions',
  });

  const changelog = useQuery({
    queryKey: ['kg-changelog', selectedSnapshot],
    queryFn: () => selectedSnapshot ? getKGChangelog(selectedSnapshot).then(r => r.data) : [],
    enabled: !!selectedSnapshot && tab === 'versions',
  });

  // Mutations
  const deepSearch = useMutation({
    mutationFn: (text: string) => runDeepSearch({ text, source_type: 'text' }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deep-search-jobs'] }),
  });

  const batchSearch = useMutation({
    mutationFn: () => runBatchDeepSearch().then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deep-search-jobs'] }),
  });

  const discovered = useQuery({
    queryKey: ['discovered-relations'],
    queryFn: () => getDiscoveredRelations().then(r => r.data),
    enabled: tab === 'pipeline',
  });

  const publishSnapshot = useMutation({
    mutationFn: (relations: any[]) => createKGSnapshot({
      relations,
      description: `DeepSearch pipeline — ${relations.length} relaciones validadas`,
      sources: ['DeepSearch LLM Pipeline'],
    }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kg-snapshots'] }),
  });

  const newProposal = useMutation({
    mutationFn: () => createProposal({ targets: targets.split(',').map(t => t.trim()), mode: 'offline' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ontologies'] }),
  });

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: 'parameters', label: 'Parameters', icon: '⚙' },
    { key: 'pipeline', label: 'DeepSearch Pipeline', icon: '🔬' },
    { key: 'versions', label: 'KG Versions', icon: '📦' },
    { key: 'ontologies', label: 'Ontology Management', icon: '🧬' },
    { key: 'audit', label: 'Audit Log', icon: '📋' },
  ];

  return (
    <div>
      <div className="flex gap-1 mb-4 flex-wrap">
        {tabs.map(t => (
          <button key={t.key}
            className={`px-4 py-1.5 rounded text-sm transition ${tab === t.key ? 'bg-blue-600 text-white' : 'bg-gray-200 hover:bg-gray-300'}`}
            onClick={() => setTab(t.key)}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ──── Parameters ──── */}
      {tab === 'parameters' && <ParametersPanel />}

      {/* ──── DeepSearch Pipeline ──── */}
      {tab === 'pipeline' && (
        <div>
          <h3 className="font-semibold mb-3 text-lg">DeepSearch Updater Pipeline</h3>
          <p className="text-xs text-gray-500 mb-3">
            Ingest text/papers → LLM extraction → Entity linking → Dedup → SHACL validation → KG snapshot
          </p>

          <div className="mb-4">
            <textarea
              className="w-full border rounded p-3 text-sm h-32"
              placeholder="Paste clinical text, paper abstract, or KB export here...&#10;Example: 'Lepidic-predominant adenocarcinoma is strongly associated with EGFR mutations and responds to osimertinib.'"
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
            />
            <div className="flex gap-2 mt-2">
              <button
                className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50"
                onClick={() => deepSearch.mutate(searchText)}
                disabled={!searchText.trim() || deepSearch.isPending}
              >
                {deepSearch.isPending ? 'Running pipeline...' : 'Run DeepSearch Pipeline'}
              </button>
            </div>
          </div>

          {/* Latest result */}
          {deepSearch.data && (
            <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded">
              <h4 className="font-semibold text-sm mb-2">Pipeline Result</h4>
              <div className="flex gap-4 text-xs mb-2">
                <span>Raw: {deepSearch.data.linked_entities?.raw_count}</span>
                <span>Linked: {deepSearch.data.linked_entities?.linked_count}</span>
                <span>Deduped: {deepSearch.data.linked_entities?.deduped_count}</span>
                <span className="text-green-700 font-bold">Valid: {deepSearch.data.linked_entities?.valid_count}</span>
                <span className="text-red-600">Invalid: {deepSearch.data.linked_entities?.invalid_count}</span>
              </div>
              {deepSearch.data.validation_result?.valid?.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs font-semibold mb-1">Validated Relations:</p>
                  <div className="max-h-40 overflow-y-auto border rounded text-xs divide-y">
                    {deepSearch.data.validation_result.valid.map((r: any, i: number) => (
                      <div key={i} className="px-2 py-1 flex gap-2">
                        <span className="font-mono text-green-700">{r.subject}</span>
                        <span className="text-blue-600 font-bold">—{r.predicate}→</span>
                        <span className="font-mono text-green-700">{r.object}</span>
                        <span className="text-gray-400 ml-auto text-[10px] truncate max-w-[200px]">{r.evidence_quote}</span>
                      </div>
                    ))}
                  </div>
                  <button
                    className="mt-2 bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700"
                    onClick={() => publishSnapshot.mutate(deepSearch.data.validation_result.valid)}
                    disabled={publishSnapshot.isPending}
                  >
                    {publishSnapshot.isPending ? 'Publishing...' : 'Publish as KG Snapshot'}
                  </button>
                  {publishSnapshot.data && (
                    <span className="ml-2 text-xs text-green-700">
                      Published: {publishSnapshot.data.version_tag}
                    </span>
                  )}
                </div>
              )}
              {deepSearch.data.validation_result?.invalid?.length > 0 && (
                <details className="text-xs mt-2">
                  <summary className="cursor-pointer text-red-600">
                    {deepSearch.data.validation_result.invalid.length} invalid relation(s)
                  </summary>
                  <div className="mt-1 max-h-32 overflow-y-auto">
                    {deepSearch.data.validation_result.invalid.map((r: any, i: number) => (
                      <div key={i} className="px-2 py-1 text-red-700">
                        {r.subject} → {r.predicate} → {r.object} ({r.validation_reason})
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          )}

          {/* Job history */}
          {/* Batch Literature Search */}
          <div className="mb-4 p-4 bg-indigo-50 border border-indigo-200 rounded">
            <h4 className="font-semibold text-sm mb-1">Batch Literature DeepSearch</h4>
            <p className="text-xs text-gray-500 mb-2">
              Busca autom&aacute;ticamente en PubMed, Semantic Scholar y arXiv nuevas relaciones entre patrones histol&oacute;gicos, mutaciones gen&eacute;ticas y tratamientos. Ejecuta ~12 queries cient&iacute;ficas curadas. Puede tardar varios minutos.
            </p>
            <button
              className="bg-indigo-600 text-white px-4 py-2 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
              onClick={() => batchSearch.mutate()}
              disabled={batchSearch.isPending}
            >
              {batchSearch.isPending ? 'Launching...' : 'Run Batch Literature Search'}
            </button>
            {batchSearch.data && (
              <span className="ml-3 text-xs text-indigo-700">
                Job {batchSearch.data.job_id?.slice(0, 8)} started ({batchSearch.data.queries_count} queries)
              </span>
            )}
          </div>

          {/* Discovered relations */}
          {(discovered.data || []).length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-sm mb-2">
                Discovered Relations ({discovered.data.length})
              </h4>
              <p className="text-xs text-gray-500 mb-1">
                Relaciones extra&iacute;das autom&aacute;ticamente de literatura cient&iacute;fica. Se incorporan al grafo al hacer "Rebuild Graph".
              </p>
              <div className="border rounded max-h-48 overflow-y-auto divide-y text-xs">
                {discovered.data.map((r: any) => (
                  <div key={r.id} className="px-2 py-1.5 flex gap-2 items-center hover:bg-gray-50">
                    <span className="font-mono text-purple-700">{r.subject}</span>
                    <span className="text-blue-600 font-bold">—{r.predicate}→</span>
                    <span className="font-mono text-purple-700">{r.object}</span>
                    <span className="text-gray-400 ml-auto text-[10px]">{r.paper_source}</span>
                    {r.paper_url && (
                      <a href={r.paper_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline text-[10px]">
                        paper
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <h4 className="font-semibold text-sm mb-2">Pipeline History</h4>
          <div className="border rounded max-h-60 overflow-y-auto">
            <table className="w-full text-xs">
              <thead><tr className="bg-gray-100">
                <th className="px-2 py-1">Job ID</th><th className="px-2 py-1">Status</th>
                <th className="px-2 py-1">Source</th><th className="px-2 py-1">Valid</th>
                <th className="px-2 py-1">Created</th>
              </tr></thead>
              <tbody>
                {(jobs.data || []).map((j: any) => (
                  <tr key={j.job_id} className="hover:bg-gray-50">
                    <td className="px-2 py-1 font-mono">{j.job_id?.slice(0, 8)}</td>
                    <td className="px-2 py-1">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        j.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                        j.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'}`}>
                        {j.status}
                      </span>
                    </td>
                    <td className="px-2 py-1">{j.source_type}</td>
                    <td className="px-2 py-1">{j.linked_entities?.valid_count ?? '-'}</td>
                    <td className="px-2 py-1 text-gray-500">{j.created_at?.slice(0, 19)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!jobs.data?.length && <p className="p-3 text-gray-400 text-sm">No pipeline jobs yet</p>}
          </div>
        </div>
      )}

      {/* ──── KG Versions ──── */}
      {tab === 'versions' && (
        <div>
          <h3 className="font-semibold mb-3 text-lg">Knowledge Graph Versions</h3>
          <p className="text-xs text-gray-500 mb-3">
            Each snapshot is a versioned release of the KG (slima-luad-kg_YYYYMMDD.jsonld) with a full changelog.
          </p>

          <div className="border rounded max-h-60 overflow-y-auto mb-4">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-100">
                <th className="px-3 py-2 text-left">Version</th>
                <th className="px-3 py-2">Nodes</th><th className="px-3 py-2">Edges</th>
                <th className="px-3 py-2">Sources</th><th className="px-3 py-2">Created</th>
                <th className="px-3 py-2">Actions</th>
              </tr></thead>
              <tbody>
                {(snapshots.data || []).map((s: any) => (
                  <tr key={s.snapshot_id} className={`hover:bg-gray-50 ${selectedSnapshot === s.snapshot_id ? 'bg-blue-50' : ''}`}>
                    <td className="px-3 py-2 font-mono font-bold">{s.version_tag}</td>
                    <td className="px-3 py-2 text-center">{s.nodes_count}</td>
                    <td className="px-3 py-2 text-center">{s.edges_count}</td>
                    <td className="px-3 py-2 text-xs">{(s.sources || []).join(', ')}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{s.created_at?.slice(0, 19)}</td>
                    <td className="px-3 py-2">
                      <button className="text-xs text-blue-600 hover:underline"
                        onClick={() => setSelectedSnapshot(s.snapshot_id)}>
                        Changelog
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!snapshots.data?.length && <p className="p-3 text-gray-400 text-sm">No KG snapshots yet</p>}
          </div>

          {/* Changelog */}
          {selectedSnapshot && (
            <div>
              <h4 className="font-semibold text-sm mb-2">
                Changelog for {snapshots.data?.find((s: any) => s.snapshot_id === selectedSnapshot)?.version_tag}
              </h4>
              <div className="border rounded max-h-60 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead><tr className="bg-gray-100">
                    <th className="px-2 py-1">Action</th><th className="px-2 py-1">Type</th>
                    <th className="px-2 py-1">Entity</th><th className="px-2 py-1">Provenance</th>
                  </tr></thead>
                  <tbody>
                    {(changelog.data || []).map((e: any) => (
                      <tr key={e.id} className="hover:bg-gray-50">
                        <td className="px-2 py-1">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                            e.action === 'ADDED' ? 'bg-green-100 text-green-700' :
                            e.action === 'REMOVED' ? 'bg-red-100 text-red-700' :
                            'bg-yellow-100 text-yellow-700'}`}>
                            {e.action}
                          </span>
                        </td>
                        <td className="px-2 py-1">{e.entity_type}</td>
                        <td className="px-2 py-1 font-mono">{e.entity_id}</td>
                        <td className="px-2 py-1 text-gray-500 max-w-[200px] truncate">{e.provenance}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!changelog.data?.length && <p className="p-3 text-gray-400 text-sm">No changelog entries</p>}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ──── Ontology Management (existing) ──── */}
      {tab === 'ontologies' && (
        <div>
          <h3 className="font-semibold mb-3 text-lg">Ontology Versions</h3>
          <div className="border rounded max-h-60 overflow-y-auto mb-4">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-100">
                <th className="px-3 py-2">Name</th><th className="px-3 py-2">Version</th>
                <th className="px-3 py-2">Active</th><th className="px-3 py-2">Imported</th>
              </tr></thead>
              <tbody>
                {ontologies.data?.map((v: any) => (
                  <tr key={v.ontology_version_id}>
                    <td className="px-3 py-2">{v.name}</td>
                    <td className="px-3 py-2">{v.version_tag}</td>
                    <td className="px-3 py-2 text-center">{v.is_active ? 'YES' : 'no'}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{v.imported_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!ontologies.data?.length && <p className="p-3 text-gray-400 text-sm">No ontology versions</p>}
          </div>

          <h3 className="font-semibold mb-3">Create Update Proposal</h3>
          <div className="flex gap-2">
            <input
              className="border rounded px-3 py-1.5 text-sm flex-1"
              placeholder="Targets (comma-separated: NCIt,MONDO,SO)"
              value={targets} onChange={e => setTargets(e.target.value)}
            />
            <button className="bg-green-600 text-white px-4 py-1.5 rounded text-sm"
              onClick={() => newProposal.mutate()}>
              Create Proposal
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Proposals: DRAFT → VALIDATING → VALIDATED → PUBLISHED (or ROLLED_BACK)
          </p>
        </div>
      )}

      {/* ──── Audit Log (existing) ──── */}
      {tab === 'audit' && (
        <div>
          <h3 className="font-semibold mb-3 text-lg">Audit Events (latest 50)</h3>
          <div className="border rounded max-h-96 overflow-y-auto">
            <table className="w-full text-xs">
              <thead><tr className="bg-gray-100">
                <th className="px-2 py-1">Event ID</th><th className="px-2 py-1">Type</th>
                <th className="px-2 py-1">Action</th><th className="px-2 py-1">Case</th>
                <th className="px-2 py-1">Timestamp</th>
              </tr></thead>
              <tbody>
                {audit.data?.map((e: any) => (
                  <tr key={e.event_id} className="hover:bg-gray-50">
                    <td className="px-2 py-1 font-mono">{e.event_id?.slice(0, 12)}</td>
                    <td className="px-2 py-1">{e.event_type}</td>
                    <td className="px-2 py-1">{e.action}</td>
                    <td className="px-2 py-1 font-mono">{e.case_id?.slice(0, 8) || '-'}</td>
                    <td className="px-2 py-1 text-gray-500">{e.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!audit.data?.length && <p className="p-3 text-gray-400 text-sm">No audit events</p>}
          </div>
        </div>
      )}
    </div>
  );
}
