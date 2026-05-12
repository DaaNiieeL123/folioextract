import { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { X, HardDrive, ShieldCheck, FolderOpen, RefreshCcw } from 'lucide-react';

interface Props {
  onClose: () => void;
  onBrowseDestination: () => Promise<string>;
  onSaveDestination: (path: string) => Promise<void>;
}

export default function SettingsModal({ onClose, onBrowseDestination, onSaveDestination }: Props) {
  const { destDir } = useStore();
  const [draftDir, setDraftDir] = useState(destDir);
  const [isSaving, setIsSaving] = useState(false);
  const [isBrowsing, setIsBrowsing] = useState(false);

  useEffect(() => {
    setDraftDir(destDir);
  }, [destDir]);

  const handleBrowse = async () => {
    setIsBrowsing(true);
    try {
      const selected = await onBrowseDestination();
      if (selected) {
        setDraftDir(selected);
      }
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSaveDestination(draftDir);
      onClose();
    } catch {
      // The parent handler already surfaces the error to the user.
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-[20px] flex items-center justify-center z-50 p-4 transition-all duration-300">
      <div className="bg-surface-lowest border border-white/10 w-full max-w-2xl rounded-[1.5rem] shadow-[0_30px_60px_rgba(0,0,0,0.6)] flex flex-col overflow-hidden relative">
        
        {/* Glow Effects */}
        <div className="absolute -top-32 -right-32 w-64 h-64 bg-primary/20 rounded-full blur-[80px] pointer-events-none" />
        <div className="absolute -bottom-32 -left-32 w-64 h-64 bg-tertiary/10 rounded-full blur-[80px] pointer-events-none" />

        {/* Header */}
        <div className="flex justify-between items-center px-8 py-6 border-b border-white/5 relative z-10 bg-surface-highest/30">
          <div>
            <h2 className="font-display text-[22px] font-bold text-white tracking-[-0.02em]">Centro de Control</h2>
            <p className="text-[13px] text-on-surface-variant font-sans mt-1">Configura el comportamiento del núcleo de FolioExtract.</p>
          </div>
          <button 
            onClick={onClose} 
            className="w-10 h-10 flex items-center justify-center bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/20 rounded-xl text-on-surface-variant hover:text-white transition-all duration-300 group"
          >
            <X size={18} className="transition-transform group-hover:rotate-90 duration-300" />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex flex-1 min-h-[300px] relative z-10">
          
          {/* Sidebar Tabs */}
          <div className="w-64 bg-surface-highest/20 border-r border-white/5 p-4 flex flex-col gap-2">
            <button
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 text-[13.5px] font-semibold tracking-wide bg-primary/10 text-primary border border-primary/20 shadow-glow-primary"
            >
              <HardDrive size={18} /> Almacenamiento
            </button>
          </div>

          {/* Settings Body */}
          <div className="flex-1 p-8 overflow-y-auto">
            <div className="space-y-6 animate-fade-in">
              <h3 className="text-white font-display text-lg mb-4">Rutas y Destinos</h3>
              
              <div>
                <label className="block text-[11px] font-bold tracking-[0.15em] uppercase text-primary mb-2">Directorio de Salida Global</label>
                <p className="text-[13px] text-on-surface-variant mb-3">Elige con el explorador la carpeta donde quieres guardar los archivos convertidos. Ya no hace falta escribir rutas manualmente.</p>
                <div className="rounded-2xl border border-white/10 bg-surface-lowest overflow-hidden">
                  <div className="px-4 py-3 border-b border-white/5">
                    <span className="block text-[12px] uppercase tracking-[0.15em] text-on-surface-variant mb-2">Carpeta Seleccionada</span>
                    <div className="min-h-[52px] rounded-xl border border-white/10 bg-background/40 px-4 py-3 text-[13px] text-white font-mono break-all">
                      {draftDir || 'Todavía no has seleccionado ninguna carpeta.'}
                    </div>
                  </div>
                  <div className="px-4 py-4 flex gap-3">
                    <button
                      type="button"
                      onClick={() => void handleBrowse()}
                      disabled={isBrowsing || isSaving}
                      className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary-container text-white font-bold rounded-xl transition-all shadow-glow-primary hover:scale-[1.02] active:scale-[0.98] text-[13px] disabled:opacity-60 disabled:hover:scale-100"
                    >
                      {isBrowsing ? <RefreshCcw size={16} className="animate-spin" /> : <FolderOpen size={16} />}
                      {isBrowsing ? 'Abriendo selector...' : 'Elegir carpeta'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setDraftDir('')}
                      disabled={isBrowsing || isSaving || !draftDir}
                      className="px-4 py-2.5 bg-transparent hover:bg-white/5 text-white font-semibold rounded-xl transition-all duration-300 border border-white/10 disabled:opacity-40 text-[13px]"
                    >
                      Limpiar
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3 p-3 bg-tertiary/5 border border-tertiary/10 rounded-lg">
                  <ShieldCheck size={16} className="text-tertiary" />
                  <span className="text-[12px] text-tertiary/90 font-medium">Directorio habilitado para escritura de extracción masiva.</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-8 py-5 border-t border-white/5 bg-surface-highest/50 flex justify-end gap-3 relative z-10 backdrop-blur-md">
          <button 
            onClick={onClose} 
            disabled={isSaving || isBrowsing}
            className="px-6 py-2.5 bg-transparent hover:bg-white/5 text-white font-semibold rounded-xl transition-all duration-300 border border-transparent hover:border-white/10 focus:outline-none text-[13px]"
          >
            Cerrar Ventana
          </button>
          <button 
            onClick={handleSave}
            disabled={isSaving || isBrowsing}
            className="px-7 py-2.5 bg-primary hover:bg-primary-container text-white font-bold rounded-xl transition-all shadow-glow-primary hover:scale-[1.02] active:scale-[0.98] text-[13px] disabled:opacity-60 disabled:hover:scale-100"
          >
            {isSaving ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>
    </div>
  );
}
