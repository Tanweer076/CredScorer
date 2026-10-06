import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage } from '../../api'
import ShapChart from '../../components/ShapChart'
import { Button, Card, ErrorBox, inputClass, StatusBadge } from '../../components/ui'
import { money } from '../../format'

const DOC_LABELS = { salary_slip: 'Salary slip', bank_statement: 'Bank statement' }

// Everything an underwriter needs for one application, and the approve / reject form.
export default function ReviewApplication() {
  const { id } = useParams()
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0) // bump to fetch again after a decision

  useEffect(() => {
    let cancelled = false
    api.get(`/underwriter/applications/${id}`)
      .then((response) => { if (!cancelled) setDetail(response.data) })
      .catch((err) => { if (!cancelled) setError(errorMessage(err)) })
    return () => { cancelled = true }
  }, [id, refresh])

  if (!detail) return error ? <ErrorBox message={error} /> : <p className="text-slate-500">Loading…</p>
  const { application, score, documents, decisions } = detail

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-800">Application #{application.id}</h1>
        <StatusBadge status={application.status} />
        <Link to="/underwriter" className="ml-auto text-sm text-indigo-700 hover:underline">Back to the queue</Link>
      </div>
      <p className="text-slate-600">{detail.applicant_name} · {detail.applicant_email}</p>

      {application.status === 'MANUAL_REVIEW' && (
        <DecisionForm applicationId={application.id} onDecided={() => setRefresh((n) => n + 1)} />
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Score">
          {score ? (
            <>
              <dl className="mb-4 flex flex-wrap gap-6 text-sm">
                <Stat label="Score" value={`${score.score} (${score.band})`} />
                <Stat label="Chance of default" value={`${(score.pd * 100).toFixed(1)}%`} />
                <Stat label="Model" value={score.model_version} />
              </dl>
              <p className="mb-1 text-sm font-medium text-slate-700">Top 5 factors (SHAP)</p>
              <ShapChart reasons={score.reasons} />
            </>
          ) : (
            <p className="text-sm text-slate-500">Not scored yet.</p>
          )}
        </Card>

        <Card title="Application">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Stat label="Amount" value={money(application.amount_requested)} />
            <Stat label="Term" value={`${application.term_months} months`} />
            <Stat label="Monthly income (declared)" value={money(application.declared_monthly_income)} />
            <Stat label="Purpose" value={application.purpose} />
            <Stat label="Employment" value={`${application.employment_type}, ${application.employment_years} years`} />
            <Stat label="Date of birth" value={application.date_of_birth ?? '-'} />
            <Stat label="Family" value={`${application.family_status ?? '-'}, ${application.children ?? 0} children`} />
            <Stat label="Housing" value={application.housing_type ?? '-'} />
            <Stat label="Education" value={application.education ?? '-'} />
            <Stat label="Owns car / home" value={`${application.owns_car ? 'yes' : 'no'} / ${application.owns_home ? 'yes' : 'no'}`} />
          </dl>
        </Card>
      </div>

      <Card title="Documents">
        {documents.length === 0 && <p className="text-sm text-slate-500">No documents uploaded.</p>}
        <div className="grid gap-4 lg:grid-cols-2">
          {documents.map((document) => <DocumentCard key={document.id} document={document} />)}
        </div>
      </Card>

      <Card title="Decision history">
        {decisions.length === 0 && <p className="text-sm text-slate-500">No decisions yet.</p>}
        <ol className="space-y-3">
          {decisions.map((d, index) => (
            <li key={index} className="border-l-4 border-slate-200 pl-3 text-sm">
              <StatusBadge status={d.outcome} />
              <span className="ml-2 text-slate-500">by {d.decided_by}, {new Date(d.created_at).toLocaleString()}</span>
              <p className="mt-1 text-slate-700">{d.reason}</p>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  )
}

function DecisionForm({ applicationId, onDecided }) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const tooShort = reason.trim().length < 10

  async function decide(outcome) {
    setSaving(true)
    setError('')
    try {
      await api.post(`/underwriter/applications/${applicationId}/decision`, { outcome, reason })
      onDecided()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="Your decision" className="border-amber-300">
      <textarea
        className={inputClass}
        rows={3}
        placeholder="Why? At least 10 characters. Auditors will read this."
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className="mt-3 flex items-center gap-2">
        <Button variant="success" disabled={tooShort || saving} onClick={() => decide('APPROVED')}>Approve</Button>
        <Button variant="danger" disabled={tooShort || saving} onClick={() => decide('REJECTED')}>Reject</Button>
        {tooShort && <span className="text-xs text-slate-500">Write a reason to enable the buttons.</span>}
      </div>
      <div className="mt-2"><ErrorBox message={error} /></div>
    </Card>
  )
}

// What Gemini read from one document, and which checks failed.
function DocumentCard({ document }) {
  const extraction = document.extraction
  const fields = extraction
    ? Object.entries(extraction.extracted).filter(([key, value]) => value !== null && typeof value !== 'object' && key !== 'doc_type')
    : []
  const months = extraction?.extracted.months || []

  return (
    <div className="rounded-lg border border-slate-200 p-4 text-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-medium text-slate-800">{DOC_LABELS[document.doc_type] || document.doc_type} #{document.id}</h3>
        {extraction ? (
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${extraction.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
            {extraction.passed ? 'Passed' : 'Failed'} · confidence {extraction.confidence.toFixed(2)}
          </span>
        ) : (
          <span className="text-xs text-slate-500">{document.extraction_status}</span>
        )}
      </div>
      {extraction?.issues.length > 0 && (
        <ul className="mb-2 list-disc pl-5 text-amber-800">
          {extraction.issues.map((issue) => <li key={issue}>{issue}</li>)}
        </ul>
      )}
      {fields.length > 0 && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
          {fields.map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="text-slate-500">{key.replaceAll('_', ' ')}</dt>
              <dd className="text-slate-800">{typeof value === 'number' ? money(value) : value}</dd>
            </div>
          ))}
        </dl>
      )}
      {months.length > 0 && (
        <table className="mt-2 w-full text-left">
          <thead className="text-slate-500">
            <tr><th className="font-medium">Month</th><th className="font-medium">Salary credit</th><th className="font-medium">Closing balance</th></tr>
          </thead>
          <tbody>
            {months.map((m) => (
              <tr key={m.month}>
                <td>{m.month}</td>
                <td>{m.salary_credit == null ? '-' : money(m.salary_credit)}</td>
                <td>{m.closing_balance == null ? '-' : money(m.closing_balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  )
}