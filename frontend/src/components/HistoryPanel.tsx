import { useMemo } from 'react';
import { useStore } from '../store/useStore';
import { Activity, FileText, Sparkles, AlertTriangle } from 'lucide-react';
import cs from 'classnames';
import JobHistoryPanel from './JobHistoryPanel';

interface Props {
  onShowToast?: (payload: { message: string; type: 'success' | 'error' | 'info' }) => void;
  onTrackJob?: (jobId: string) => Promise<void> | void;
}

export default function HistoryPanel({ onShowToast, onTrackJob }: Props) {
  const { history, clearHistory } = useStore();
  const entries = useMemo(() => Object.values(history).reverse(), [history]);
  const completed = entries.filter(e => !e.isProcessing && !e.isError).length;
  const errors = entries.filter(e => e.isError).length;

  return (
    <div className="w-[460px] h-full flex flex-col glass-panel rounded-[2rem] ml-4 relative overflow-hidden z-10">
      {/* Ambient Top Glow */}
      <div className="absolute top-0 left-0 right-0 h-32 bg-primary/5 blur-[40px] pointer-events-none" />

      <div className="px-8 pt-8 pb-6 flex justify-between items-end border-b border-white/5 relative z-10">
        <div>
          <h2 className="font-display text-[22px] font-bold text-white tracking-[-0.02em] mb-1.5 flex items-center gap-2">
            <Activity size={20} className="text-primary" /> Registro de Actividad
          </h2>
          <p className="font-sans text-[13px] text-on-surface-variant">Archivos documentados y procesados.</p>
        </div>
        <button
          onClick={clearHistory}
          disabled={entries.length === 0}
          className="text-[11px] font-bold text-outline-variant hover:text-error transition-colors uppercase tracking-[0.2em] border border-white/5 px-3 py-1.5 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-error/10 hover:border-error/30"
        >
          Limpiar
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-3 relative z-10">
        {entries.length === 0 ? (
          <div className="min-h-[280px] flex flex-col items-center justify-center text-on-surface-variant opacity-80">
            <div className="w-20 h-20 bg-surface-lowest border border-white/5 rounded-full flex items-center justify-center mb-5 animate-float shadow-ambient">
              <Sparkles size={32} className="text-primary/50" />
            </div>
            <p className="font-display text-[20px] font-semibold text-white">Historial Vacío</p>
            <p className="font-sans text-[14px] mt-2 text-center max-w-[250px]">Arrastra documentos al núcleo central para iniciar la secuencia.</p>
          </div>
        ) : (
          entries.map(item => {
            return (
              <div
                key={item.filename}
                className="group p-4 flex items-center gap-4 bg-surface-lowest/50 border border-white/5 rounded-2xl hover:bg-white/[0.03] hover:border-white/10 transition-all duration-300 hover:shadow-ambient hover:-translate-y-0.5 relative overflow-hidden"
              >
                {/* Status Indicator Bar */}
                <div className={cs(
                  "absolute left-0 top-0 bottom-0 w-1 transition-colors duration-500",
                  item.isProcessing ? "bg-primary animate-pulse" : item.isError ? "bg-error" : "bg-tertiary shadow-glow-tertiary"
                )} />

                <div className={cs(
                  "w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border transition-all duration-500",
                  item.isProcessing ? "bg-primary/10 border-primary/30 text-primary" : 
                  item.isError ? "bg-error/10 border-error/30 text-error" : 
                  "bg-white/5 border-white/10 text-on-surface-variant"
                )}>
                  {item.isProcessing ? (
                    <div className="w-5 h-5 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                  ) : item.isError ? (
                    <AlertTriangle size={20} />
                  ) : (
                    <FileText size={20} strokeWidth={1.5} />
                  )}
                </div>

                <div className="flex-1 min-w-0 pr-2">
                  <p className="font-sans font-semibold text-on-surface text-[14px] truncate mb-1">
                    {item.filename}
                  </p>
                  <p className="font-sans text-[12px] text-on-surface-variant">
                    {item.isProcessing ? (
                      <span className="text-primary animate-pulse flex items-center gap-1.5"><Activity size={12}/> Procesando conversión...</span>
                    ) : item.isError ? (
                      <span className="text-error">{item.errorMsg}</span>
                    ) : (
                      <span className="text-tertiary font-medium">Extracción completada.</span>
                    )}
                  </p>
                </div>
                
                <div className="flex flex-col items-center justify-center shrink-0 w-[46px] h-[46px] rounded-lg bg-surface-lowest border border-white/5">
                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider">{item.format?.replace('.', '') || 'MD'}</span>
                </div>
              </div>
            );
          })
        )}

        <JobHistoryPanel onShowToast={onShowToast} onTrackJob={onTrackJob} />
      </div>

      <div className="px-8 py-5 bg-surface-highest/60 border-t border-white/5 flex justify-between items-center relative z-10 backdrop-blur-md">
        <span className="text-[12px] font-bold uppercase tracking-[0.15em] text-on-surface-variant">Operaciones Exitosas</span>
        <div className="flex items-center gap-3">
          {errors > 0 && <span className="text-error text-[13px] font-bold bg-error/10 px-3 py-1 rounded-md">{errors} Errores</span>}
          <span className="text-tertiary font-bold text-[18px] px-3 py-1 bg-tertiary/10 rounded-md border border-tertiary/20 shadow-glow-tertiary">{completed}</span>
        </div>
      </div>
    </div>
  );
}
