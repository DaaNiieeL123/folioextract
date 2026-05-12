import { useCallback, useEffect, useMemo, useState } from 'react';
import { cancelJob, getJob, getJobs, openSystemPath, retryJob } from '../services/api/client';
import type { JobSummary } from '../services/api/client';
import { AlertTriangle, Ban, CheckCircle2, ChevronRight, Clock3, FolderOpen, Loader2, RefreshCcw } from 'lucide-react';
import cs from 'classnames';

type ToastType = 'success' | 'error' | 'info';

interface Props {
  refreshMs?: number;
  onShowToast?: (payload: { message: string; type: ToastType }) => void;
  onTrackJob?: (jobId: string) => Promise<void> | void;
}

function statusLabel(status: JobSummary['status']): string {
  if (status === 'queued') return 'Queued';
  if (status === 'running') return 'Running';
  if (status === 'failed') return 'Failed';
  if (status === 'canceled') return 'Canceled';
  if (status === 'interrupted') return 'Interrupted';
  return 'Completed';
}

function statusClass(status: JobSummary['status']): string {
  if (status === 'queued') return 'text-amber-300 border-amber-500/40 bg-amber-500/10';
  if (status === 'running') return 'text-blue-300 border-blue-500/40 bg-blue-500/10';
  if (status === 'failed') return 'text-red-300 border-red-500/40 bg-red-500/10';
  if (status === 'canceled') return 'text-orange-300 border-orange-500/40 bg-orange-500/10';
  if (status === 'interrupted') return 'text-fuchsia-300 border-fuchsia-500/40 bg-fuchsia-500/10';
  return 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10';
}

function statusIcon(status: JobSummary['status']) {
  if (status === 'queued') return <Loader2 size={12} className="animate-spin" />;
  if (status === 'running') return <Clock3 size={12} />;
  if (status === 'failed') return <AlertTriangle size={12} />;
  if (status === 'canceled') return <Ban size={12} />;
  if (status === 'interrupted') return <AlertTriangle size={12} />;
  return <CheckCircle2 size={12} />;
}

function percentage(job: JobSummary): number {
  if (!job.total) return 0;
  return Math.round((job.processed / job.total) * 100);
}

function fileStatusClass(status: NonNullable<JobSummary['file_items']>[number]['status']): string {
  if (status === 'pending') return 'text-blue-300 border-blue-500/40 bg-blue-500/10';
  if (status === 'failed') return 'text-red-300 border-red-500/40 bg-red-500/10';
  if (status === 'canceled') return 'text-orange-300 border-orange-500/40 bg-orange-500/10';
  if (status === 'interrupted') return 'text-fuchsia-300 border-fuchsia-500/40 bg-fuchsia-500/10';
  return 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10';
}

function canRetry(job: JobSummary | null): boolean {
  if (!job) return false;
  if (job.status === 'queued' || job.status === 'running') return false;
  const items = job.file_items || [];
  return items.some((item) => item.status !== 'completed');
}

function canCancel(job: JobSummary | null): boolean {
  return !!job && (job.status === 'queued' || job.status === 'running');
}

export default function JobHistoryPanel({ refreshMs = 4000, onShowToast, onTrackJob }: Props) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selected, setSelected] = useState<JobSummary | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const loadJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getJobs(20);
      setJobs(data);
      if (selected) {
        const updatedSelected = data.find((item) => item.job_id === selected.job_id);
        if (updatedSelected) {
          const detail = await getJob(updatedSelected.job_id);
          if (detail) {
            setSelected(detail);
          }
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [selected]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      if (!mounted) return;
      await loadJobs();
    };

    void load();
    const id = window.setInterval(() => {
      void load();
    }, refreshMs);
    return () => {
      mounted = false;
      window.clearInterval(id);
    };
  }, [loadJobs, refreshMs]);

  const runningJobs = useMemo(() => jobs.filter((j) => j.status === 'running').length, [jobs]);
  const queuedJobs = useMemo(() => jobs.filter((j) => j.status === 'queued').length, [jobs]);

  const openDetails = useCallback(async (jobId: string) => {
    const detail = await getJob(jobId);
    if (detail) {
      setSelected(detail);
    }
  }, []);

  const showToast = useCallback((message: string, type: ToastType) => {
    onShowToast?.({ message, type });
  }, [onShowToast]);

  const handleOpenPath = useCallback(async (path: string, successMessage: string) => {
    try {
      await openSystemPath(path);
      showToast(successMessage, 'success');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'No se pudo abrir la ruta solicitada.', 'error');
    }
  }, [showToast]);

  const handleCancel = useCallback(async () => {
    if (!selected || !canCancel(selected) || isBusy) return;
    setIsBusy(true);
    try {
      await cancelJob(selected.job_id);
      showToast('Cancelación solicitada.', 'info');
      await openDetails(selected.job_id);
      await loadJobs();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'No se pudo cancelar el job.', 'error');
    } finally {
      setIsBusy(false);
    }
  }, [isBusy, loadJobs, openDetails, selected, showToast]);

  const handleRetry = useCallback(async () => {
    if (!selected || !canRetry(selected) || isBusy) return;
    setIsBusy(true);
    try {
      const data = await retryJob(selected.job_id);
      showToast('Reintento iniciado.', 'success');
      await loadJobs();
      if (onTrackJob) {
        await onTrackJob(data.job_id);
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'No se pudo reintentar el job.', 'error');
    } finally {
      setIsBusy(false);
    }
  }, [isBusy, loadJobs, onTrackJob, selected, showToast]);

  return (
    <div className="mt-5 border-t border-[#181c29] pt-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-bold tracking-[0.2em] text-[#595b66] uppercase">Jobs</span>
        <span className="text-[10px] text-[#5b6987] tabular-nums">{jobs.length} total · {queuedJobs} queued · {runningJobs} running</span>
      </div>

      <div className="space-y-2 max-h-[220px] overflow-y-auto history-scroll pr-1">
        {isLoading && jobs.length === 0 ? (
          <div className="text-[11px] text-[#5b6987] flex items-center gap-2"><Loader2 size={12} className="animate-spin" /> Cargando jobs...</div>
        ) : jobs.length === 0 ? (
          <div className="text-[11px] text-[#464c63]">Sin jobs persistidos aún.</div>
        ) : (
          jobs.map((job) => (
            <button
              key={job.job_id}
              type="button"
              onClick={() => void openDetails(job.job_id)}
              className="w-full text-left rounded-xl border border-[#1c2230] bg-[#0f1219] px-3 py-2.5 hover:border-[#2a3756] transition-colors"
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="text-[10px] font-mono text-[#7d86a1] truncate">{job.job_id.slice(0, 10)}...</span>
                <span className={cs('px-2 py-0.5 rounded-md border text-[9px] font-bold uppercase tracking-wide inline-flex items-center gap-1', statusClass(job.status))}>
                  {statusIcon(job.status)} {statusLabel(job.status)}
                </span>
              </div>

              <div className="text-[11px] text-[#c8d0e0]">{job.processed}/{job.total} archivos · {percentage(job)}%</div>
              <div className="text-[10px] text-[#5b6987] truncate">OK {job.successes} · Error {job.errors} · {job.extension}</div>

              <div className="mt-2 h-1 rounded-full bg-[#1b2b4d] overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${percentage(job)}%` }} />
              </div>
            </button>
          ))
        )}
      </div>

      {selected && (
        <div className="mt-4 rounded-xl border border-[#1c2230] bg-[#0f1219] p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-gray-200">Detalle Job</span>
            <button type="button" onClick={() => setSelected(null)} className="text-[10px] text-[#5b6987] hover:text-gray-300">Cerrar</button>
          </div>

          <div className="space-y-1.5 text-[10.5px] text-[#aeb7cc]">
            <p><span className="text-[#5b6987]">ID:</span> {selected.job_id}</p>
            <p><span className="text-[#5b6987]">Estado:</span> {selected.status}</p>
            <p><span className="text-[#5b6987]">Progreso:</span> {selected.processed}/{selected.total} ({percentage(selected)}%)</p>
            <p><span className="text-[#5b6987]">Salida:</span> {selected.output_dir}</p>
            <p><span className="text-[#5b6987]">Formato:</span> {selected.extension}</p>
            <p><span className="text-[#5b6987]">Archivos:</span> {selected.files.length}</p>
            {selected.last_file ? <p><span className="text-[#5b6987]">Último:</span> {selected.last_file}</p> : null}
            {selected.last_error ? <p className="text-red-300"><span className="text-red-400">Error:</span> {selected.last_error}</p> : null}
            {selected.elapsed_ms ? <p><span className="text-[#5b6987]">Tiempo:</span> {selected.elapsed_ms} ms</p> : null}
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={isBusy || !canCancel(selected)}
              onClick={() => void handleCancel()}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-orange-500/30 bg-orange-500/10 text-[10px] uppercase tracking-wide text-orange-200 disabled:opacity-40"
            >
              <Ban size={12} /> Cancelar
            </button>
            <button
              type="button"
              disabled={isBusy || !canRetry(selected)}
              onClick={() => void handleRetry()}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-primary/30 bg-primary/10 text-[10px] uppercase tracking-wide text-primary disabled:opacity-40"
            >
              <RefreshCcw size={12} /> Reintentar
            </button>
            <button
              type="button"
              onClick={() => void handleOpenPath(selected.output_dir, 'Carpeta de salida abierta.')}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-[10px] uppercase tracking-wide text-emerald-200"
            >
              <FolderOpen size={12} /> Abrir carpeta
            </button>
          </div>

          <div className="mt-3 max-h-40 overflow-y-auto history-scroll pr-1 space-y-1.5">
            {(selected.file_items || selected.files.map((filename) => ({
              filename,
              source_path: null,
              output_path: null,
              status: 'pending' as const,
              error: null,
            }))).map((item) => (
              <div key={item.filename} className="rounded-md border border-[#1c2230] bg-[#0b101a] px-2.5 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] text-[#c8d0e0] truncate">{item.filename}</span>
                  <span className={cs('px-1.5 py-0.5 rounded border text-[9px] uppercase tracking-wide shrink-0', fileStatusClass(item.status))}>
                    {item.status}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-2">
                  <span className="text-[9px] text-[#5b6987] truncate">{item.error || item.output_path || item.source_path || ''}</span>
                  {item.output_path ? (
                    <button
                      type="button"
                      onClick={() => void handleOpenPath(item.output_path || '', `Archivo abierto: ${item.filename}`)}
                      className="inline-flex items-center gap-1 text-[9px] text-primary hover:text-blue-300 shrink-0"
                    >
                      Abrir <ChevronRight size={10} />
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => void openDetails(selected.job_id)}
            className="mt-3 inline-flex items-center gap-1 text-[10px] text-primary hover:text-blue-300"
          >
            Refrescar detalle <ChevronRight size={12} />
          </button>
        </div>
      )}
    </div>
  );
}
