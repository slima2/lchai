import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ingestEHR, getEHRVersions, extractAndMap, getEntities, getMappings } from '../api';

interface Props {
  caseId: string;
}

export default function EHRPanel({ caseId }: Props) {
  const qc = useQueryClient();
  const [text, setText] = useState('');
  const [selEHR, setSelEHR] = useState<string | null>(null);

  const versions = useQuery({
    queryKey: ['ehr-versions', caseId],
    queryFn: () => getEHRVersions(caseId).then(r => r.data),
  });

  const entities = useQuery({
    queryKey: ['entities', selEHR],
    queryFn: () => getEntities(selEHR!).then(r => r.data),
    enabled: !!selEHR,
  });

  const mappings = useQuery({
    queryKey: ['mappings', selEHR],
    queryFn: () => getMappings(selEHR!).then(r => r.data),
    enabled: !!selEHR,
  });

  const ingest = useMutation({
    mutationFn: () => ingestEHR(caseId, text),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['ehr-versions'] });
      setSelEHR(r.data.ehr_id);
      setText('');
    },
  });

  const extract = useMutation({
    mutationFn: () => extractAndMap(selEHR!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities', selEHR] });
      qc.invalidateQueries({ queryKey: ['mappings', selEHR] });
    },
  });

  return (
    <div className="grid grid-cols-2 gap-6">
      {/* Left: EHR input */}
      <div>
        <h3 className="font-semibold mb-2">EHR Text Input</h3>
        <textarea
          className="border rounded w-full h-48 p-3 text-sm"
          placeholder="Paste clinical text here... (e.g., 'Patient with lung adenocarcinoma, EGFR positive, stage IIIA')"
          value={text}
          onChange={e => setText(e.target.value)}
        />
        <div className="flex gap-2 mt-2">
          <button className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm" onClick={() => ingest.mutate()}>
            Ingest EHR
          </button>
          {selEHR && (
            <button className="bg-purple-600 text-white px-4 py-1.5 rounded text-sm" onClick={() => extract.mutate()}>
              Extract & Map
            </button>
          )}
        </div>

        <h4 className="font-semibold mt-6 mb-2">Versions</h4>
        <div className="border rounded divide-y max-h-40 overflow-y-auto">
          {versions.data?.map((v: any) => (
            <div
              key={v.ehr_id}
              className={`px-3 py-2 text-xs cursor-pointer ${selEHR === v.ehr_id ? 'bg-blue-100' : 'hover:bg-gray-50'}`}
              onClick={() => setSelEHR(v.ehr_id)}
            >
              v{v.version} — {v.ehr_id.slice(0, 8)}
            </div>
          ))}
        </div>
      </div>

      {/* Right: Entities + Mappings */}
      <div>
        <h3 className="font-semibold mb-2">Extracted Entities</h3>
        <div className="border rounded max-h-40 overflow-y-auto mb-4">
          <table className="w-full text-xs">
            <thead><tr className="bg-gray-100"><th className="px-2 py-1">Text</th><th className="px-2 py-1">Type</th><th className="px-2 py-1">Confidence</th></tr></thead>
            <tbody>
              {entities.data?.map((e: any) => (
                <tr key={e.entity_id} className="hover:bg-gray-50">
                  <td className="px-2 py-1 font-medium">{e.text}</td>
                  <td className="px-2 py-1"><span className="bg-gray-200 px-1 rounded">{e.type}</span></td>
                  <td className="px-2 py-1 text-right">{(e.confidence * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!entities.data?.length && <p className="p-3 text-gray-400 text-xs">No entities extracted yet</p>}
        </div>

        <h3 className="font-semibold mb-2">Ontology Mappings</h3>
        <div className="border rounded max-h-40 overflow-y-auto">
          <table className="w-full text-xs">
            <thead><tr className="bg-gray-100"><th className="px-2 py-1">Label</th><th className="px-2 py-1">Ontology</th><th className="px-2 py-1">IRI</th></tr></thead>
            <tbody>
              {mappings.data?.map((m: any) => (
                <tr key={m.mapping_id} className="hover:bg-gray-50">
                  <td className="px-2 py-1 font-medium">{m.label}</td>
                  <td className="px-2 py-1">{m.ontology}</td>
                  <td className="px-2 py-1 text-blue-600 truncate max-w-xs">{m.iri}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!mappings.data?.length && <p className="p-3 text-gray-400 text-xs">No mappings yet</p>}
        </div>
      </div>
    </div>
  );
}
