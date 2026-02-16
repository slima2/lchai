import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPatients, createPatient, getCases, createCase } from '../api';

interface Props {
  onSelectCase: (caseId: string) => void;
}

export default function CaseSelector({ onSelectCase }: Props) {
  const qc = useQueryClient();
  const [extId, setExtId] = useState('');
  const [selPatient, setSelPatient] = useState<string | null>(null);

  const patients = useQuery({ queryKey: ['patients'], queryFn: () => getPatients().then(r => r.data) });
  const cases = useQuery({
    queryKey: ['cases', selPatient],
    queryFn: () => getCases(selPatient!).then(r => r.data),
    enabled: !!selPatient,
  });

  const addPatient = useMutation({
    mutationFn: () => createPatient({ external_id: extId || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['patients'] }); setExtId(''); },
  });

  const addCase = useMutation({
    mutationFn: () => createCase({ patient_id: selPatient }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cases'] }),
  });

  return (
    <div className="grid grid-cols-2 gap-6">
      {/* Patients */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Patients</h2>
        <div className="flex gap-2 mb-3">
          <input
            className="border rounded px-3 py-1.5 text-sm flex-1"
            placeholder="External ID (optional)"
            value={extId}
            onChange={e => setExtId(e.target.value)}
          />
          <button
            className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700"
            onClick={() => addPatient.mutate()}
          >
            + Patient
          </button>
        </div>
        <div className="border rounded divide-y max-h-96 overflow-y-auto">
          {patients.data?.map((p: any) => (
            <div
              key={p.patient_id}
              className={`px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 ${
                selPatient === p.patient_id ? 'bg-blue-100' : ''
              }`}
              onClick={() => setSelPatient(p.patient_id)}
            >
              <span className="font-mono text-xs">{p.patient_id.slice(0, 8)}</span>
              {p.external_id && <span className="ml-2 text-gray-600">{p.external_id}</span>}
            </div>
          ))}
          {patients.data?.length === 0 && (
            <p className="px-3 py-4 text-gray-400 text-sm">No patients yet</p>
          )}
        </div>
      </section>

      {/* Cases */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Cases</h2>
        {selPatient ? (
          <>
            <button
              className="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700 mb-3"
              onClick={() => addCase.mutate()}
            >
              + New Case
            </button>
            <div className="border rounded divide-y max-h-96 overflow-y-auto">
              {cases.data?.map((c: any) => (
                <div
                  key={c.case_id}
                  className="px-3 py-2 text-sm cursor-pointer hover:bg-green-50 flex justify-between"
                  onClick={() => onSelectCase(c.case_id)}
                >
                  <span className="font-mono text-xs">{c.case_id.slice(0, 8)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    c.status === 'CREATED' ? 'bg-gray-200' :
                    c.status === 'REVIEW_REQUIRED' ? 'bg-yellow-200' :
                    'bg-green-200'
                  }`}>
                    {c.status}
                  </span>
                </div>
              ))}
              {cases.data?.length === 0 && (
                <p className="px-3 py-4 text-gray-400 text-sm">No cases yet</p>
              )}
            </div>
          </>
        ) : (
          <p className="text-gray-400 text-sm">Select a patient first</p>
        )}
      </section>
    </div>
  );
}
