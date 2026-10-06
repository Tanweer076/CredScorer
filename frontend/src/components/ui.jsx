// Small shared building blocks, so every page looks the same.

export function Card({ title, children, className = '' }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}>
      {title && <h2 className="mb-4 text-lg font-semibold text-slate-800">{title}</h2>}
      {children}
    </section>
  )
}

export function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
    secondary: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    success: 'bg-emerald-600 text-white hover:bg-emerald-700',
  }
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  )
}

export const inputClass =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'

export function ErrorBox({ message }) {
  if (!message) return null
  return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p>
}

const STATUS_STYLES = {
  SUBMITTED: 'bg-slate-100 text-slate-700',
  DOCS_VERIFIED: 'bg-sky-100 text-sky-700',
  SCORED: 'bg-violet-100 text-violet-700',
  MANUAL_REVIEW: 'bg-amber-100 text-amber-800',
  APPROVED: 'bg-emerald-100 text-emerald-700',
  REJECTED: 'bg-red-100 text-red-700',
}

const STATUS_LABELS = {
  SUBMITTED: 'Submitted',
  DOCS_VERIFIED: 'Documents verified',
  SCORED: 'Scored',
  MANUAL_REVIEW: 'Under review',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
}

export function StatusBadge({ status }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status] || 'bg-slate-100'}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}