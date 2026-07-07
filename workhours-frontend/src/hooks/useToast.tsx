import { createContext, useContext, useState, ReactNode, useCallback } from 'react'

interface Toast { id: number; message: string; type: 'success' | 'error' | 'info' }
interface ToastCtx { toast: (message: string, type?: Toast['type']) => void }
const ToastContext = createContext<ToastCtx | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((message: string, type: Toast['type'] = 'success') => {
    const id = Date.now()
    setToasts(p => [...p, { id, message, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3500)
  }, [])

  const styles: Record<Toast['type'], string> = {
    success: 'bg-slate-900 border-emerald-500/30',
    error: 'bg-slate-900 border-red-500/30',
    info: 'bg-slate-900 border-nebula-500/30',
  }
  const dot: Record<Toast['type'], string> = {
    success: 'bg-emerald-500', error: 'bg-red-500', info: 'bg-nebula-400',
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`${styles[t.type]} flex items-center gap-2.5 text-white pl-3.5 pr-4 py-3 rounded-lg shadow-elevated border text-sm font-medium animate-in slide-in-from-bottom-2 fade-in-0 duration-200 max-w-sm`}
          >
            <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dot[t.type]}`} />
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be inside ToastProvider')
  return ctx
}
