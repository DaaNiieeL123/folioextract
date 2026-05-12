import { useStore } from '../store/useStore';
import { Settings, FolderSync, HeartPulse } from 'lucide-react';
import cs from 'classnames';

interface TopBarProps {
  backendStatus: 'checking' | 'ready' | 'down';
  onOpenSettings: () => void;
  onConvertFolder: () => void;
  isProcessing: boolean;
}

export default function TopBar({ backendStatus, onOpenSettings, onConvertFolder, isProcessing }: TopBarProps) {
  const { format, setFormat, destDir } = useStore();
  const healthLabel = backendStatus === 'ready'
    ? 'Motor Activo'
    : backendStatus === 'checking'
      ? 'Iniciando Motor'
      : 'Motor Sin Respuesta';
  const healthClass = backendStatus === 'ready'
    ? 'border-emerald-400/25 bg-emerald-500/10 text-emerald-200'
    : backendStatus === 'checking'
      ? 'border-amber-400/25 bg-amber-500/10 text-amber-100'
      : 'border-red-400/25 bg-red-500/10 text-red-200';
  const healthDotClass = backendStatus === 'ready'
    ? 'bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.8)]'
    : backendStatus === 'checking'
      ? 'bg-amber-300 shadow-[0_0_12px_rgba(252,211,77,0.7)] animate-pulse'
      : 'bg-red-400 shadow-[0_0_12px_rgba(248,113,113,0.8)]';

  return (
    <div className="flex flex-col z-20 sticky top-0 left-0 right-0">
      {/* ── Premium High-End Header ── */}
      <div className="flex justify-between items-center px-10 py-5 glass-layer relative overflow-hidden">
        {/* Subtle Edge Highlight */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
        
        <div className="flex items-center gap-5 relative z-10 group cursor-default">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-primary-container p-[1px] shadow-glow-primary transition-transform duration-500 group-hover:scale-110">
            <div className="w-full h-full bg-surface-lowest rounded-[11px] flex items-center justify-center relative overflow-hidden">
              <div className="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <img src="/favicon.png" alt="" className="relative z-10 h-7 w-7 object-contain" />
            </div>
          </div>
          <div className="flex flex-col">
            <h1 className="font-display text-[26px] font-bold tracking-[-0.03em] text-white m-0 leading-none drop-shadow-md">
              Folio<span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-primary-on-fixed">Extract</span>
            </h1>
            <span className="text-[10px] font-semibold text-primary tracking-[0.3em] uppercase mt-1 opacity-80">Open Extraction Workspace</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className={cs(
            "flex items-center gap-2.5 px-4 py-2 rounded-xl border backdrop-blur-sm",
            healthClass
          )}>
            <div className={cs("w-2.5 h-2.5 rounded-full", healthDotClass)} />
            <HeartPulse size={15} />
            <span className="text-[12px] font-bold uppercase tracking-[0.16em]">{healthLabel}</span>
          </div>

          <button
            onClick={onOpenSettings}
            disabled={isProcessing}
            className="flex items-center gap-2.5 px-5 py-2.5 bg-white/5 border border-white/5 hover:border-white/15 hover:bg-white/10 rounded-xl text-[13px] font-semibold text-gray-300 hover:text-white transition-all duration-300 shadow-sm disabled:opacity-50 relative overflow-hidden group"
          >
            <Settings size={16} className="text-primary transition-transform group-hover:rotate-90 duration-500" /> Configuración
          </button>
        </div>
      </div>

      {/* ── Tonal Toolbar Core ── */}
      <div className="flex items-center justify-between px-10 py-4 glass-panel border-t-0 border-x-0 rounded-none relative z-10 bg-surface/50">
        <div className="flex items-center gap-10">
          
          {/* Format selector */}
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-bold tracking-[0.2em] text-on-surface-variant uppercase font-sans">FORMATO DE SALIDA</span>
            <div className="flex bg-surface-lowest rounded-xl p-1 border border-white/5 shadow-inner">
              {['.md', '.txt', '.docx'].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => setFormat(fmt)}
                  disabled={isProcessing}
                  className={cs(
                    "px-6 py-1.5 text-[13px] font-bold rounded-lg transition-all duration-300",
                    format === fmt
                      ? "bg-primary text-white shadow-glow-primary scale-100"
                      : "bg-transparent text-on-surface-variant hover:text-white hover:bg-white/5 scale-95"
                  )}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </div>

          <div className="w-px h-8 bg-outline-variant/30" />

          {/* Destination directory */}
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-bold tracking-[0.2em] text-on-surface-variant uppercase font-sans">RUTA DE DESTINO</span>
            <div className="group flex items-center bg-surface-lowest rounded-xl border border-white/5 hover:border-primary/40 transition-colors shadow-inner overflow-hidden">
              <div className="px-5 py-2 max-w-[320px] overflow-hidden">
                <span className="text-on-surface-variant text-[13px] font-mono truncate">{destDir || 'Ninguna ruta seleccionada'}</span>
              </div>
              <button 
                disabled={isProcessing} 
                onClick={onOpenSettings}
                className="px-5 py-2 bg-white/5 border-l border-white/5 text-[12px] font-bold text-primary hover:bg-primary hover:text-white transition-colors duration-300 disabled:opacity-50 tracking-wide uppercase"
              >
                Configurar
              </button>
            </div>
          </div>
        </div>

        {/* PRO Animated Action Button */}
        <button
          onClick={onConvertFolder}
          disabled={isProcessing}
          className="relative overflow-hidden flex items-center gap-2.5 px-7 py-2.5 bg-tertiary text-surface-lowest rounded-xl text-[14px] font-bold transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100 shadow-glow-tertiary group"
        >
          {/* Shimmer Effect */}
          <div className="absolute inset-0 -translate-x-full animate-[shimmer_3s_infinite] bg-gradient-to-r from-transparent via-white/40 to-transparent skew-x-[-15deg]" />
          <FolderSync size={18} className="relative z-10 transition-transform group-hover:rotate-180 duration-700" /> 
          <span className="relative z-10">{isProcessing ? 'Sincronizando Archivos...' : 'Procesar Carpeta Completa'}</span>
        </button>
      </div>
    </div>
  );
}
