const defaultApiBase = import.meta.env.DEV
  ? 'http://127.0.0.1:8000'
  : window.location.origin;

export const API_BASE = (import.meta.env.VITE_API_URL || defaultApiBase).replace(/\/$/, '');

export const API_ROUTES = {
  convert: '/api/convert',
  convertUpload: '/api/convert/upload',
  settings: '/api/settings',
  jobs: '/api/jobs',
  jobById: (jobId: string) => `/api/jobs/${jobId}`,
  jobProgress: (jobId: string) => `/api/jobs/${jobId}/progress`,
  cancelJob: (jobId: string) => `/api/jobs/${jobId}/cancel`,
  retryJob: (jobId: string) => `/api/jobs/${jobId}/retry`,
  openPath: '/api/system/open',
  selectFolder: '/api/system/select-folder',
  metrics: '/api/metrics',
  health: '/api/health',
} as const;

export const buildApiUrl = (path: string): string => `${API_BASE}${path}`;
