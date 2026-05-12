import { API_ROUTES, buildApiUrl } from './routes';

interface ProgressData {
  current?: number;
  total?: number;
  filename?: string;
  is_error?: boolean;
  error_msg?: string;
  output_path?: string;
  successes?: number;
  errors?: number;
  status?: string;
}

export interface SettingsData {
  theme: string;
  last_output_dir: string;
}

export interface HealthData {
  status: string;
  backend_ready?: boolean;
  running_jobs: string[];
  running_jobs_count: number;
}

export interface JobSummary {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'canceled' | 'interrupted';
  total: number;
  processed: number;
  successes: number;
  errors: number;
  extension: string;
  output_dir: string;
  files: string[];
  file_items?: Array<{
    filename: string;
    source_path?: string | null;
    output_path?: string | null;
    status: 'pending' | 'completed' | 'failed' | 'canceled' | 'interrupted';
    error?: string | null;
  }>;
  started_at?: number;
  finished_at?: number | null;
  last_file?: string | null;
  last_error?: string | null;
  elapsed_ms?: number | null;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let backendMessage: string | null = null;
    try {
      const payload = await response.json();
      const message = payload?.error?.message;
      if (message) {
        backendMessage = String(message);
      }
    } catch {
      // fallback to generic error below
    }
    throw new Error(backendMessage ?? `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function convertPdf(paths: string[], outputDir: string, extension: string) {
  return requestJson<{ message: string; job_id: string }>(buildApiUrl(API_ROUTES.convert), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths, output_dir: outputDir, extension }),
  });
}

export async function convertPdfUpload(files: File[], outputDir: string, extension: string) {
  const form = new FormData();
  form.append('output_dir', outputDir);
  form.append('extension', extension);
  files.forEach((file) => form.append('files', file, file.name));

  return requestJson<{ message: string; job_id: string }>(buildApiUrl(API_ROUTES.convertUpload), {
    method: 'POST',
    body: form,
  });
}

export async function getSettings(): Promise<SettingsData> {
  return requestJson<SettingsData>(buildApiUrl(API_ROUTES.settings));
}

export async function updateSettings(data: SettingsData): Promise<SettingsData> {
  return requestJson<SettingsData>(buildApiUrl(API_ROUTES.settings), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function getHealth(): Promise<HealthData> {
  return requestJson<HealthData>(buildApiUrl(API_ROUTES.health));
}

export async function getJobs(limit = 20): Promise<JobSummary[]> {
  const data = await requestJson<{ jobs: JobSummary[] }>(`${buildApiUrl(API_ROUTES.jobs)}?limit=${limit}`);
  return data.jobs || [];
}

export async function getJob(jobId: string): Promise<JobSummary | null> {
  try {
    const data = await requestJson<{ job: JobSummary }>(buildApiUrl(API_ROUTES.jobById(jobId)));
    return data.job;
  } catch {
    return null;
  }
}

export async function cancelJob(jobId: string): Promise<{ message: string; job_id: string }> {
  return requestJson<{ message: string; job_id: string }>(buildApiUrl(API_ROUTES.cancelJob(jobId)), {
    method: 'POST',
  });
}

export async function retryJob(jobId: string): Promise<{ message: string; job_id: string }> {
  return requestJson<{ message: string; job_id: string }>(buildApiUrl(API_ROUTES.retryJob(jobId)), {
    method: 'POST',
  });
}

export async function openSystemPath(path: string): Promise<{ message: string; path: string }> {
  return requestJson<{ message: string; path: string }>(buildApiUrl(API_ROUTES.openPath), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
}

export async function selectOutputDirectory(initialPath = ''): Promise<{ message: string; path: string }> {
  return requestJson<{ message: string; path: string }>(buildApiUrl(API_ROUTES.selectFolder), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initial_path: initialPath }),
  });
}

export function subscribeToProgress(
  jobId: string,
  onMessage: (data: ProgressData) => void,
  onComplete: () => void
) {
  const source = new EventSource(buildApiUrl(API_ROUTES.jobProgress(jobId)));
  source.addEventListener('progress', (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {
      // ignore malformed SSE payloads
    }
  });
  source.addEventListener('complete', (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {
      // ignore malformed SSE payloads
    }
    onComplete();
    source.close();
  });
  source.onerror = () => {
    onComplete();
    source.close();
  };
  return () => source.close();
}
