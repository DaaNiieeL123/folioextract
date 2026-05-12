import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type HistoryItem = {
  filename: string;
  isProcessing: boolean;
  isError: boolean;
  errorMsg?: string;
  format?: string;
  timestamp?: number;
};

interface AppState {
  format: string;
  setFormat: (fmt: string) => void;
  destDir: string;
  setDestDir: (dir: string) => void;

  history: Record<string, HistoryItem>;
  addOrUpdateHistory: (filename: string, update: Partial<HistoryItem>) => void;
  clearHistory: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      format: '.md',
      setFormat: (fmt) => set({ format: fmt }),
      destDir: '',
      setDestDir: (dir) => set({ destDir: dir }),

      history: {},
      addOrUpdateHistory: (filename, update) =>
        set((state) => ({
          history: {
            ...state.history,
            [filename]: {
              ...(state.history[filename] || {
                filename,
                isProcessing: true,
                isError: false,
                timestamp: Date.now(),
              }),
              ...update,
            },
          },
        })),
      clearHistory: () => set({ history: {} }),
    }),
    {
      name: 'folioextract-store',                         // localStorage key
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        format: state.format,                            // persist format selection
        // output directory is persisted by backend settings
      }),
    }
  )
);
