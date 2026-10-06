import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage } from '../../api'
import { Card, ErrorBox, StatusBadge } from '../../components/ui'
import { money } from '../../format'

// Step 1 version: shows the application. Step 2 adds document upload, live status and the score.
export default function ApplicationDetail() {
  const { id } = useParams()
  const [application, setApplication] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get(`/applications/${id}`)
      .then((response) => setApplication(response.data))
      .catch((err) => setError(errorMessage(err)))
  }, [id])

  if (error) return <ErrorBox message={error} />
  if (!application) return <p className="text-slate-500">Loading…</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-800">Application #{application.id}</h1>
        <StatusBadge status={application.status} />
      </div>
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
      <p className="text-sm text-slate-500">
        Document upload and your score come in the next step. <Link to="/applicant" className="text-indigo-700 hover:underline">Back to my applications</Link>
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