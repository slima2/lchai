import axios from 'axios';
import keycloak from './auth/keycloak';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
  },
});

api.interceptors.request.use(async (config) => {
  if (keycloak.authenticated && keycloak.token) {
    if (keycloak.isTokenExpired(10)) {
      try { await keycloak.updateToken(30); } catch { keycloak.logout(); }
    }
    config.headers.Authorization = `Bearer ${keycloak.token}`;
  }
  return config;
});

// Patients
export const createPatient = (data: any) => api.post('/patients', data);
export const getPatients = (query?: string) => api.get('/patients', { params: { query } });
export const getPatient = (id: string) => api.get(`/patients/${id}`);
export const deletePatient = (id: string) => api.delete(`/patients/${id}`);

// Cases
export const createCase = (data: any) => api.post('/cases', data);
export const getCases = (patientId?: string) => api.get('/cases', { params: { patientId } });
export const getCase = (id: string) => api.get(`/cases/${id}`);
export const updateCase = (id: string, data: any) => api.patch(`/cases/${id}`, data);
export const deleteCase = (id: string) => api.delete(`/cases/${id}`);

// Images
// Upload strategy:
//   - Files ≤ MULTIPART_THRESHOLD: single POST through the API proxy (simple, validated server-side).
//   - Files >  MULTIPART_THRESHOLD: presigned multipart upload directly to S3 (bypasses gateway timeouts and
//     server-side memory load). The backend supports this via :request-upload + :complete-multipart.
const SINGLE_UPLOAD_THRESHOLD = 200 * 1024 * 1024;  // 200 MB; above this we go presigned

export const uploadImage = async (caseId: string, file: File, onProgress?: (pct: number) => void) => {
  if (file.size <= SINGLE_UPLOAD_THRESHOLD) {
    return uploadImageSingle(caseId, file, onProgress);
  }
  return uploadImageMultipart(caseId, file, onProgress);
};

async function uploadImageSingle(caseId: string, file: File, onProgress?: (pct: number) => void) {
  const formData = new FormData();
  formData.append('file', file);

  const { data: image } = await api.post(`/cases/${caseId}/images:upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 0,
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return { data: image };
}

async function uploadImageMultipart(caseId: string, file: File, onProgress?: (pct: number) => void) {
  const { data: req } = await api.post(`/cases/${caseId}/images:request-upload`, {
    filename: file.name,
    size_bytes: file.size,
  });

  if (!req.multipart) {
    // Backend chose single presigned PUT (file under its server-side threshold).
    await axios.put(req.presigned_url, file, {
      headers: { 'Content-Type': req.content_type || 'application/octet-stream' },
      timeout: 0,
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    });
    const { data: image } = await api.post(`/cases/${caseId}/images:confirm-upload`, {
      image_id: req.image_id,
    });
    return { data: image };
  }

  // Multipart path
  const partSize: number = req.part_size;
  const partUrls: { part_number: number; presigned_url: string }[] = req.part_urls;
  const totalParts = partUrls.length;
  const completedBytesByPart = new Array<number>(totalParts).fill(0);

  const parts: { ETag: string; PartNumber: number }[] = [];
  for (let i = 0; i < totalParts; i++) {
    const pn = partUrls[i].part_number;
    const start = (pn - 1) * partSize;
    const end = Math.min(file.size, start + partSize);
    const blob = file.slice(start, end);
    const resp = await axios.put(partUrls[i].presigned_url, blob, {
      headers: { 'Content-Type': req.content_type || 'application/octet-stream' },
      timeout: 0,
      onUploadProgress: (e) => {
        if (onProgress) {
          completedBytesByPart[i] = e.loaded;
          const total = completedBytesByPart.reduce((a, b) => a + b, 0);
          onProgress(Math.min(99, Math.round((total / file.size) * 100)));
        }
      },
    });
    const etag = (resp.headers['etag'] || resp.headers['ETag'] || '').replace(/"/g, '');
    if (!etag) throw new Error(`Part ${pn} did not return an ETag header`);
    parts.push({ ETag: etag, PartNumber: pn });
  }

  const { data: image } = await api.post(`/cases/${caseId}/images:complete-multipart`, {
    image_id: req.image_id,
    upload_id: req.upload_id,
    parts,
  });
  if (onProgress) onProgress(100);
  return { data: image };
}
export const getImages = (caseId: string) => api.get(`/cases/${caseId}/images`);
export const getViewerUrl = (imageId: string) => api.get(`/images/${imageId}/viewer-url`);

// Inference (v2)
export const processImage = (imageId: string, caseId: string, useChoquet = true) =>
  api.post(`/images/${imageId}:process`, { case_id: caseId, use_choquet: useChoquet });
export const getJob = (jobId: string) => api.get(`/jobs/${jobId}`);
export const getLatestResults = (imageId: string) => api.get(`/images/${imageId}/results/latest`);
export const getResultBundle = (id: string) => api.get(`/results/${id}`);
export const getArtifacts = (rbId: string) => api.get(`/results/${rbId}/artifacts`);
export const getCheckpointStatus = () => api.get('/checkpoints/status');

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
export const explainGraph = (caseId: string, language?: string) =>
  api.post<{ case_id: string; explanation: string }>(`/cases/${caseId}/graph/explain`, { language });
export const explainResults = (caseId: string, language?: string) =>
  api.post<{ case_id: string; explanation: string }>(`/cases/${caseId}/graph/explain`, { language });

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

// KG gene-pattern-treatment associations (dynamic, includes DeepSearch)
export const getGeneAssociations = () => api.get('/graph/gene-associations');

// Artifacts — streamed from MinIO via image-service proxy
export const getArtifactUrl = (uri: string) => {
  const key = uri.replace(/^s3:\/\/[^/]+\//, '');
  return `${API_URL}/api/v1/artifacts/presigned?key=${encodeURIComponent(key)}`;
};

// Active Learning — Pattern Corrections (separate microservice)
export const submitPatternCorrections = (
  resultBundleId: string, caseId: string, imageId: string, corrections: any[]
) =>
  api.post('/active-learning/corrections', {
    case_id: caseId, image_id: imageId,
    result_bundle_id: resultBundleId, corrections,
  });
export const getActiveLearningJob = (jobId: string) =>
  api.get(`/active-learning/jobs/${jobId}`);
export const getPatternCorrections = (resultBundleId: string) =>
  api.get(`/active-learning/corrections/${resultBundleId}`);

// Audit
export const getAuditEvents = (params?: any) => api.get('/audit/events', { params });
