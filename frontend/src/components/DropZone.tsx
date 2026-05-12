import { useCallback, useRef, useState } from 'react';
import { UploadCloud, Zap, Cpu } from 'lucide-react';
import cs from 'classnames';

interface Props {
  onDrop: (files: File[]) => void;
  disabled?: boolean;
}

export default function DropZone({ onDrop, disabled = false }: Props) {
  const [isHovered, setIsHovered] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const extractPdfFiles = useCallback((files: FileList | File[]) => {
    return Array.from(files).filter((file) => file.name.toLowerCase().endsWith('.pdf'));
  }, []);

  const handleClick = useCallback(() => {
    if (disabled) return;
    inputRef.current?.click();
  }, [disabled]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? extractPdfFiles(e.target.files) : [];
    if (files.length > 0) {
      onDrop(files);
    }
    e.target.value = '';
  }, [extractPdfFiles, onDrop]);

  const handleWebDrop = useCallback((e: React.DragEvent) => {
    if (disabled) return;
    e.preventDefault();
    setIsHovered(false);

    const files = extractPdfFiles(e.dataTransfer.files);
    if (files.length > 0) {
      onDrop(files);
    }
  }, [extractPdfFiles, onDrop, disabled]);

  return (
    <div
      className={cs(
        "flex-1 flex flex-col items-center justify-center p-10 cursor-pointer transition-all duration-500 relative rounded-[2rem] overflow-hidden group",
        isHovered ? "bg-primary/5 scale-[1.01]" : "bg-surface-lowest/40 hover:bg-surface-lowest/80",
        disabled ? "opacity-40 cursor-not-allowed filter grayscale" : "hover:shadow-glow-primary/20"
      )}
      onDragOver={e => { e.preventDefault(); if (!disabled) setIsHovered(true); }}
      onDragLeave={() => setIsHovered(false)}
      onDrop={handleWebDrop}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        multiple
        className="hidden"
        onChange={handleInputChange}
      />

      {/* Animated Ghost Border */}
      <div className={cs("absolute inset-2 pointer-events-none rounded-[1.5rem] transition-all duration-500 animated-dashed-border", isHovered ? "is-hovered" : "")} />

      {/* Floating Ambient Glow */}
      <div className={cs(
        "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-primary/20 border-primary blur-[80px] rounded-full pointer-events-none transition-all duration-700",
        isHovered ? "opacity-100 scale-150 animate-pulse-glow" : "opacity-0 scale-50"
      )} />

      {/* Futuristic Center Icon */}
      <div className={cs(
        "mb-10 relative z-10 w-28 h-28 rounded-full flex items-center justify-center transition-all duration-500 border glass-panel",
        isHovered ? "border-primary/50 shadow-glow-primary scale-110" : "border-white/5 shadow-ambient animate-float"
      )}>
        <UploadCloud size={44} strokeWidth={1.2} className={cs("transition-all duration-500", isHovered ? "text-primary drop-shadow-[0_0_15px_rgba(136,145,255,0.8)]" : "text-primary/70")} />
        {isHovered && (
          <div className="absolute inset-0 rounded-full border border-primary/40 animate-ping opacity-20" />
        )}
      </div>

      <div className="relative z-10 flex flex-col items-center max-w-lg text-center gap-5">
        <h2 className={cs(
          "font-display text-[2.75rem] font-bold tracking-[-0.03em] leading-tight transition-all duration-500",
          isHovered ? "text-white text-glow" : "text-on-surface"
        )}>
          Zona de Extracción
        </h2>
        <p className="text-[17px] text-on-surface-variant font-sans leading-relaxed tracking-wide">
          {disabled ? 'Sincronización en proceso. Por favor espere.' : 'Arrastra múltiples documentos PDF a este núcleo, o haz clic para explorar tus archivos locales.'}
        </p>

        <div className="flex gap-4 items-center mt-6">
          <span className="flex items-center gap-2 px-4 py-2 rounded-full border border-white/5 text-[11px] font-bold text-on-surface-variant uppercase tracking-[0.2em] bg-white/[0.02] backdrop-blur-md shadow-sm">
            <Zap size={14} className="text-tertiary" /> Soporte Multi-Lote
          </span>
          <span className="flex items-center gap-2 px-4 py-2 rounded-full border border-primary/20 text-[11px] font-bold text-primary uppercase tracking-[0.2em] bg-primary/[0.05] backdrop-blur-md shadow-[0_0_10px_rgba(136,145,255,0.1)] group-hover:border-primary/50 transition-colors">
            <Cpu size={14} className="text-primary-on-fixed" /> Motor IA Integrado
          </span>
        </div>
      </div>
    </div>
  );
}
