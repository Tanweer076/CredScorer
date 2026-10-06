import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage } from '../../api'
import DocumentUpload from '../../components/DocumentUpload'
import Reasons from '../../components/Reasons'
import ScoreGauge from '../../components/ScoreGauge'
import { Card, ErrorBox, StatusBadge } from '../../components/ui'
import WhatIf from '../../components/WhatIf'
import { money } from '../../format'

const POLL_MS = 4000

// GET that returns null on 404 ("not scored yet", "no decision yet") instead of failing.
async function getOrNull(url) {
  try {
    return (await api.get(url)).data
  } catch (err) {
    if (err.response?.status === 404) return null
    throw err
  }
}

// Everything on this page. The order matters: the worker can finish a step between two requests.
// Reading the documents first, then the application, then its score and decision means we never
// see a finished step without its result (and so never stop checking too early).
async function fetchAll(id) {
  const documents = (await api.get(`/applications/${id}/documents`)).data
  const application = (await api.get(`/applications/${id}`)).data
  const [score, decision] = await Promise.all([
    getOrNull(`/applications/${id}/score`),
    getOrNull(`/applications/${id}/decision`),
  ])
  return { application, documents, score, decision }
}

export default function ApplicationDetail() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0) // bump this number to fetch again
  const reload = useCallback(() => setRefresh((n) => n + 1), [])

  useEffect(() => {
    let cancelled = false // ignore an answer that arrives after we moved on
    fetchAll(id)
      .then((result) => {
        if (cancelled) return
        setData(result)
        setError('')
      })
      .catch((err) => { if (!cancelled) setError(errorMessage(err)) })
    return () => { cancelled = true }
  }, [id, refresh])

  // While the worker is still reading documents or scoring, check again every few seconds.
  const working = data && (
    data.documents.some((d) => d.extraction_status === 'PENDING') || data.application.status === 'DOCS_VERIFIED'
  )
  useEffect(() => {
    if (!working) return
    const timer = setInterval(reload, POLL_MS)
    return () => clearInterval(timer)
  }, [working, reload])

  if (!data) return error ? <ErrorBox message={error} /> : <p className="text-slate-500">Loading…</p>
  const { application, documents, score, decision } = data

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-800">Application #{application.id}</h1>
        <StatusBadge status={application.status} />
        {working && <span className="animate-pulse text-sm text-sky-700">Working on it…</span>}
        <Link to="/applicant" className="ml-auto text-sm text-indigo-700 hover:underline">Back to my applications</Link>
      </div>
      <ErrorBox message={error} />

      <Progress status={application.status} />
      {decision && <DecisionBanner decision={decision} />}

      {score && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Your credit score">
            <ScoreGauge score={score.score} band={score.band} />
            <p className="mb-2 mt-4 text-sm font-medium text-slate-700">What affected it most</p>
            <Reasons reasons={score.reasons} />
            {score.recommendations.length > 0 && (
              <>
                <p className="mb-2 mt-4 text-sm font-medium text-slate-700">How to improve it</p>
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {score.recommendations.map((tip) => <li key={tip}>{tip}</li>)}
                </ul>
              </>
            )}
          </Card>
          <WhatIf application={application} />
        </div>
      )}

      <DocumentUpload
        applicationId={application.id}
        documents={documents}
        canUpload={application.status === 'SUBMITTED'}
        onUploaded={reload}
      />

      <Card title="Summary">
        <dl className="grid gap-4 text-sm sm:grid-cols-3">
          <Item label="Amount" value={money(application.amount_requested)} />
          <Item label="Term" value={`${application.term_months} months`} />
          <Item label="Purpose" value={application.purpose} />
          <Item label="Monthly income" value={money(application.declared_monthly_income)} />
          <Item label="Employment" value={application.employment_type} />
          <Item label="Submitted" value={new Date(application.created_at).toLocaleDateString()} />
        </dl>
      </Card>
    </div>
  )
}

const STEPS = [
  { label: 'Submitted', statuses: ['SUBMITTED'] },
  { label: 'Documents verified', statuses: ['DOCS_VERIFIED'] },
  { label: 'Scored', statuses: ['SCORED'] },
  { label: 'Decision', statuses: ['MANUAL_REVIEW', 'APPROVED', 'REJECTED'] },
]

// Four steps, filled in up to where the application is now.
function Progress({ status }) {
  const current = STEPS.findIndex((step) => step.statuses.includes(status))
  return (
    <ol className="grid grid-cols-4 gap-2">
      {STEPS.map((step, index) => (
        <li key={step.label}>
          <div className={`h-1.5 rounded-full ${index <= current ? 'bg-indigo-600' : 'bg-slate-200'}`} />
          <p className={`mt-1 text-xs ${index <= current ? 'font-medium text-slate-800' : 'text-slate-400'}`}>{step.label}</p>
        </li>
      ))}
    </ol>
  )
}

const DECISION_STYLES = {
  APPROVED: { box: 'border-emerald-200 bg-emerald-50 text-emerald-800', title: 'Your loan is approved' },
  REJECTED: { box: 'border-red-200 bg-red-50 text-red-800', title: 'Your application was not approved' },
  MANUAL_REVIEW: { box: 'border-amber-200 bg-amber-50 text-amber-900', title: 'An underwriter is reviewing your application' },
}

function DecisionBanner({ decision }) {
  const style = DECISION_STYLES[decision.outcome] || DECISION_STYLES.MANUAL_REVIEW
  return (
    <div className={`rounded-xl border p-4 ${style.box}`}>
      <p className="font-semibold">{style.title}</p>
      <p className="mt-1 text-sm">{decision.reason}</p>
      <p className="mt-1 text-xs opacity-75">
        Decided by {decision.decided_by === 'system' ? 'our automatic checks' : 'an underwriter'} on {new Date(decision.created_at).toLocaleString()}
      </p>
    </div>
  )
}

function Item({ label, value }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  )
}