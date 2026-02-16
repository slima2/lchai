import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

// Patients
export const createPatient = (data: any) => api.post('/patients', data);
export const getPatients = (query?: string) => api.get('/patients', { params: { query } });
export const getPatient = (id: string) => api.get(`/patients/${id}`);

// Cases
export const createCase = (data: any) => api.post('/cases', data);
export const getCases = (patientId?: string) => api.get('/cases', { params: { patientId } });
export const getCase = (id: string) => api.get(`/cases/${id}`);
export const updateCase = (id: string, data: any) => api.patch(`/cases/${id}`, data);

// Images
export const uploadImage = (caseId: string, file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api.post(`/cases/${caseId}/images:upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const getImages = (caseId: string) => api.get(`/cases/${caseId}/images`);
export const getViewerUrl = (imageId: string) => api.get(`/images/${imageId}/viewer-url`);

// Inference
export const processImage = (imageId: string, caseId: string) =>
  api.post(`/images/${imageId}:process`, { case_id: caseId });
export const getJob = (jobId: string) => api.get(`/jobs/${jobId}`);
export const getLatestResults = (imageId: string) => api.get(`/images/${imageId}/results/latest`);
export const getResultBundle = (id: string) => api.get(`/results/${id}`);
export const getArtifacts = (rbId: string) => api.get(`/results/${rbId}/artifacts`);

// EHR
export const ingestEHR = (caseId: string, content: string) =>
  api.post(`/cases/${caseId}/ehr:ingest`, { content, source: 'paste' });
export const getEHRVersions = (caseId: string) => api.get(`/cases/${caseId}/ehr/versions`);
export const extractAndMap = (ehrId: string) => api.post(`/ehr/${ehrId}:extract-and-map`);
export const getEntities = (ehrId: string) => api.get(`/ehr/${ehrId}/entities`);
export const getMappings = (ehrId: string) => api.get(`/ehr/${ehrId}/mappings`);

// Graph
export const getCaseGraph = (caseId: string) => api.get(`/cases/${caseId}/graph`);
export const rebuildGraph = (caseId: string, fromOntology = true) =>
  api.post(`/cases/${caseId}/graph:rebuild`, null, { params: { fromOntology } });
export const explainGraph = (caseId: string) =>
  api.post<{ case_id: string; explanation: string }>(`/cases/${caseId}/graph/explain`);

// Ontology Admin
export const getOntologies = () => api.get('/admin/ontologies');
export const createProposal = (data: any) => api.post('/admin/ontologies:update-proposal', data);

// DeepSearch Pipeline
export const runDeepSearch = (data: { text: string; source_type?: string }) =>
  api.post('/admin/deep-search', data);
export const runBatchDeepSearch = (data?: { queries?: string[]; sources?: string[] }) =>
  api.post('/admin/deep-search/batch', data || {});
export const getDeepSearchJobs = () => api.get('/admin/deep-search/jobs');
export const getDeepSearchJob = (jobId: string) => api.get(`/admin/deep-search/jobs/${jobId}`);
export const getDiscoveredRelations = () => api.get('/admin/deep-search/discovered');

// KG Versioning
export const getKGSnapshots = () => api.get('/admin/kg/snapshots');
export const createKGSnapshot = (data: any) => api.post('/admin/kg/snapshots', data);
export const getKGChangelog = (snapshotId: string) =>
  api.get(`/admin/kg/snapshots/${snapshotId}/changelog`);

// Artifacts — presigned URL proxy
export const getArtifactUrl = (uri: string) => {
  // Convert s3://bucket/key to MinIO presigned URL via gateway
  const key = uri.replace(/^s3:\/\/[^/]+\//, '');
  return `${API_URL}/api/v1/artifacts/presigned?key=${encodeURIComponent(key)}`;
};

// Audit
export const getAuditEvents = (params?: any) => api.get('/audit/events', { params });
