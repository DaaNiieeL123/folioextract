import { CheckCircle2, XCircle, Info, X } from 'lucide-react';
import cs from 'classnames';
import type { ToastPayload } from '../App';

interface ToastProps extends ToastPayload {
  onDismiss: () => void;
}

const icons = {
  success: <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />,
  error: <XCircle size={18} className="text-red-400 shrink-0" />,
  info: <Info size={18} className="text-blue-400 shrink-0" />,
};

const borders = {
  success: 'border-l-emerald-500',
  error: 'border-l-red-500',
  info: 'border-l-blue-500',
};

export default function Toast({ message, type, onDismiss }: ToastProps) {
  return (
    <div className={cs(
      "fixed bottom-16 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl",
      "bg-[#121724] border border-[#1e2a3d] border-l-4 shadow-2xl",
      "animate-slide-up max-w-sm",
      borders[type]
    )}>
      {icons[type]}
      <span className="text-[13px] text-gray-200 font-medium flex-1">{message}</span>
      <button onClick={onDismiss} title="Cerrar notificación" aria-label="Cerrar notificación" className="text-[#464c63] hover:text-gray-300 transition-colors ml-2">
        <X size={14} />
      </button>
    </div>
  );
}
