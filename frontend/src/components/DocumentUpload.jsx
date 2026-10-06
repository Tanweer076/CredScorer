import { useEffect, useState } from 'react'
import api, { errorMessage } from '../api'
import { Card, ErrorBox } from './ui'

const DOC_TYPES = [
  { type: 'salary_slip', label: 'Salary slip', hint: 'Your latest monthly salary slip.' },
  { type: 'bank_statement', label: 'Bank statement', hint: 'The last 3 months, showing your salary credits.' },
]
const MAX_BYTES = 5 * 1024 * 1024

// The newest upload of each type counts; a re-upload replaces the earlier one.
function latestDocuments(documents) {
  const latest = {}
  for (const document of [...documents].sort((a, b) => a.id - b.id)) latest[document.doc_type] = document
  return latest
}

export default function DocumentUpload({ applicationId, documents, canUpload, onUploaded }) {
  const latest = latestDocuments(documents)
  return (
    <Card title="Documents">
      <p className="mb-4 text-sm text-slate-600">
        Upload both as PDF files (up to 5 MB each). We read them automatically and check them against your form.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {DOC_TYPES.map((d) => (
          <DocumentSlot
            key={d.type}
            applicationId={applicationId}
            docType={d.type}
            label={d.label}
            hint={d.hint}
            document={latest[d.type]}
            canUpload={canUpload}
            onUploaded={onUploaded}
          />
        ))}
      </div>
    </Card>
  )
}

function DocumentSlot({ applicationId, docType, label, hint, document, canUpload, onUploaded }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [check, setCheck] = useState(null)
  const finished = document && document.extraction_status !== 'PENDING'

  // Once the worker has read the document, fetch what it found.
  useEffect(() => {
    if (!finished) return
    let cancelled = false
    api.get(`/applications/${applicationId}/documents/${document.id}/extraction`)
      .then((response) => { if (!cancelled) setCheck(response.data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [applicationId, document?.id, finished])

  async function upload(event) {
    const file = event.target.files[0]
    event.target.value = '' // so choosing the same file again still triggers a change
    if (!file) return
    if (file.size > MAX_BYTES) {
      setError('File is larger than 5 MB')
      return
    }
    const form = new FormData()
    form.append('doc_type', docType)
    form.append('file', file)
    setUploading(true)
    setError('')
    try {
      await api.post(`/applications/${applicationId}/documents`, form)
      onUploaded()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setUploading(false)
    }
  }

  // Only show the check result for the document currently on screen, not an older upload.
  const result = check && document && check.document_id === document.id ? check : null

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="font-medium text-slate-800">{label}</h3>
        <DocumentState document={document} result={result} />
      </div>
      <p className="mb-3 text-xs text-slate-500">{hint}</p>

      {result && result.issues.length > 0 && (
        <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-amber-800">
          {result.issues.map((issue) => <li key={issue}>{issue}</li>)}
        </ul>
      )}

      {canUpload && (
        <label className={`inline-block cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 ${uploading ? 'pointer-events-none opacity-50' : ''}`}>
          {uploading ? 'Uploading…' : document ? 'Upload a new file' : 'Choose PDF'}
          <input type="file" accept="application/pdf,.pdf" className="hidden" onChange={upload} disabled={uploading} />
        </label>
      )}
      <div className="mt-2"><ErrorBox message={error} /></div>
    </div>
  )
}

function DocumentState({ document, result }) {
  if (!document) return <Pill className="bg-slate-100 text-slate-600">Not uploaded</Pill>
  if (document.extraction_status === 'PENDING') {
    return <Pill className="animate-pulse bg-sky-100 text-sky-700">Reading…</Pill>
  }
  if (document.extraction_status === 'FAILED') return <Pill className="bg-red-100 text-red-700">Could not read</Pill>
  if (!result) return <Pill className="bg-slate-100 text-slate-600">Checking…</Pill>
  if (result.passed) return <Pill className="bg-emerald-100 text-emerald-700">✓ Verified</Pill>
  return <Pill className="bg-amber-100 text-amber-800">Needs attention</Pill>
}

function Pill({ className, children }) {
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>{children}</span>
}