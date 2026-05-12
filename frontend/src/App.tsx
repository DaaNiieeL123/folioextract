import { useState, useCallback, useRef, useEffect } from 'react';
import { useStore } from './store/useStore';
import { convertPdfUpload, getHealth, getJob, getJobs, getSettings, selectOutputDirectory, subscribeToProgress, updateSettings } from './services/api/client';
import DropZone from './components/DropZone';
import HistoryPanel from './components/HistoryPanel';
import TopBar from './components/TopBar';
import SettingsModal from './components/SettingsModal';
import Toast from './components/Toast';
import cs from 'classnames';

export type ToastPayload = { message: string; type: 'success' | 'error' | 'info' };

function App() {
  const { format, destDir, setDestDir, addOrUpdateHistory } = useStore();
  const [progressMsg, setProgressMsg] = useState('Sistema inactivo. Esperando documentos para extracción.');
  const [progressCount, setProgressCount] = useState({ current: 0, total: 0 });
  const [progressStats, setProgressStats] = useState({ success: 0, error: 0 });
  const [etaSeconds, setEtaSeconds] = useState<number | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'ready' | 'down'>('checking');
  const [toast, setToast] = useState<ToastPayload | null>(null);
  const unsubscribeProgressRef = useRef<(() => void) | null>(null);
  const conversionStartedAtRef = useRef<number | null>(null);
  const settingsThemeRef = useRef('System');
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const trackedJobIdRef = useRef<string | null>(null);

  useEffect(() => () => {
    unsubscribeProgressRef.current?.();
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadSettings = async () => {
      try {
        const data = await getSettings();
        if (!mounted) return;
        settingsThemeRef.current = data.theme || 'System';
        setDestDir(data.last_output_dir || '');
      } catch {
        // Keep local defaults if settings cannot be loaded.
      }
    };

    void loadSettings();
    return () => {
      mounted = false;
    };
  }, [setDestDir]);

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const data = await getHealth();
        if (!mounted) return;
        setBackendStatus((data.backend_ready ?? data.status === 'ok') ? 'ready' : 'down');
      } catch {
        if (!mounted) return;
        setBackendStatus('down');
      }
    };

    void checkHealth();
    const id = window.setInterval(() => {
      void checkHealth();
    }, 4000);

    return () => {
      mounted = false;
      window.clearInterval(id);
    };
  }, []);

  const showToast = useCallback((payload: ToastPayload) => {
    setToast(payload);
    setTimeout(() => setToast(null), 4000);
  }, []);

  const getErrorMessage = useCallback((error: unknown, fallback: string) => {
    if (error instanceof Error && error.message.trim()) {
      return error.message;
    }
    return fallback;
  }, []);

  const persistDestination = useCallback(async (nextDir: string) => {
    const saved = await updateSettings({
      theme: settingsThemeRef.current,
      last_output_dir: nextDir,
    });
    settingsThemeRef.current = saved.theme || 'System';
    setDestDir(saved.last_output_dir || '');
    return saved.last_output_dir || '';
  }, [setDestDir]);

  const trackJob = useCallback(async (
    jobId: string,
    fallback?: { total?: number; filenames?: string[]; format?: string }
  ) => {
    unsubscribeProgressRef.current?.();
    trackedJobIdRef.current = jobId;
    conversionStartedAtRef.current = Date.now();
    setIsProcessing(true);

    const detail = await getJob(jobId);
    const trackedFormat = detail?.extension || fallback?.format || format;
    const total = detail?.total || fallback?.total || 0;
    const fileNames = detail?.file_items?.map((item) => item.filename) || fallback?.filenames || [];

    setProgressCount({ current: detail?.processed || 0, total });
    setProgressStats({ success: detail?.successes || 0, error: detail?.errors || 0 });
    setEtaSeconds(null);
    setProgressMsg(
      detail?.status === 'queued'
        ? `Job ${jobId.slice(0, 8)} en cola de ejecución...`
        : `Iniciando secuencia de extracción para ${total} documento${total === 1 ? '' : 's'}...`
    );

    fileNames.forEach((filename) =>
      addOrUpdateHistory(filename, {
        isProcessing: true,
        isError: false,
        format: trackedFormat,
      })
    );

    let successes = Number(detail?.successes || 0);
    let errors = Number(detail?.errors || 0);
    const extractName = (name: string) => name.split(/[/\\]/).pop() || name;

    unsubscribeProgressRef.current = subscribeToProgress(jobId, (data) => {
      if (data.filename) {
        const name = extractName(String(data.filename));
        const current = Number(data.current || 0);
        const totalFromEvent = Number(data.total || total);

        addOrUpdateHistory(name, {
          isProcessing: false,
          isError: !!data.is_error,
          errorMsg: data.error_msg as string | undefined,
          format: trackedFormat,
        });
        setProgressCount({ current, total: totalFromEvent });
        setProgressStats((prev) => {
          const nextSuccess = data.is_error ? prev.success : prev.success + 1;
          const nextError = data.is_error ? prev.error + 1 : prev.error;
          const percent = totalFromEvent ? Math.round((current / totalFromEvent) * 100) : 0;
          if (conversionStartedAtRef.current && current > 0 && totalFromEvent > current) {
            const elapsedSeconds = (Date.now() - conversionStartedAtRef.current) / 1000;
            const averagePerFile = elapsedSeconds / current;
            const remaining = Math.max(0, Math.round((totalFromEvent - current) * averagePerFile));
            setEtaSeconds(remaining);
          } else {
            setEtaSeconds(null);
          }
          setProgressMsg(`Procesando ${current}/${totalFromEvent} (${percent}%) · ${name}`);
          return { success: nextSuccess, error: nextError };
        });
      } else if (data.successes !== undefined) {
        successes = Number(data.successes);
        errors = Number(data.errors);
        const finalStatus = String(data.status || 'completed');
        setProgressStats({ success: successes, error: errors });
        setEtaSeconds(0);
        if (finalStatus === 'canceled') {
          setProgressMsg(`Job cancelado. ${successes} archivos terminaron antes de la cancelación.`);
          showToast({ message: 'Job cancelado.', type: 'info' });
        } else if (finalStatus === 'failed') {
          setProgressMsg(`Job finalizado con errores. ${errors} fallo(s).`);
          showToast({ message: `${successes} completados · ${errors} errores`, type: 'error' });
        } else {
          setProgressMsg(`Secuencia finalizada — ¡${successes} operaciones exitosas!${errors ? ` (${errors} fallos)` : ''}`);
          showToast({
            message: errors
              ? `${successes} completados · ${errors} errores`
              : `Operación maestra finalizada. ${successes} documentos listos.`,
            type: errors ? 'error' : 'success'
          });
        }
        setIsProcessing(false);
      }
    }, () => {
      setIsProcessing(false);
      conversionStartedAtRef.current = null;
      unsubscribeProgressRef.current = null;
      trackedJobIdRef.current = null;
    });
  }, [addOrUpdateHistory, format, showToast]);

  useEffect(() => {
    if (backendStatus !== 'ready' || isProcessing || trackedJobIdRef.current) return;
    let mounted = true;

    const restoreActiveJob = async () => {
      try {
        const jobs = await getJobs(10);
        if (!mounted) return;
        const activeJob = jobs.find((job) => job.status === 'queued' || job.status === 'running');
        if (activeJob) {
          await trackJob(activeJob.job_id);
        }
      } catch {
        // No-op: the regular health polling will keep the shell state updated.
      }
    };

    void restoreActiveJob();
    return () => {
      mounted = false;
    };
  }, [backendStatus, isProcessing, trackJob]);

  const handleDestinationChange = useCallback(async (nextDir: string) => {
    try {
      const savedDir = await persistDestination(nextDir);
      if (savedDir) {
        showToast({ message: 'Directorio de salida actualizado.', type: 'success' });
      } else {
        showToast({ message: 'Directorio de salida limpiado.', type: 'info' });
      }
    } catch (error) {
      showToast({ message: getErrorMessage(error, 'No se pudo guardar la configuración.'), type: 'error' });
      throw error;
    }
  }, [getErrorMessage, persistDestination, showToast]);

  const handleBrowseDestination = useCallback(async () => {
    try {
      const data = await selectOutputDirectory(destDir);
      return data.path || '';
    } catch (error) {
      showToast({ message: getErrorMessage(error, 'No se pudo abrir el selector de carpetas.'), type: 'error' });
      throw error;
    }
  }, [destDir, getErrorMessage, showToast]);

  const handleFilesDropped = useCallback(async (files: File[]) => {
    const pdfFiles = files.filter((file) => file.name.toLowerCase().endsWith('.pdf'));
    if (!pdfFiles.length || isProcessing) return;
    if (!destDir.trim()) {
      showToast({ message: 'Asegúrate de configurar la RUTA DE DESTINO primero.', type: 'info' });
      return;
    }
    if (backendStatus !== 'ready') {
      showToast({ message: 'El motor de procesamiento no está disponible todavía.', type: 'error' });
      return;
    }

    const total = pdfFiles.length;
    setProgressCount({ current: 0, total });
    setProgressStats({ success: 0, error: 0 });
    setEtaSeconds(null);
    setProgressMsg(`Iniciando secuencia de extracción para ${total} documento${total > 1 ? 's' : ''}...`);

    try {
      const { job_id: jobId } = await convertPdfUpload(pdfFiles, destDir, format);
      await trackJob(jobId, {
        total,
        filenames: pdfFiles.map((file) => file.name),
        format,
      });
    } catch (error) {
      const errorMessage = getErrorMessage(error, 'Error de conexión con el núcleo.');
      showToast({ message: errorMessage, type: 'error' });
      setProgressMsg(errorMessage);
      setIsProcessing(false);
      conversionStartedAtRef.current = null;
    }
  }, [backendStatus, destDir, format, getErrorMessage, isProcessing, showToast, trackJob]);

  const handleConvertFolder = useCallback(() => {
    if (isProcessing) return;
    folderInputRef.current?.click();
  }, [isProcessing]);

  const handleFolderInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []).filter((file) => file.name.toLowerCase().endsWith('.pdf'));
    if (!selectedFiles.length) {
      showToast({ message: 'La carpeta está vacía o no contiene PDFs válidos.', type: 'info' });
      e.target.value = '';
      return;
    }
    void handleFilesDropped(selectedFiles);
    e.target.value = '';
  }, [handleFilesDropped, showToast]);

  const progressPercent = progressCount.total
    ? (progressCount.current / progressCount.total) * 100
    : 0;
  const effectiveProgressMsg = !isProcessing && backendStatus === 'checking'
    ? 'Inicializando motor de conversion...'
    : !isProcessing && backendStatus === 'down'
      ? 'Motor de procesamiento no disponible.'
      : progressMsg;

  return (
    <div className="h-screen w-full bg-background font-sans overflow-hidden flex flex-col relative z-0 text-on-surface">
      
      {/* ── Breathtaking Ambient Aurora Core ── */}
      <div className="aurora-bg" />
      <div className="absolute inset-0 bg-background/60 backdrop-blur-[100px] pointer-events-none z-0" />
      {/* ────────────────────────────────────── */}

      <TopBar
        backendStatus={backendStatus}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onConvertFolder={handleConvertFolder}
        isProcessing={isProcessing}
      />

      {backendStatus !== 'ready' && (
        <div className="py-2.5 px-10 bg-error/10 border-b border-error/20 text-error text-[11px] font-bold tracking-[0.2em] uppercase text-center backdrop-blur-md relative z-10 shadow-glow-error">
          ⚠️ {backendStatus === 'checking' ? 'Inicializando motor interno...' : 'Motor no disponible. Verifica el backend.'}
        </div>
      )}

      {/* Main Container Layered over Aurora */}
      <div className="flex-1 flex px-10 py-8 gap-0 overflow-hidden relative z-10">
        <input
          ref={(node) => {
            folderInputRef.current = node;
            if (node) {
              node.setAttribute('webkitdirectory', '');
              node.setAttribute('directory', '');
            }
          }}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          className="hidden"
          onChange={handleFolderInputChange}
        />
        <DropZone onDrop={handleFilesDropped} disabled={isProcessing} />
        <HistoryPanel onShowToast={showToast} onTrackJob={trackJob} />
      </div>

      {/* Extreme Glass Status Bar */}
      <div className="h-16 glass-layer border-t border-white/5 border-b-0 flex items-center shrink-0 px-10 gap-8 relative z-20">
        <div className={cs(
          "w-3.5 h-3.5 rounded-full transition-all duration-500",
          isProcessing ? "bg-primary shadow-glow-primary animate-ping" : "bg-white/10"
        )} />
        <span aria-live="polite" className="text-[13px] font-semibold text-gray-300 flex-1 truncate font-mono tracking-wide">{effectiveProgressMsg}</span>

        <div className="w-[300px] h-2.5 bg-background shadow-inner rounded-full overflow-hidden border border-white/10 relative">
          <div
            className="absolute left-0 top-0 bottom-0 bg-primary transition-all duration-300 ease-out progress-bar shadow-glow-primary"
            style={{ '--progress': `${progressPercent}%` } as { [key: string]: string }}
          />
        </div>

        <div className="flex gap-8 text-[12px] font-bold tracking-[0.15em] uppercase text-on-surface-variant font-mono">
          <span className="flex gap-2">BLOQUE <span className="text-primary">{progressCount.current}/{progressCount.total || 0}</span></span>
          <span className="flex gap-2">OK <span className="text-tertiary drop-shadow-[0_0_8px_rgba(0,230,150,0.5)]">{progressStats.success}</span></span>
          <span className="flex gap-2">ERR <span className="text-error drop-shadow-[0_0_8px_rgba(255,79,100,0.5)]">{progressStats.error}</span></span>
          <span className="flex gap-2">ETA <span className="text-white">{etaSeconds === null ? '--' : `${etaSeconds}s`}</span></span>
        </div>
      </div>

      {isSettingsOpen && (
        <SettingsModal
          onClose={() => setIsSettingsOpen(false)}
          onBrowseDestination={handleBrowseDestination}
          onSaveDestination={handleDestinationChange}
        />
      )}
      {toast && <Toast {...toast} onDismiss={() => setToast(null)} />}
    </div>
  );
}

export default App;
