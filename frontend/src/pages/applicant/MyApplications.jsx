import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../../api'
import { Card, ErrorBox, StatusBadge } from '../../components/ui'
import { money } from '../../format'

export default function MyApplications() {
  const [applications, setApplications] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/applications')
      .then((response) => setApplications(response.data))
      .catch((err) => setError(errorMessage(err)))
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">My applications</h1>
        <Link to="/applicant/new" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          New application
        </Link>
      </div>
      <ErrorBox message={error} />
      {applications === null && !error && <p className="text-slate-500">Loading…</p>}
      {applications?.length === 0 && (
        <Card><p className="text-slate-600">No applications yet. Start one with “New application”.</p></Card>
      )}
      {applications?.length > 0 && (
        <Card className="p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">#</th>
                <th className="px-6 py-3 font-medium">Purpose</th>
                <th className="px-6 py-3 font-medium">Amount</th>
                <th className="px-6 py-3 font-medium">Term</th>
                <th className="px-6 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((a) => (
                <tr key={a.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="px-6 py-3">
                    <Link to={`/applicant/applications/${a.id}`} className="font-medium text-indigo-700 hover:underline">{a.id}</Link>
                  </td>
                  <td className="px-6 py-3">{a.purpose}</td>
                  <td className="px-6 py-3">{money(a.amount_requested)}</td>
                  <td className="px-6 py-3">{a.term_months} months</td>
                  <td className="px-6 py-3"><StatusBadge status={a.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}