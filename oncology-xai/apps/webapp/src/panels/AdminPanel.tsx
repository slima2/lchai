import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getOntologies, createProposal, getAuditEvents,
  runDeepSearch, runBatchDeepSearch, getDeepSearchJobs, getDiscoveredRelations,
  getKGSnapshots, createKGSnapshot, getKGChangelog,
} from '../api';

type Tab = 'parameters' | 'pipeline' | 'versions' | 'ontologies' | 'audit';

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
      {tab === 'parameters' && (
        <div>
          <h3 className="font-semibold mb-3 text-lg">System Parameters</h3>
          <p className="text-xs text-gray-500 mb-4">
            These parameters control mutation prediction confidence labels. AUROC values come from the thesis benchmark
            (687 LUAD slides, 5-fold stratified CV, best fold per gene). They can be updated if the model is retrained
            on a larger population.
          </p>

          <div className="grid grid-cols-2 gap-6">
            {/* AUROC Table */}
            <div>
              <h4 className="font-semibold text-sm mb-2">Gene AUROC (Best Fold)</h4>
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border px-3 py-2 text-left">Gene</th>
                    <th className="border px-3 py-2 text-right">AUROC</th>
                    <th className="border px-3 py-2 text-center">Best Method</th>
                    <th className="border px-3 py-2 text-center">Fold</th>
                    <th className="border px-3 py-2 text-center">Label</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { gene: 'TP53', auroc: 0.8024, method: 'B2 (embeddings)', fold: 2 },
                    { gene: 'EGFR', auroc: 0.7504, method: 'B2 (embeddings)', fold: 4 },
                    { gene: 'RBM10', auroc: 0.7371, method: 'FC (Fuzzy Choquet)', fold: 4 },
                    { gene: 'STK11', auroc: 0.6962, method: 'P (proposed)', fold: 3 },
                    { gene: 'KRAS', auroc: 0.6800, method: 'FC (Fuzzy Choquet)', fold: 3 },
                    { gene: 'KEAP1', auroc: 0.6218, method: 'P (proposed)', fold: 1 },
                  ].map(row => (
                    <tr key={row.gene} className="hover:bg-gray-50">
                      <td className="border px-3 py-2 font-bold">{row.gene}</td>
                      <td className="border px-3 py-2 text-right font-mono">{row.auroc.toFixed(4)}</td>
                      <td className="border px-3 py-2 text-center text-xs">{row.method}</td>
                      <td className="border px-3 py-2 text-center">{row.fold}</td>
                      <td className="border px-3 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          row.auroc >= 0.70 ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {row.auroc >= 0.70 ? 'Conclusive' : 'Inconclusive'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-gray-400 mt-2">
                Source: thesis benchmark (Lima et al., 2026). 687 LUAD-only slides, 5-fold stratified CV.
              </p>
            </div>

            {/* Threshold + Config */}
            <div>
              <h4 className="font-semibold text-sm mb-2">Classification Threshold</h4>
              <div className="bg-gray-50 rounded p-4 mb-4">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-sm font-medium">AUROC Threshold:</span>
                  <span className="text-2xl font-bold text-blue-700">0.70</span>
                </div>
                <p className="text-xs text-gray-600">
                  Genes with AUROC ≥ 0.70 are labeled <strong className="text-green-700">Conclusive</strong> (reliable prediction).
                  Genes below are labeled <strong className="text-yellow-700">Inconclusive</strong> (molecular testing recommended).
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  0.70 is a widely accepted threshold for "acceptable discrimination" in clinical prediction models
                  (Hosmer & Lemeshow, 2000). To change this threshold, update <code>AUROC_CONCLUSIVE_THRESHOLD</code> in <code>.env</code>
                  and restart the inference service.
                </p>
              </div>

              <h4 className="font-semibold text-sm mb-2">Other Parameters</h4>
              <div className="bg-gray-50 rounded p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Mutation threshold (POS/NEG)</span>
                  <span className="font-mono font-bold">0.50</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Top-K attention tiles</span>
                  <span className="font-mono font-bold">200</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Max tiles per WSI</span>
                  <span className="font-mono font-bold">10,000</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Tile size</span>
                  <span className="font-mono font-bold">224 px</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Backbone</span>
                  <span className="font-mono font-bold">CTransPath Swin Tiny</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Classifier</span>
                  <span className="font-mono font-bold">FuzzyArcLoss V2</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Permutation repeats</span>
                  <span className="font-mono font-bold">10</span>
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                To modify these parameters, edit <code>.env</code> and restart the system with <code>docker compose up -d</code>.
              </p>
            </div>
          </div>
        </div>
      )}

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
